#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Known crash paths database handler"""
__author__ = 'Danil Lavrentyuk'

from hashlib import md5
import traceback
import os, os.path, re, copy
import errno
from collections import OrderedDict

WINAPICALL = 'winapicall'
EXEFILE = 'exefile!'

CALLS_TO_REPLACE = [
    # WIN API calls
    (r'(win32[a-z]!\w+)', WINAPICALL),
    (r'(user32!\w+)', WINAPICALL),
    (r'(kernel32!\w+)', WINAPICALL),
    (r'(ntdll!\w+)', WINAPICALL),
    # Name of EXE files
    (r'(Cox_Business_Security_Solutions!)', EXEFILE),
    (r'(DW_Spectrum!)', EXEFILE),
    (r'(DW_Spectrum_Global!)', EXEFILE),
    (r'(EZ_Pro!)', EXEFILE),
    (r'(FlyView!)', EXEFILE),
    (r'(Nx_Witness_Chinese!)', EXEFILE),
    (r'(HD_Witness!)', EXEFILE),
    (r'(NTN!)', EXEFILE),
    (r'(PCMS!)', EXEFILE),
    (r'(Qulu!)', EXEFILE),
    (r'(Sentry_Matrix!)', EXEFILE),
    (r'(Tricom_MVSS!)', EXEFILE),
    (r'(VMS_Demonstration!)', EXEFILE),
    (r'(VMS_Smart_Client!)', EXEFILE),
    (r'(nvision!)', EXEFILE) ]
    
CALLS_TO_REMOVE = [ '0x0' ]
    
class KnowCrashDB(object):

    class CrashInfo(object):

        def __init__(self, issue = None, priority = None, faults = None):
            self.issue = issue
            self.priority = priority
            self.faults = faults or 1

        def setIssue(self, issue, priority):
            self.issue = issue
            self.priority = priority

        def resetIssue(self):
            self.issue = None
            self.priority = None

        def get(self):
            return (self.issue, self.priority, self.faults)

    def __init__(self, fname):
        # It doesn't open db here to allow global initialization
        self.fname = fname
        self.crashes = dict()
        self.hashes = dict()
        self.changed = False
        cnt = 0
        try:
            with open(fname) as f:
                for line in f:
                    cnt += 1
                    if line.strip() == '': continue
                    try:
                        val = eval(line)
                    except Exception, e:
                        print "Error parsing known crashes file's line %s: %s" % (cnt, e)
                        continue
                    key = val[0]
                    #TODO add priority here!
                    self.crashes[key] = self.CrashInfo(*val[1]) if len(val) > 1 else self.CrashInfo()
                    self.hashes.setdefault(self.hash(key), []).append(key)
        except IOError, e:
            if e.errno == errno.ENOENT:
                print "%s not found, use empty list" % fname
            else:
                raise
        else:
            print "%s faults are known already" % len(self.crashes)

    @staticmethod
    def prepare2hash(key):
        calls = filter(lambda c: c not in CALLS_TO_REMOVE, key)
        def replace(call):
            call_new = call
            for exp, sub in CALLS_TO_REPLACE:
                call_new = re.sub(exp, sub, call_new)
            return call_new
        return tuple(OrderedDict.fromkeys(map(replace, calls)))[0:4]

    @staticmethod
    def hash(key):
        return md5(''.join(KnowCrashDB.prepare2hash(key))).hexdigest()

    def has(self, key):
        return key in self.crashes

    def add(self, key):
        if key not in self.crashes:
            hashval = self.hash(key)
            # Get min issue number
            crashinfos = map(lambda k: self.crashes.get(k), self.hashes.get(hashval, []))
            crashinfos = filter(lambda x: x, crashinfos)
            crashinfo = None
            if crashinfos:
                crashinfos.sort(key=lambda x: x.issue)
                crashinfo = crashinfos[0]
                crashinfo.faults = 1
                self.crashes[key] = copy.deepcopy(crashinfo)
            else:
                self.crashes[key] = self.CrashInfo()
            self.hashes.setdefault(hashval, []).append(key)
            open(self.fname, "a").write("%r\n" % ([key, self.crashes[key].get()]))
            self.changed = True

    def set_issue(self, key, issue):
        #if key in self.crashes and self.crashes[key] is not None and self.crashes[key][0] != issue[0]:
        #    print "ERROR: Trying to owerride issue %s with %s" % (self.crashes[key], issue)
        #    return
        for k in self.hashes[self.hash(key)]:
            if issue:
                self.crashes[k].setIssue(*issue)
            else:
                self.crashes[k].resetIssue()
            open(self.fname, "a").write("%r\n" % ([k, self.crashes[k].get()],))
            self.changed = True

    def get_and_incr_faults(self, key):
        crashinfo = self.crashes.get(key)
        if crashinfo:
            crashinfo.faults += 1
            self.changed = True
        return crashinfo

    def get_faults(self, key):
        hashval = self.hash(key)
        crashinfos = map(lambda k: self.crashes.get(k, self.CrashInfo()), self.hashes.get(hashval, []))
        return sum(map(lambda x: x.faults, crashinfos))

    def rewrite(self):
        print "Known crashed table was updated. Rewriting it's file."
        tmpname = self.fname + '.tmp'
        try:
            with open(tmpname, "w") as out:
                for key, crashinfo in self.crashes.iteritems():
                    out.write("%r\n" % ([key, crashinfo.get()]))
                out.close()
            if os.path.isfile(self.fname) and os.name == 'nt':
                os.remove(self.fname)
            os.rename(tmpname, self.fname)
            self.changed = False
        except Exception:
            print "Error rewritting known crashes file: %s" % (traceback.format_exc(),)
