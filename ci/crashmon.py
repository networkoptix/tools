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
    res = requests.get(url, auth = AUTH)
    if res.status_code != 200:
        print "Error: %s" % (res.status_code)
        return []
    try:
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
    known = set()
    try:
        with open(KNOWN_FALTS_FILE) as f:
            for line in f:
                if line.strip() != '':
                    known.add(eval(line))
    except IOError, e:
        if e.errno == errno.ENOENT:
            print "%s not found, use empty list" % KNOWN_FALTS_FILE
        else:
            raise
    else:
        print "%s faults are known already" % len(known)
    return known


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


def email_newcrash(url, dump, calls, path):
    msg = MIMEMultipart()
    text = MIMEText(
        "A crash with a new trace path found.\n\n"
        "URL: %s\n\n"
        "Call stask (named functions only):\n%s\n\n"
         % (url, calls)
    )
    msg.attach(text)
    att = MIMEText(dump)
    att.add_header('Content-Disposition', 'attachment', filename=path.lstrip('/'))
    msg.attach(att)
    msg['Subject'] = "Crash with a new trace path found!"
    email_send(MAIL_FROM, MAIL_TO, msg)

drop_microsec_rx = re.compile("\.\d\d\d\d\d\d$")

def email_summary(text, mintime, maxtime):
    if drop_microsec_rx.search(mintime):
        mintime = mintime[:-7]
    if drop_microsec_rx.search(maxtime):
        maxtime = maxtime[:-7]
    msg = MIMEText(text)
    msg['Subject'] = "Crashes by trace paths summary from %s to %s" % (mintime, maxtime)
    email_send(MAIL_FROM, MAIL_TO, msg)


def fault_case2str(calls, fnames, path):
    buf = []
    if calls == None:
        buf.append("<UNKNOWN>:")
    else:
        buf.append("Key: %s" % repr(calls))
        if path:
            buf.append("Stack:")
            buf.append(path)
    buf.append("Files (%s):" % len(fnames))
    for fname in fnames:
        buf.append("\t%s" % fname)
    buf.append('')
    return "\n".join(buf)


class LastCrashTracker(object):
    name = 'LastTimes'
    sumname = 'LastSummary' # The last time a summary crash report was reated

    def __init__(self, filename):
        self.fn = filename
        self.summary_tm = 0
        self.stamps = {k: {'path': '', 'time':''} for k in CRASH_EXT}
        if os.path.isfile(filename):
            self.load()
        self.changed = False

    def load(self):
        v = {}
        try:
            execfile(self.fn, v)
            if self.sumname in v:
                self.summary_tm = v[self.sumname]
            for k, t in v[self.name].iteritems():
                if k in CRASH_EXT:
                    if not 'path' in t and 'time' in t:
                        print "Wrong crash file record for extension %s: %s" % (k, t)
                        sys.exit(2)
                    self.stamps[k] = t
                else:
                    print "ERROR: unknown crash file extension found: %s" % k
        except Exception, e:
            print "ERROR: Failed to read last crash timestamps file %s: %s" % (self.fn, traceback.format_exc())
            sys.exit(2)

    def store(self):
        file(self.fn, 'w').write(LAST_CRASH_TIME_TPL % (self.name, self.stamps, self.sumname, self.summary_tm))
        self.changed = False

    def __getitem__(self, item):
        return self.stamps.get(item, 0)

    def set(self, ext, path, tm):
        if tm > self.stamps.get(ext, 0):
            self.stamps[ext] = {'path': path, 'time': tm}
            self.changed = True

    def __str__(self):
        return "%s('%s', changed=%s, summary_tm=%s, %s)" % (
            self.__class__.__name__, self.name, self.changed, self.summary_tm, self.stamps)


class CrashMonitor(object):
    """
    The main class.
    Recurrent crash server checker. New crashes loader.
    """
    def __init__(self, args):
        # Setup the interruption handler
        self._stop = False
        self._lasts = LastCrashTracker(LASTS_FILE)
        self._known = load_known_faults()
        self.args = args
        signal.signal(signal.SIGINT,self._onInterrupt)

    def _onInterrupt(self, _signum, _stack):
        self._stop = True

    def updateCrashes(self):
        "Loads crashes list from the crashserver, filters by last parsed crash times."
        crash_list = dict()
        faults = dict() if self._lasts.summary_tm + SUMMARY_PERIOD * (24 * 60 * 60) <= time.time() else None
        paths = {} # store (key: path) pairs for summary
        mintime = '9999999999'
        maxtime = ''
        for ct in CRASH_EXT:
            if self._stop:
                break
            mark = self._lasts[ct]
            crash_list[ct] = sorted((v for v in get_crashes(ct)
                                     if v['upload'] >= mark['time'] and v['path'] > mark['path']),
                                    key=lambda v: (v['upload'],v['path']))
            if crash_list[ct]:
                mintime = min(crash_list[ct][0]['upload'], mintime)
                maxtime = max(crash_list[ct][-1]['upload'], maxtime)
            print "Loaded %s: %s new crashes" % (ct, len(crash_list[ct]))
            for crash in crash_list[ct]:
                if self._stop:
                    break
                url = ('' if crash['path'][0] == '/' else '/').join((DUMP_BASE, crash['path']))
                try:
                    result = requests.get(url, auth=AUTH)
                    if result.status_code != 200:
                        print "Error reading %s: %s" % (crash['path'], result.status_code)
                        continue
                except Exception, e:
                    print "Error loading %s: %s" % (crash['path'], e)
                    continue
                dump = result.text
                result.close()
                calls = parse_dump(iter(dump.split("\n")), ct, crash['path'])
                # calls is empty if the crash trace function names and the signal  haven't been found out
                # if calls consists only of one element -- it should be the signal (and there is no function names)
                if calls:
                    key = tuple(calls)
                    formated_calls = format_calls(demangle_names(calls))
                    if key not in self._known:
                        print "New crash found in %s" % crash['path']
                        print "Calls:"
                        print formated_calls
                        email_newcrash(url, dump, formated_calls, crash['path'])
                        self._known.add(key)
                        open(KNOWN_FALTS_FILE, "a").write("%s\n" % (key,))
                        if faults is not None:
                            paths[key] = formated_calls
                        faults[key] = [crash['path']]
                    else:
                        faults[key].append(crash['path'])
                else:
                    if faults is not None:
                        faults.setdefault('<UNKNOWN>', []).append(crash['path'])
                    #    print "DEBUG: a new fault with ALREADY known trace path found.\nDump: %s\nCalls:\n%s" % (
                    #        crash['path'], formated_calls
                    #    )
                    #print "Uploaded at %s" % crash['upload']
                    self._lasts.set(ct, crash['path'], crash['upload'])
                    self._lasts.store()
                    #

        if faults is not None:
            unknown = faults.pop('<UNKNOWN>', None)
            sig_only = []
            buf = []
            for k in sorted(faults.keys(), key=lambda x: (len(faults[x]), x), reverse=True):
                if len(k) == 1:
                    sig_only.append(k)
                else:
                    buf.append(fault_case2str(k, faults[k], paths[k]))
            if sig_only:
                for k in sig_only:
                    buf.append(fault_case2str(k, faults[k], paths[k]))
            if unknown is not None:
                buf.append(fault_case2str(None, unknown, None))

            if buf:
                email_summary("\n".join(buf), mintime, maxtime)

            self._lasts.summary_tm = time.time()
            self._lasts.store()

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
