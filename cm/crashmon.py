#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Crash Inspector regulary analizes crash reports, finds crashed function names,
manages a know crashes list and creates tickets for new crashes.
"""

__author__ = 'Danil Lavrentyuk'
import sys
import os
import os.path
import time
import signal
import socket
import requests
import traceback
import argparse
import re
from subprocess import Popen, PIPE
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from parsedump import parse_dump
from crashdb import KnowCrashDB, WINAPICALL
import nxjira

from crashmonconf import *

__version__ = '1.4'

import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

with warnings.catch_warnings():
    warnings.simplefilter('ignore', InsecureRequestWarning)

if os.name == 'posix':  # may be platform.system is better? ;)
    dumptool = None

    CRASH_EXT = ('crash', 'gdb-bt')

    def get_lock():
        global lock_socket   # Without this our lock gets garbage collected
        lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            lock_socket.bind('\0' + PROCESS_NAME)
        except socket.error:
            return False
        return True

    def is_crash_dump_path(path):
        return (path.startswith('mediaserver') or path.startswith('client')
                ) and (
                path.endswith('.crash') or path.endswith('.gdb-bt'))

    def is_windows_dump(path):
        return False

    

    filt_path = "/usr/bin/c++filt"

    def demangle_names(names):
        try:
            p = Popen([filt_path], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate(input="\n".join(names))
        except Exception:
            print "WARNING: call %s failed: %s\nNames demangling SKIPPED!" % (filt_path, sys.exc_info())
            return names
        if p.returncode:
            print "DEBUG: %s returned code %s. STDERR: %s\nNames demangling SKIPPED!" % (filt_path, p.returncode, err)
            return names
        return out.split("\n")

    def report_name(fname):
        return fname

elif os.name == 'nt':
    import dumptool

    CRASH_EXT = ('dmp',)

    from filelock import FileLock, Timeout
    def get_lock():
        global lock
        lock = FileLock(sys.argv[0]+'.lock')
        try:
            lock.acquire(timeout=0)
        except Timeout:  # already locked
            return False
        return True

    def is_crash_dump_path(path):
        return path.endswith('.cdb-bt')

    def is_windows_dump(path):
        return path.endswith('.dmp')

    def demangle_names(names):  # already processed
        return names

    def report_name(fname):
        return dumptool.report_name(fname, True)

else:
    print "Unsupported OS: %s" % os.name
    sys.exit(2)

def attachment_filter(attachment):
    return is_crash_dump_path(attachment["filename"])

def attachment_windows_dump_filter(attachment):
    return is_windows_dump(attachment["filename"])


def web_link_filter(link):
    if not link or \
       not link.get('object') or \
       not link['object'].get('url'): return False
    ext = os.path.splitext(link['object']['url'])[1]
    return ext and ext[1:] in CRASH_EXT

def format_calls(calls): # FIXME put it into a separate module
    return "\n".join("\t"+c for c in calls)


# Do not process (add JIRA task) for drivers call stack
DRIVERS_FILTER = [
    r'ig.*64',
    r'atig6txx',
    r'atio6axx',
    r'nvoglv64',
    r'DpOFeedb',
    r'LavasoftTcpService64',
    r'DBROverlayIconBackuped' ]

def need_process_calls(calls):
    level = 0
    for c in KnowCrashDB.prepare2hash(calls):
        if c == WINAPICALL:
            continue
        if level >= 2:
            break
        for exp in DRIVERS_FILTER:
            if re.search(exp, c):
                return False
        level+=1
    return True

def isHotfix(version):
    if version is None:
        return False
    lastBuild = RELEASE_BUILDS.get(tuple(version[:3]), None)
    return lastBuild is not None and version[3] > lastBuild


def is_crash_new(crash, mark):
    return (
        crash['upload'] > mark['time'] or
        (crash['upload'] == mark['time'] and crash['path'] > mark['path'])
    )

OLD_VERSIONS_RE = r'^\/\w+\/2\.[0-5]\.'

def remove_old_versions(crashes):
    return filter(
        lambda v: not re.search(OLD_VERSIONS_RE, v['path']), crashes)

def remove_developers_crashes(crashes):
    return filter(
        lambda v: get_vers_bn(v)[1] != 0, crashes)

def get_crashes(crtype, mark):
    '''
    Load crashes list from the stat-server. Return a list of crash dicts
    :param crtype: str
    :param mark: str
    :return: list
    '''
    print "Getting %s data" % crtype
    url = crash_list_url(crtype)
    try:
        res = requests.get(url, auth = AUTH)
        if res.status_code != 200:
            print "Error: %s" % (res.status_code)
            return []
        crashes = res.json()
        if os.name == 'nt':
            crashes = remove_old_versions(crashes)
        rx = re.compile(r"\d+\.\d+\.\d+(\.\d+)")
        for crash in crashes:
            # 'new' means the crash upload timestamp is later than the last processed one
            crash['new'] = is_crash_new(crash, mark)
            cp = crash['path'].lstrip('/').split('/')
            if (os.name == 'posix'  # on Windows we've got many different starting directories
                and cp[0] not in ('mediaserver', 'mediaserver-bin', 'client-bin', 'client.bin')):
                print "WARNING: unexpected the first crash dump path element: %s" % cp[0]
            crash['basename'] = cp[-1]
            m = rx.match(cp[1])
            crash["version"] = [int(n) for n in m.group(0).split('.')[:4]] if m else None
            crash["isHotfix"] = isHotfix(crash["version"])

        crashes = remove_developers_crashes(crashes)

        print "Loaded %s: %s new crashes" % (crtype, sum(v['new'] for v in crashes))
        return sorted(crashes, key=lambda v: (v['upload'],v['path']))
    except Exception:
        print "Failed to get %s: %s" % (url, traceback.format_exc())
        return []


def dump_url(path):
    return ('' if path[0] == '/' else '/').join((DUMP_BASE, path))

if dumptool is not None:
    customization_rx = re.compile(r"\d+\.\d+\.\d+\.\d+\-\w+\-([^-]+)")
    cacheDir = 'cdb-cache'

    if not os.path.isdir(cacheDir):
        os.makedirs(cacheDir)

    def get_customization(uri):
        parts = uri.split('/')
        if parts[0] == '':
            parts.pop(0)
        m = customization_rx.match(parts[1])
        if m:
            cust = m.group(1)
            print "Customization found: " + cust
            return cust
        print "WARNING: Failed to get customization, 'default' used."
        return 'default'

    def callDumptool(dump, crash):
        fname = os.path.join(cacheDir, crash['basename'])
        with open(fname, "wb") as f:
            f.write(dump)
            f.close()
        try:
            dump = dumptool.analyseDump(
                fname, format='dict', customization=get_customization(crash['path']))
            if not dump:
                return False
            crash['component'] = dump['component']
            crash['dump'] = dump['dump']
            return True
        except Exception as err:
            print "Dump analyse failed: " + traceback.format_exc()
            return ''
        finally:
            try:
                os.remove(fname)
            except Exception as err:
                print "Failed to remove %s: %s" % (fname, err.message)


def load_crash_dump(crash_type, crash):
    if crash_type == 'dmp':
        crash_type = 'cdb-bt'
    url = dump_url(crash['path'])
    try:
        result = requests.get(url, auth=AUTH)
        if result.status_code != 200:
            print "Error reading %s: %s" % (crash['path'], result.status_code)
            return False
    except Exception:
        print "Error loading %s: %s" % (crash['path'], traceback.format_exc())
        return False
    #
    if dumptool is None:
        crash['dump'] = result.text
        crash['component'] = 'server'
    else:
        if not callDumptool(result.content, crash):
            print "FAILED to analize dump %s" % crash['path']
            #TODO send an email on it?
            return False
    #
    crash['url'] = url
    crash['calls'] = parse_dump(iter(crash['dump'].splitlines()), crash_type, crash['path'])
    if crash['calls']:
        crash['calls'] = tuple(demangle_names(crash['calls']))
        crash['hash'] = KnowCrashDB.hash(crash['calls'])
    else:
        print "Error parsing %s" % (crash['path'])
        return False
    return True


def email_send(mailfrom, mailto, msg): #FIXME move into a separate file!
    msg['From'] = mailfrom
    msg['To'] = mailto
    smtp = SMTP(SMTP_ADDR)
    if SMTP_LOGIN:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_LOGIN, SMTP_PASS)
    #smtp.set_debuglevel(1)
    smtp.sendmail(mailfrom, mailto, msg.as_string())
    smtp.quit()


def email_newcrash(crash, calls, jira_error=None):
    msg = MIMEMultipart()
    if jira_error:
        title = (
            "Jira error reported while trying to create a new crash issue:\n"
            "%s\nJira reply: %s\n"
            "New crash details:\n"
            % (jira_error.message, jira_error.reply)
        )
        msg['Subject'] = "Failed to create issue for a new crash!"
    else:
        vers, bn = get_vers_bn(crash)
        where = " (%s, version: %s, build number: %s)" % \
                (crash['component'] if crash['component'] else '',
                 vers, bn)
        title = "A crash with a new trace path found%s.\n\n" % where
        msg['Subject'] = "Crash with a new trace path found!%s" % where
    text = MIMEText(
        "%s"
        "Hash: %s\n"
        "URL: %s\n\n"
        "Call stask (named functions only):\n%s\n\n"
         % (title, crash['hash'], crash['url'], calls)
    )
    msg.attach(text)
    att = MIMEText(crash['dump'])
    att.add_header('Content-Disposition', 'attachment', filename=report_name(crash['path']).lstrip('/'))
    msg.attach(att)
    email_send(MAIL_FROM, MAIL_TO, msg)


def email_cant_attach(crash, issue, url, response, dump_path):
    print "DEBUG: email_cant_attach: %s, %s, %s, %s" % (issue, url, response, dump_url(dump_path))
    pass # TODO!!!


def email_priority_fail(key, issue, pold, pnew, error):
    print "DEBUG: email_priority_fail: %s, %s => %s, %s" % (issue, pold, pnew, error)
    pass # TODO!!!


def get_vers_bn(crash):
    version = crash.get('version')
    vers = 'unknown'
    bn = 0
    if version:
        vers = '.'.join(map(str, crash['version'][:-1]))
        bn = crash['version'][-1]
    return (vers, bn)

def fault_case2str(dumps, path, hash, issue=None):
    buf = []
    if hash == '':
        buf.append("<UNKNOWN>:")
    else:
        buf.append("Hash: %s" % hash)
        if issue:
            buf.append("Jira issue: %s" % (nxjira.browse_url(issue),))
        if path:
            buf.append("Stack:")
            buf.append(path)
    buf.append("Files (%s):" % len(dumps))
    for fname, _, _ in dumps:
        buf.append("\t%s" % fname)
    buf.append('')
    return "\n".join(buf)


def email_summary(faults, mintime, maxtime, known_issues):
    unknown = faults.pop('<UNKNOWN>', None)
    sig_only = []
    buf = []
    for k in sorted(faults.keys(), key=lambda x: (len(faults[x][0]), x), reverse=True):
        issue = known_issues.crashes[k].issue if known_issues.has(k) else None
        (sig_only if len(k) == 1 else buf).append(fault_case2str(faults[k][0], faults[k][1], faults[k][2], issue))
    if sig_only:
        buf += sig_only
    if unknown is not None:
        buf.append(fault_case2str(*unknown))
    if buf:
        #print "DEBUG:\n%s" % ("\n".join(buf),)
        msg = MIMEText("\n".join(buf))
        if re.search(r"\.\d\d\d\d\d\d$", mintime):
            mintime = mintime[:-7]
        if re.search(r"\.\d\d\d\d\d\d$", maxtime):
            maxtime = maxtime[:-7]
        msg['Subject'] = "Crashes by trace paths summary from %s to %s" % (mintime, maxtime)
        email_send(MAIL_FROM, MAIL_TO, msg)


class LastCrashTracker(object):
    _name = 'LastTimes'
    _sumname = 'LastSummary' # The last time a summary crash report was reated

    def __init__(self, filename):
        self._fn = filename
        self._summary_tm = 0
        self._stamps = {k: {'path': '', 'time': ''} for k in CRASH_EXT}
        if os.path.isfile(filename):
            self.load()
        self._changed = False

    def __getitem__(self, item):
        if item == 'summary':
            return self._summary_tm
        elif item == 'next_summary':
            return self.next_summary_time()
        return self._stamps.get(item, 0)

    def load(self):
        v = {}
        try:
            execfile(self._fn, v)
            if self._sumname in v:
                self._summary_tm = v[self._sumname]
            for k, t in v[self._name].iteritems():
                if k in CRASH_EXT:
                    if not 'path' in t and 'time' in t:
                        print "Wrong crash file record for extension %s: %s" % (k, t)
                        sys.exit(2)
                    self._stamps[k] = t
                else:
                    print "ERROR: unknown crash file extension found: %s" % k
        except Exception, e:
            print "ERROR: Failed to read last crash timestamps file %s: %s" % (self._fn, traceback.format_exc())
            sys.exit(2)

    def store(self):
        file(self._fn, 'w').write(LAST_CRASH_TIME_TPL % (self._name, self._stamps, self._sumname, self._summary_tm))
        self._changed = False

    def set(self, ext, path, tm):
        last = self._stamps.get(ext, None)
        if last is None or tm > last['time'] or (tm == last['time'] and path > last['path']):
            self._stamps[ext] = {'path': path, 'time': tm}
            self._changed = True
            self.store()

    def set_summary(self):
        self._summary_tm = time.time()
        self._changed = True
        self.store()

    def next_summary_time(self):
        return self._summary_tm + SUMMARY_PERIOD * (24 * 60 * 60)

    def __str__(self):
        return "%s('%s', changed=%s, summary_tm=%s, %s)" % (
            self.__class__.__name__, self._name, self._changed, self._summary_tm, self._stamps)

def find_priority(number):
    for i, level in enumerate(ISSUE_LEVEL):
        if number < level[0]:
            return i
    return i+1


class CrashMonitor(object):
    """
    The main class.
    Recurrent crash server checker. New crashes loader.
    """
    def __init__(self, args):
        # Setup the interruption handler
        self._stop = False
        self._lasts = LastCrashTracker(LASTS_FILE)
        self._known = KnowCrashDB(KNOWN_FAULTS_FILE)
        self.args = args
        signal.signal(signal.SIGINT,self._onInterrupt)

    def _onInterrupt(self, _signum, _stack):
        self._stop = True

    def _parseCalls(self, crash):
        key = crash['calls']
        formated_calls = format_calls(key)
        if crash['new'] and not self._known.has(key):
            print "New crash found in %s" % crash['path']
            if SEND_NEW_CRASHES:
                email_newcrash(crash, formated_calls)
            self._known.add(key)
        return key, formated_calls

    def updateCrashes(self):
        "Loads crashes list from the crashserver, filters by last parsed crash times."
        next_summary = self._lasts['next_summary']
        faults = dict()  # count number of loaded crashes with the same keys
        mintime, maxtime = '9999999999', ''

        for ct in CRASH_EXT:
            if self._stop: break
            crash_list = get_crashes(ct, self._lasts[ct])
            if not crash_list: continue
            mintime = min(crash_list[0]['upload'], mintime)
            maxtime = max(crash_list[-1]['upload'], maxtime)

            if dumptool is not None:
                dumptool.clear_cache(cacheDir, (crash['basename'] for crash in crash_list))

            for crash in crash_list:
                if self._stop: break
                #if ct == 'dmp':
                #    raw_input("Debug pause. Press ENTER")
                #
                print "Processing: %s" % crash['path']
                print "Crash info: %s" % crash
                if not load_crash_dump(ct, crash): continue
                # calls is empty when the crash trace function names and the signal haven't been found out
                # if calls consists only of one element -- it should be the signal (and there is no function names)
                key, formated_calls = self._parseCalls(crash) if crash['calls'] else ('<UNKNOWN>', '')
                print "Key: %s" % (key,)
                print "Formatted calls: %s" % (formated_calls,)

                faults.setdefault(key, ([], formated_calls, crash['hash']))[0].append(
                    (crash['url'], crash['path'], crash['dump']))

                if crash['new']:
                    # only new crashes can increase counter
                    if crash['calls'] and need_process_calls(crash['calls']):
                        # NOTE: faults[key][0] counts crashes in this call of load_crash_dump() only
                        # i.e. it counts only crashes currently stored on crash server
                        # (according to it's rotation period)
                        # i.e. too rare crashes are ignored
                        # It's Misha Uskov's idea, approved by Roma
                        crashes_count = self._known.get_faults(key) + 1
                        i = find_priority(crashes_count)
                        if i > 0:
                            crashinfo = self._known.get_and_incr_faults(key)
                            if crashinfo and crashinfo.issue:
                                _, issue_data = nxjira.get_issue(crashinfo.issue)
                                if issue_data.code == nxjira.CODE_NOT_FOUND:
                                    print "WARNING: Jira issue %s is not found. Issue will be created anew!" % crashinfo.issue
                                    self._known.set_issue(key, None)
                                    crashinfo = None
                            if crashinfo and crashinfo.issue:
                                if issue_data.ok:
                                    if self.can_change(issue_data, crash['version'], crash["isHotfix"]):
                                        # 1. Attach the new crash dump
                                        _, attach_count = nxjira.count_attachments(issue_data, predicat=attachment_filter)
                                        while attach_count >= MAX_ATTACHMENTS:
                                            print "Deleting oldest attachment in %s" % crashinfo.issue
                                            if not nxjira.delete_oldest_attchment(issue_data, predicat=attachment_filter):
                                                break
                                            attach_count -= 1
                                        _, link_count = nxjira.count_web_links(issue_data, predicat=web_link_filter)
                                        while link_count >= MAX_ATTACHMENTS:
                                            print "Deleting oldest link in %s" % crashinfo.issue
                                            if not nxjira.delete_oldest_web_link(issue_data, predicat=web_link_filter):
                                                break
                                            link_count -= 1
                                        _, dump_attach_count = nxjira.count_attachments(
                                            issue_data, predicat=attachment_windows_dump_filter)
                                        while dump_attach_count >= 0:
                                            print "Deleting oldest attachment in %s" % crashinfo.issue
                                            if not nxjira.delete_oldest_attchment(
                                                issue_data, predicat=attachment_windows_dump_filter):
                                                break
                                            dump_attach_count -= 1
                                        if attach_count < MAX_ATTACHMENTS and link_count < MAX_ATTACHMENTS:
                                            res = self.add_attachment(crashinfo.issue, crash['path'], crash['dump'], crash['url'], True)
                                            if res is not None:
                                                email_cant_attach(crash, crashinfo.issue, crash['url'], res, crash['path'])
                                        # 2. Check if the priority should be increased
                                        if crashinfo.priority < i: # new priority is higher
                                            rc = self.increase_priority(key, crashinfo, i, issue_data)
                                            if rc:
                                                self._known.set_issue(key, (crashinfo.issue, i))
                                            elif rc is not None:
                                                print "No issue %s found in Jira, priority change ignored" % crashinfo.issue
                                    else:
                                        print "Ignore already closed issue %s" % crashinfo.issue
                                else:
                                    print "ERROR: can't load issue %s: %s, %s" % (
                                        crashinfo.issue, issue_data.code, issue_data.reason)
                            else:
                                try:
                                    new_issue = self.create_jira_issue(crash, formated_calls, i, crashes_count, faults[key][0])
                                    self._known.set_issue(key, (new_issue, i))
                                except nxjira.JiraError, e:
                                    email_newcrash(crash, formated_calls, e)
                    self._lasts.set(ct, crash['path'], crash['upload'])

        if self._known.changed:
            self._known.rewrite()

        if next_summary <= time.time():
            print "Sending crashes summary..."
            email_summary(faults, mintime, maxtime, self._known)
            self._lasts.set_summary()

    def create_jira_issue(self, crash, calls, priority, crashes_count, dumps):
        desc = (
            "Crash Monitor detected '%d' crashes with a new trace path\n\n"
            "Hash: %s\n"
            "Call stask (named functions only):\n{code}%s{code}\n\n"
             % (crashes_count, crash['hash'], calls)
        )
        if priority < 1:
            print "ERROR: create_jira_issue int number value < 1"
            return
        if priority > len(ISSUE_LEVEL):
            priority = len(ISSUE_LEVEL)
        if crash['component'] == 'server':
            component = 'Server'
            team = 'Server'
        elif crash['component'] == 'client':
            component = 'Client'
            team = 'GUI'
        else:
            print "ERROR: create_jira_issue: unknown component value: %s" % (crash['component'],)
            component = team = None
        if component is None:
            name = "Crash detected: %s" % crash['hash']
        else:
            name = "Crash detected in %s: %s" % (crash['component'], crash['hash'])

        vers, bn = get_vers_bn(crash)    

        issue_key, url = nxjira.create_issue(
            name, desc, ISSUE_LEVEL[priority-1][1], component, team, vers, bn)
        if len(dumps) > MAX_ATTACHMENTS:
            del dumps[MAX_ATTACHMENTS:]
        is_first = True
        for url, path, dump in dumps:
            res = self.add_attachment(issue_key, path, dump, url, is_first)
            is_first = False
            if res is not None:
                email_cant_attach(crash, issue_key, url, res, path)
        print "New jira issue created: %s" % (issue_key,)
        return issue_key

    def add_attachment(self, issue, name, dump, url, add_dump_attachment):
        name = report_name(name.lstrip('/'))
        if not is_crash_dump_path(name):
            print "WARNING: Strange crash dump name: %s" % name
            print "POSSIBLY is_crash_dump_path() conditions are to be updated!"
        res = nxjira.create_web_link(issue, name, url)
        if not res and add_dump_attachment:
            nxjira.create_dump_attachment(issue, url, AUTH)
        return nxjira.create_attachment(issue, name, dump) or res

    def increase_priority(self, key, crashinfo, priority, issue_data=None):
        if priority < 1: # FIXME copypasta!
            print "ERROR: increase_priority int number value < 1"
            return
        if priority > len(ISSUE_LEVEL):
            priority = len(ISSUE_LEVEL)
        pnew = ISSUE_LEVEL[priority-1][1]
        pold = ISSUE_LEVEL[crashinfo.priority-1][1] if 0 < crashinfo.priority <= len(ISSUE_LEVEL) else None
        try:
            rc = nxjira.priority_change(issue_data or crashinfo.issue, pnew, pold)
            if rc:
                print "Issue %s priority changed: %s -> %s" % (crashinfo.issue, pold, pnew)
            return rc
        except nxjira.JiraError, e:
            email_priority_fail(key, crashinfo.issue, pold, pnew, e)
            return None

    def can_change(self, issue_data, crashed_version, is_hotfix): # TODO why not to move it into the JiraReply class?
        if issue_data.is_done(): # it's a readon not to add more dumps and increase priority
            if issue_data.is_closed(): # hmm...
                smallest_version = issue_data.smallest_fixversion()
                print "DEBUG: closed issue %s, fix version %s, crash found in %s" % (
                    issue_data.data['key'], smallest_version, crashed_version)
                # Future version case
                if smallest_version and smallest_version[0] == 0:
                    print "Issue %s has Future version" % (issue_data.data['key'],)
                    return False
                if crashed_version is None or crashed_version[:3] > smallest_version or is_hotfix:
                    if issue_data.reopen():
                        print "Issue %s reopened" % (issue_data.data['key'],)
                        return True
            return False
        return True

    def run(self):
        """ The main cyrcle """
        if args.auto:
            try:
                period = int(args.period)
            except Exception:
                period = CHECK_PERIOD
            print "[auto mode, period %s min]" % period
            period *= 60
            while not self._stop:
                self.updateCrashes()
                time.sleep(period)
        else:
            self.updateCrashes()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--auto", action="store_true",
        help="automatically periodical check mode.")
    parser.add_argument("-p", "--period", type=int,
        help="new crashes check period (sleep time since end of one check to start of another), minutes, use with -a")
    parser.add_argument("-t", "--time", action="store_true",
        help="log start and finish times (useful for scheduled runs).")
    parser.add_argument("--dummy", action="store_true", help="just run dummy loop, for debug")
    return parser.parse_args()


def dummy_loop():  # for some debug
    print "Running dummy loop..."
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    args = parse_args()
    if args.time:
        print "[Start at %s]" % time.asctime()

    if get_lock():
        if args.dummy:
            dummy_loop()
        else:
            try:
                CrashMonitor(args).run()
            except BaseException:
                traceback.print_exc()

    else:
        if os.name == 'posix':
            print "Another copy of process found. Lock name: " + PROCESS_NAME
        else:
            print "Another copy of process found."
        sys.exit(1)

    if args.time:
        print "[Finished at %s]" % time.asctime()
