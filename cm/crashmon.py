#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
__author__ = 'Danil Lavrentyuk'
"""
Crash Inspector regulary analizes crash reports, finds crashed function names,
manages a know crashes list and creates tickets for new crashes.
"""
import sys
import os
import os.path
import time
import signal
import socket
import requests
import traceback
import argparse
import errno
import re
from hashlib import md5
from subprocess import Popen, PIPE
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


from parsedump import parse_dump

from crashmonconf import *

filt_path = "/usr/bin/c++filt"


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


def get_crashes(crtype):
    print "Getting %s data" % crtype
    url = crash_list_url(crtype)
    try:
        res = requests.get(url, auth = AUTH)
        if res.status_code != 200:
            print "Error: %s" % (res.status_code)
            return []
        return res.json()
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


def load_known_faults():
    known = []
    try:
        with open(KNOWN_FAULTS_FILE) as f:
            for line in f:
                if line.strip() != '':
                    hash, key = line.split(':',1)
                    known.append((hash, eval(key)))
    except IOError, e:
        if e.errno == errno.ENOENT:
            print "%s not found, use empty list" % KNOWN_FAULTS_FILE
        else:
            raise
    else:
        print "%s faults are known already" % len(known)
    return known


def load_crash_dump(crash_type, crash):
    url = ('' if crash['path'][0] == '/' else '/').join((DUMP_BASE, crash['path']))
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
        crash['hash'] = md5(''.join(crash['calls'])).hexdigest()
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


def email_newcrash(crash, calls):
    msg = MIMEMultipart()
    text = MIMEText(
        "A crash with a new trace path found.\n\n"
        "Hash: %s\n"
        "URL: %s\n\n"
        "Call stask (named functions only):\n%s\n\n"
         % (crash['hash'], crash['url'], calls)
    )
    msg.attach(text)
    att = MIMEText(crash['dump'])
    att.add_header('Content-Disposition', 'attachment', filename=crash['path'].lstrip('/'))
    msg.attach(att)
    msg['Subject'] = "Crash with a new trace path found!"
    email_send(MAIL_FROM, MAIL_TO, msg)


def fault_case2str(fnames, path, hash):
    buf = []
    if hash == '':
        buf.append("<UNKNOWN>:")
    else:
        buf.append("Hash: %s" % hash)
        if path:
            buf.append("Stack:")
            buf.append(path)
    buf.append("Files (%s):" % len(fnames))
    for fname in fnames:
        buf.append("\t%s" % fname)
    buf.append('')
    return "\n".join(buf)


def email_summary(faults, mintime, maxtime):
    unknown = faults.pop('<UNKNOWN>', None)
    sig_only = []
    buf = []
    for k in sorted(faults.keys(), key=lambda x: (len(faults[x][0]), x), reverse=True):
        (sig_only if len(k) == 1 else buf).append(fault_case2str(*faults[k]))
    if sig_only:
        buf += sig_only
    if unknown is not None:
        buf.append(fault_case2str(*unknown))
    if buf:
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

    def __getitem__(self, item):
        if item == 'summary':
            return self._summary_tm
        return self._stamps.get(item, 0)

    def set(self, ext, path, tm):
        last = self._stamps.get(ext, None)
        if last is None or (tm > last['time'] and path > last['path']):
            self._stamps[ext] = {'path': path, 'time': tm}
            self._changed = True
            self.store()

    def set_summary(self):
        self._summary_tm = time.time()
        self._changed = True
        self.store()

    def __str__(self):
        return "%s('%s', changed=%s, summary_tm=%s, %s)" % (
            self.__class__.__name__, self._name, self._changed, self._summary_tm, self._stamps)


class CrashMonitor(object):
    """
    The main class.
    Recurrent crash server checker. New crashes loader.
    """
    def __init__(self, args):
        # Setup the interruption handler
        self._stop = False
        self._lasts = LastCrashTracker(LASTS_FILE)
        self._known = set()
        self._hashes = dict()
        for hash, key in load_known_faults():
            self._known.add(key)
            self._hashes.setdefault(hash, []).append(key)
        self.args = args
        signal.signal(signal.SIGINT,self._onInterrupt)

    def _onInterrupt(self, _signum, _stack):
        self._stop = True

    def updateCrashes(self):
        "Loads crashes list from the crashserver, filters by last parsed crash times."
        faults = dict() if self._lasts['summary'] + SUMMARY_PERIOD * (24 * 60 * 60) <= time.time() else None
        mintime, maxtime = '9999999999', ''
        crash_sort_key = lambda v: (v['upload'],v['path'])

        for ct in CRASH_EXT:
            if self._stop:
                break
            crash_list = get_crashes(ct)
            if not crash_list:
                continue
            mark = self._lasts[ct]
            for crash in crash_list:
                crash['new'] = crash['upload'] >= mark['time'] and crash['path'] > mark['path']
            print "Loaded %s: %s new crashes" % (ct, sum(v['new'] for v in crash_list))

            if faults is not None: # We need all crashes from the list
                crash_list = sorted(crash_list, key=crash_sort_key)
                if crash_list:
                    mintime = min(crash_list[0]['upload'], mintime)
                    maxtime = max(crash_list[-1]['upload'], maxtime)
            else:
                crash_list = sorted((v for v in crash_list if v['new']), key=crash_sort_key)

            for crash in crash_list:
                if self._stop:
                    break
                if not load_crash_dump(ct, crash):
                    continue
                # calls is empty when the crash trace function names and the signal haven't been found out
                # if calls consists only of one element -- it should be the signal (and there is no function names)
                if crash['calls']:
                    key = crash['calls']
                    formated_calls = format_calls(key)
                    if crash['new'] and key not in self._known:
                        if crash['hash'] in self._hashes:
                            self.report_hash_collision(crash['hash'], key)
                        else:
                            self._hashes[crash['hash']] = [key]
                        print "New crash found in %s" % crash['path']
                        email_newcrash(crash, formated_calls)
                        self._known.add(key)
                        open(KNOWN_FAULTS_FILE, "a").write("%s:%s\n" % (crash['hash'], key))
                else:
                    key, formated_calls = '<UNKNOWN>', ''

                if crash['new']:
                    self._lasts.set(ct, crash['path'], crash['upload'])

                if faults is not None:
                    faults.setdefault(key, ([], formated_calls, crash['hash']))[0].append(crash['url'])

        if faults is not None:
            email_summary(faults, mintime, maxtime)
            self._lasts.set_summary()

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
    parser.add_argument("-a", "--auto", action="store_true", help="Continuos full autotest mode.")
    parser.add_argument("-p", "--period", type=int, help="new crashes check period (sleep time between since end of one check to start of another), minutes")
    parser.add_argument("-t", "--time", action="store_true", help="Log start and finish times (useful for scheduled runs).")
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
