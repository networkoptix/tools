#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Known crash paths database handler"""
__author__ = 'Danil Lavrentyuk'

from hashlib import md5
import traceback
import os, os.path, re
import errno

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
                    self.crashes[key] = val[1] if len(val) > 1 else None
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
        return map(replace, calls)

    @staticmethod
    def hash(key):
        return md5(''.join(KnowCrashDB.prepare2hash(key))).hexdigest()

    def has(self, key):
        return key in self.crashes

    def add(self, key):
        if key not in self.crashes:
            hashval = self.hash(key)
            self.crashes[key] = None
            self.hashes.setdefault(hashval, []).append(key)
            open(self.fname, "a").write("%r\n" % ([key],))

    def set_issue(self, key, issue):
        #if key in self.crashes and self.crashes[key] is not None and self.crashes[key][0] != issue[0]:
        #    print "ERROR: Trying to owerride issue %s with %s" % (self.crashes[key], issue)
        #    return
        for k in self.hashes[self.hash(key)]:
            self.crashes[k] = issue
            open(self.fname, "a").write("%r\n" % ([k, issue],))
            self.changed = True

    def rewrite(self):
        print "Known crashed table was updated. Rewriting it's file."
        tmpname = self.fname + '.tmp'
        try:
            with open(tmpname, "w") as out:
                for key, issue in self.crashes.iteritems():
                    out.write("%r\n" % ([key, issue] if issue is not None else [key],))
                out.close()
            if os.path.isfile(self.fname) and os.name == 'nt':
                os.remove(self.fname)
            os.rename(tmpname, self.fname)
            self.changed = False
        except Exception:
            print "Error rewritting known crashes file: %s" % (traceback.format_exc(),)

