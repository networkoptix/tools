#!/usr/bin/env python -u
# -*- coding: UTF-8 -*-
__author__ = 'Danil Lavrentyuk'
""" Load a crash reports list from the crashserver.
"""
import requests
import traceback as TB
import sys
import os
import os.path

from crashmonconf import *

__all__ = ['get_crashes']

def get_crashes(crtype):
    print "Getting %s data" % crtype
    url = crash_list_url(crtype)
    res = requests.get(url, auth = AUTH)
    if res.status_code != 200:
        print "Error: %s" % (res.status_code)
        return None
    try:
        return res.json()
    except Exception:
        print "Failed to get %s: %s" % (url, TB.format_exc())


def check_uniq(data):
    u = {rec['path'] for rec in data}
    return len(u) == len(data)


def ensure_path(p):
    parts = p.split('/')
    subpath = '.'
    for d in parts[:-1]:
        if d == '.':
            continue
        subpath += '/' + d
        if not os.path.isdir(subpath):
            print "(Create dir %s)" % subpath
            os.mkdir(subpath)

def main():
    crash_list = dict()
    for ct in CRASH_EXT:
        print "[[ %s ]]" % ct
        crash_list[ct] = get_crashes(ct)

    dupes = False
    for ct in CRASH_EXT:
        ok = check_uniq(crash_list[ct])
        print "Uniq url check for %s: %s" % (ct, ('OK' if ok else 'FAIL'))
        dupes = dupes or (not ok)

    if dupes:
        print "Duplicate URLs found. Exitting"
        sys.exit(10)

    done_paths = {ct: [] for ct in CRASH_EXT}

    for ct in CRASH_EXT:
        dir = os.path.join(".", ct)
        print "[[ %s ]]" % dir
        for rec in crash_list[ct]:
            if load_dump(rec, dir):
                done_paths[ct].append(fn)
            lpath = rec['path']
            if lpath[0] == '/':
                lpath = lpath[1:]
            url = DUMP_BASE + lpath
            fn = os.path.join(dir, lpath)
            if os.path.isfile(fn):
                print "Already exists: " + fn
                done_paths[ct].append(fn)
                continue
            ensure_path(fn)
            result = requests.get(url, auth=AUTH)
            if result.status_code != 200:
                print "Error reading %s: %s" % (lpath, result.status_code)
                continue
            print "Saving: " + fn
            with open(fn, "w") as f:
                f.write(result.content)
            done_paths[ct].append(fn)

    for ct in CRASH_EXT:
        with open(ct + ".list", "wt") as f:
            for fn in done_paths[ct]:
                print >>f, fn

def load_dump(rec, dir_to):
    lpath = rec['path']
    if lpath[0] == '/':
        lpath = lpath[1:]
    fn = os.path.join(dir_to, lpath)
    if os.path.isfile(fn):
        print "Already exists: " + fn
        return True
    ensure_path(fn)
    url = DUMP_BASE + lpath
    result = requests.get(url, auth=AUTH)
    if result.status_code != 200:
        print "Error reading %s: %s" % (lpath, result.status_code)
        return False
    print "Saving: " + fn
    with open(fn, "w") as f:
        f.write(result.content)
    return True


if __name__ == '__main__':
    main()
