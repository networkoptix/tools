# -*- coding: utf-8 -*-
""" Some POSIX-only utilities for autotests
"""
__author__ = 'Danil Lavrentyuk'

try:
    import resource
    _NO_RESOURCE = False
except ImportError:
    _NO_RESOURCE = True

def fix_ulimit(new_limit):
    if _NO_RESOURCE:
        return
    val = resource.getrlimit(resource.RLIMIT_NOFILE)
    if new_limit > val[1]:
        print "WARNING! Configured open files limit (%s) is greater than the current hard limit (%s)" % (new_limit, val[1])
        new_limit = val[1]
    resource.setrlimit(resource.RLIMIT_NOFILE, (new_limit, val[1]))
    print "DEBUG: fix_ulimit: new RLIMIT_NOFILE: %s" % (resource.getrlimit(resource.RLIMIT_NOFILE),)


