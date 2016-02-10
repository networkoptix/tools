#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
"""Known crash paths database handler"""
__author__ = 'Danil Lavrentyuk'

from hashlib import md5
import traceback
import os, os.path
import errno


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
                    self.hashes[key] = self.hash(key)
        except IOError, e:
            if e.errno == errno.ENOENT:
                print "%s not found, use empty list" % fname
            else:
                raise
        else:
            print "%s faults are known already" % len(self.crashes)

    @staticmethod
    def hash(key):
        return md5(''.join(key)).hexdigest()

    def iterhash(self):
        return self.hashes.iteritems()

    def has(self, key):
        return key in self.crashes

    def add(self, key):
        if key not in self.crashes:
            self.crashes[key] = None
            open(self.fname, "a").write("%r\n" % ([key],))

    def set_issue(self, key, issue):
        if key in self.crashes and self.crashes[key] is not None and self.crashes[key][0] != issue[0]:
            print "ERROR: Trying to owerride issue %s with %s" % (self.crashes[key], issue)
            return
        self.crashes[key] = issue
        open(self.fname, "a").write("%r\n" % ([key, issue],))
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

