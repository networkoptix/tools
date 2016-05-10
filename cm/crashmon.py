#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
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
from crashdb import KnowCrashDB
import nxjira

from crashmonconf import *

__version__ = '1.3'

filt_path = "/usr/bin/c++filt"


def is_crash_dump_path(path):
    return (path.startswith('mediaserver') or path.startswith('client')
            ) and (
            path.endswith('.crash') or path.endswith('.gdb-bt'))


def attachment_filter(attachment):
    return is_crash_dump_path(attachment["filename"])


def format_calls(calls): # FIXME put it into a separate module
    return "\n".join("\t"+c for c in calls)


def get_lock(process_name):
    global lock_socket   # Without this our lock gets garbage collected
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + process_name)
    except socket.error:
        return False
    return True


def isHotfix(version):
    if version is None:
        return False
    lastBuild = RELEASE_BUILDS.get(tuple(version[:3]), None)
    return lastBuild is not None and version[3] > lastBuild

def get_crashes(crtype, mark):
    print "Getting %s data" % crtype
    url = crash_list_url(crtype)
    try:
        res = requests.get(url, auth = AUTH)
        if res.status_code != 200:
            print "Error: %s" % (res.status_code)
            return []
        crashes = res.json()
        rx = re.compile(r"\d+\.\d+\.\d+(\.\d+)")
        for crash in crashes:
            crash['new'] = crash['upload'] > mark['time'] or (
                                crash['upload'] == mark['time'] and crash['path'] > mark['path']
                           )

            cp = crash['path'].lstrip('/').split('/')
            if cp[0] not in ('mediaserver', 'mediaserver-bin', 'client-bin', 'client.bin'):
                print "WARNING: unexpected the first crash dump path element: %s", cp[0]
            m = rx.match(cp[1])
            crash["version"] = [int(n) for n in m.group(0).split('.')[:4]] if m else None
            crash["isHotfix"] = isHotfix(crash["version"])

        print "Loaded %s: %s new crashes" % (crtype, sum(v['new'] for v in crashes))
        return sorted(crashes, key=lambda v: (v['upload'],v['path']))
    except Exception:
        print "Failed to get %s: %s" % (url, traceback.format_exc())
        return []


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


def dump_url(path):
    return ('' if path[0] == '/' else '/').join((DUMP_BASE, path))


def load_crash_dump(crash_type, crash):
    url = dump_url(crash['path'])
    try:
        result = requests.get(url, auth=AUTH)
        if result.status_code != 200:
            print "Error reading %s: %s" % (crash['path'], result.status_code)
            return False
    except Exception:
        print "Error loading %s: %s" % (crash['path'], traceback.format_exc())
        return False
    crash['dump'] = result.text
    crash['url'] = url
    crash['calls'] = parse_dump(iter(crash['dump'].split("\n")), crash_type, crash['path'])
    if crash['calls']:
        crash['calls'] = tuple(demangle_names(crash['calls']))
        crash['hash'] = KnowCrashDB.hash(crash['calls'])
    else:
        crash['hash'] = ''
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
        msg['Subject'] = "Failed to reate issue for a new crash!"
    else:
        title = "A crash with a new trace path found.\n\n"
        msg['Subject'] = "Crash with a new trace path found!"
    text = MIMEText(
        "%s"
        "Hash: %s\n"
        "URL: %s\n\n"
        "Call stask (named functions only):\n%s\n\n"
         % (title, crash['hash'], crash['url'], calls)
    )
    msg.attach(text)
    att = MIMEText(crash['dump'])
    att.add_header('Content-Disposition', 'attachment', filename=crash['path'].lstrip('/'))
    msg.attach(att)
    email_send(MAIL_FROM, MAIL_TO, msg)


def email_cant_attach(crash, issue, url, response, dump_path):
    print "DEBUG: email_cant_attach: %s, %s, %s, %s" % (issue, url, response, dump_url(dump_path))
    pass # TODO!!!


def email_priority_fail(key, issue, pold, pnew, error):
    print "DEBUG: email_priority_fail: %s, %s => %s, %s" % (issue, pold, pnew, error)
    pass # TODO!!!


def fault_case2str(dumps, path, hash, issue=None):
    buf = []
    if hash == '':
        buf.append("<UNKNOWN>:")
    else:
        buf.append("Hash: %s" % hash)
        if issue:
            buf.append("Jira issue: %s" % (nxjira.browse_url(issue[0]),))
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
        issue = known_issues.crashes[k] if known_issues.has(k) else None
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


def email_hash_collision(hash, keys):
    msg = MIMEText(
        "WARNING! A hash collision detected!\n(We're very lucky, take a drink! :) It's a really rare occation!)\n\n"
        "Hash: %s\nKeys:\n%s\n"
         % (hash, keys))
    msg['Subject'] = "WARNING! A hash collision detected for %s" % hash
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
        self._hashes = dict()
        for key, hashval in self._known.iterhash():
            self._hashes.setdefault(hashval, []).append(key)
        self.args = args
        signal.signal(signal.SIGINT,self._onInterrupt)

    def _onInterrupt(self, _signum, _stack):
        self._stop = True

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

            for crash in crash_list:
                if self._stop: break
                #
                if not load_crash_dump(ct, crash): continue
                # calls is empty when the crash trace function names and the signal haven't been found out
                # if calls consists only of one element -- it should be the signal (and there is no function names)
                if crash['calls']:
                    key = crash['calls']
                    formated_calls = format_calls(key)
                    if crash['new'] and not self._known.has(key):
                        if crash['hash'] in self._hashes:
                            self.report_hash_collision(crash['hash'], key)
                        else:
                            self._hashes[crash['hash']] = [key]
                        print "New crash found in %s" % crash['path']
                        if SEND_NEW_CRASHES:
                            email_newcrash(crash, formated_calls)
                        self._known.add(key)
                else:
                    key, formated_calls = '<UNKNOWN>', ''

                faults.setdefault(key, ([], formated_calls, crash['hash']))[0].append((crash['url'], crash['path'], crash['dump']))

                if crash['new']:
                    # only new crashes can increase counter
                    if crash['calls']:
                        # NOTE: faults[key][0] counts crashes in this call of load_crash_dump() only
                        # i.e. it counts only crashes currently stored on crash server
                        # (according to it's rotation period)
                        # i.e. too rare crashes are ignored
                        # It's Misha Uskov's idea, approved by Roma
                        i = find_priority(len(faults[key][0]))
                        if i > 0:
                            issue = self._known.crashes[key]
                            if issue:
                                _, issue_data = nxjira.get_issue(issue[0])
                                if issue_data.code == nxjira.CODE_NOT_FOUND:
                                    print "WARNING: Jira issue %s is not found. Issue will be created anew!"
                                    self._known.set_issue(key, None)
                                    issue = None
                            if issue:
                                if issue_data.ok:
                                    if self.can_change(issue_data, crash['version'], crash["isHotfix"]):
                                        # 1. Attach the new crash dump
                                        _, counted = nxjira.count_attachments(issue_data, predicat=attachment_filter)
                                        while counted >= MAX_ATTACHMENTS:
                                            print "Deleting oldest attachment in %s" % (issue[0],)
                                            if not nxjira.delete_oldest_attchment(issue_data, predicat=attachment_filter):
                                                break
                                            counted -= 1
                                        if counted < MAX_ATTACHMENTS:
                                            res = self.add_attachment(issue[0], crash['path'], crash['dump'])
                                            if res is not None:
                                                email_cant_attach(crash, issue[0], crash['url'], res, crash['path'])
                                        # 2. Check if the priority should be increased
                                        if issue[1] < i: # new priority is higher
                                            rc = self.increase_priority(key, issue, i, issue_data)
                                            if rc:
                                                self._known.set_issue(key, (issue[0], i))
                                            elif rc is not None:
                                                print "No issue %s found in Jira, priority change ignored" % (issue[0],)
                                    else:
                                        print "Ignore already closed issue %s" % (issue[0],)
                                else:
                                    print "ERROR: can't load issue %s: %s, %s" % (
                                        issue[0], issue_data.code, issue_data.reason)
                            else:
                                try:
                                    new_issue = self.create_jira_issue(crash, formated_calls, i, faults[key][0])
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

    def create_jira_issue(self, crash, calls, priority, dumps):
        name = "Crash detected: %s" % crash['hash']
        desc = (
            "Crash Monitor detected a crash with a new trace path\n\n"
            "Hash: %s\n"
            "URL: %s\n\n"
            "Call stask (named functions only):\n%s\n\n"
             % (crash['hash'], crash['url'], calls)
        )
        if priority < 1:
            print "ERROR: create_jira_issue int number value < 1"
            return
        if priority > len(ISSUE_LEVEL):
            priority = len(ISSUE_LEVEL)
        issue_key, url = nxjira.create_issue(name, desc, ISSUE_LEVEL[priority-1][1])
        if len(dumps) > MAX_ATTACHMENTS:
            del dumps[MAX_ATTACHMENTS:]
        for _, path, dump in dumps:
            res = self.add_attachment(issue_key, path, dump)
            if res is not None:
                email_cant_attach(crash, issue_key, url, res, path)
        print "New jira issue created: %s" % (issue_key,)
        return issue_key

    def add_attachment(self, issue, name, dump):
        name = name.lstrip('/')
        if not is_crash_dump_path(name):
            print "WARNING: Strange crash dump name: %s" % name
            print "POSSIBLY is_crash_dump_path() conditions are to be updated!"
        return nxjira.create_attachment(issue, name, dump)

    def increase_priority(self, key, issue, priority, issue_data=None):
        if priority < 1: # FIXME copypasta!
            print "ERROR: increase_priority int number value < 1"
            return
        if priority > len(ISSUE_LEVEL):
            priority = len(ISSUE_LEVEL)
        pnew = ISSUE_LEVEL[priority-1][1]
        pold = ISSUE_LEVEL[issue[1]-1][1] if 0 < issue[1] <= len(ISSUE_LEVEL) else None
        try:
            rc = nxjira.priority_change(issue_data or issue[0], pnew, pold)
            if rc:
                print "Issue %s priority changed: %s -> %s" % (issue[0], pold, pnew)
            return rc
        except nxjira.JiraError, e:
            email_priority_fail(key, issue, pold, pnew, e)
            return None

    def can_change(self, issue_data, crashed_version, is_hotfix): # TODO why not to move it into the JiraReply class?
        if issue_data.is_done(): # it's a readon not to add more dumps and increase priority
            if issue_data.is_closed(): # hmm...
                print "DEBUG: closed issue %s, fix version %s, crash found in %s" % (issue_data.data['key'], issue_data.smallest_fixversion(), crashed_version)
                if crashed_version is None or crashed_version[:3] > issue_data.smallest_fixversion() or is_hotfix:
                    if issue_data.reopen():
                        print "Issue %s reopened" % (issue_data.data['key'],)
                        return True
            return False
        return True

    def report_hash_collision(self, hash, key):
        self._hashes[hash].append(key)
        keys = "\n".join("\t%s" % (v,) for v in self._hashes[hash])
        print "WARNING: a hash collision detected! Hash = %s. Keys:\n%s" % (hash, keys)
        email_hash_collision(hash, keys)

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



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--auto", action="store_true", help="automatically periodical check mode.")
    parser.add_argument("-p", "--period", type=int, help="new crashes check period (sleep time since end of one check to start of another), minutes, use with -a")
    parser.add_argument("-t", "--time", action="store_true", help="log start and finish times (useful for scheduled runs).")
    args = parser.parse_args()

    if args.time:
        print "[Start at %s]" % time.asctime()

    if get_lock(PROCESS_NAME):
        CrashMonitor(args).run()
    else:
        print "Another copy of process found. Lock name: " + PROCESS_NAME
        sys.exit(1)

    if args.time:
        print "[Finished at %s]" % time.asctime()
