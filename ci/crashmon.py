#!/usr/bin/env python2
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
#import datetime
from subprocess import Popen, PIPE

from crashmonconf import *

filt_path = "/usr/bin/c++filt"

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
        print "Failed to get %s: %s" % (url, TB.format_exc())
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


class LastCrashTracker(object):
    name = 'LastTimes'

    def __init__(self, filename):
        self.fn = filename
        self.timestamps = {k: '' for k in CRASH_EXT}
        if os.path.isfile(filename):
            self.load()
            print 'Last loaded crashes times:'
            for ext in CRASH_EXT:
                print "%6s: %t" % (ext, self.timestamps[ext])
        self.changed = False

    def load(self):
        v = {}
        try:
            execfile(self.fn, v)
            for k, t in v[self.name]:
                if k in CRASH_EXT:
                    self.timestamps[k] = t
                else:
                    print "ERROR: unknown crash file extension found: %s" % k
        except Exception, e:
            print "ERROR: Failed to read last crash timestamps file %s" % self.fn
            sys.exit(2)

    def store(self):
        file(self.fn, 'w').write(LAST_CRASH_TIME_TPL % (self.name, self.timestamps))

    def __getitem__(self, item):
        return self.timestamps.get(item, 0)

    def set(self, ext, tm):
        if tm > self.get(ext):
            self.timestamps.get[ext] = tm
            self.changed = True

    def __str__(self):
        return "%s('%s', changed=%s, %s)" % (self.__class__.__name__, self.name, self.changed, self.timestamps)


class CrashMonitor(object):
    """
    The main class.
    Recurrent crash server checker. New crashes loader.
    """
    def __init__(self):
        # Setup the interruption handler
        self._stop = False
        self._lasts = LastCrashTracker(LASTS_FILE)
        signal.signal(signal.SIGINT,self._onInterrupt)

    def _onInterrupt(self, _signum, _stack):
        self._stop = True

    def updateCrashLists(self):
        "Loads crashes list from the crashserver, filters by last parsed crash times."
        crash_list = dict()
        for ct in CRASH_EXT:
            mark = self._lasts[ct]
            crash_list[ct] = sorted((v for v in get_crashes(ct) if v['upload'] > mark), key=lambda v: v['upload'])
            print "Loaded %s: %s new crashes" % (ct, len(crash_list[ct]))
            for crash in crash_list[ct]:
                lpath = crash['path']
                if lpath[0] == '/':
                    lpath = lpath[1:]
                url = DUMP_BASE + lpath
                try:
                    result = requests.get(url, auth=AUTH)
                    if result.status_code != 200:
                        print "Error reading %s: %s" % (lpath, result.status_code)
                        continue
                except Exception, e:
                    print "Error loading %s: %s" % (lpath, e)
                    continue
                data = result.content




    def run(self):
        "The main cyrcle."
        while not self._stop:
            self.updateCrashLists()
            # 2. parse new crashes
            # # 2.1 send mail for each new track
            # # 2.2 updated and store self._lasts for _each_ crash parsed
            time.sleep(CHECK_PERIOD)



if __name__ == '__main__':
    if get_lock(PROCESS_NAME):
        CrashMonitor().run()
    else:
        print "Another copy of process found. Lock name: " + PROCESS_NAME
        sys.exit(1)
