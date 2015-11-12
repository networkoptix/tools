#!/usr/bin/python
__author__ = 'Danil Lavrentyuk'
"""Creates camera data storage directories and fills then with test data files.
Call with two necessary arguments -- base storage path and a camera physicalId
"""
import sys
import os
import os.path
import time
import shutil
import random

mypath = os.path.dirname(os.path.abspath(sys.argv[0]))
sample_path = os.path.join(mypath, 'sample.mkv')
if not os.path.isfile(sample_path):
    print "Sample file %s doesn't exist" % sample_path
    sys.exit(2)

SAMPLE_LEN = 65 # sample video length, in seconds
SAMPLE_LEN_MS = SAMPLE_LEN * 1000

if len(sys.argv) < 3:
    print "The base storage path argument is necessary!"
    sys.exit(1)

base_path = sys.argv[1]
camera = sys.argv[2]

if not os.path.isdir(base_path):
    print "The base storage directory %s isn't found!" % base_path
    sys.exit(2)

hi_path = os.path.join(base_path, 'hi_quality', camera)
low_path = os.path.join(base_path, 'low_quality', camera)

def mk(path, log=False):
    if not os.path.isdir(path):
        if log:
            print "Creating %s" % path
        os.makedirs(path)

mk(hi_path, False)
mk(low_path, False)

HOUR = 60*60
DAY = HOUR*24
START_OFFSET = 30 * DAY

time_base = int(time.time()) - START_OFFSET
time_dir_fmt = os.path.join("%s","%02d","%02d","%02d")

def time2path(dt):
    if dt < 1400000000:
        dt += time_base
    tm = time.gmtime(dt)
    return time_dir_fmt % tm[0:4]

def time2fn(t):
    return "%d_%d.mkv" % (int(t*1000), SAMPLE_LEN_MS)

RECORDED_PATHS = [ (p, time2path(p)) for p in  (t + time_base for t in ( p[0]*DAY+p[1]*HOUR for p in (
    (0, 1),  (0, 2),  (0, 3),  (0, 4),
    (1, 0),  (1, 1),  (1, 23),
    (2, 0),  (2, 1),  (2, 22), (2, 23),
    (3, 0),
    (4, 5),  (4, 6),
#    (8, 21), (8, 22), (8, 23),
#    (9, 0),  (9, 1),  (9, 2)
)))]  # it must be sirted!


def create_datepaths(base):
    for t, p in RECORDED_PATHS:
        mk(os.path.join(base, p))

create_datepaths(hi_path)
create_datepaths(low_path)

def fill_data():
    start = 0
    for tm, path in RECORDED_PATHS:
        end = tm+HOUR
        start = max(start, tm) + max(0, (random.random() * 60) - 15)
        #print "Start: %s, end %s, d %s" % (start, end, end-start)
        for i in xrange(random.randint(1, int((end-start)/65.0))):
            start += max(0, (random.random()-0.5)*3)
            if start >= end:
                break
            for base in (hi_path, low_path):
                dest = os.path.join(base, path, time2fn(start))
                #print "Copy %s to %s" % (sample_path, dest)
                shutil.copyfile(sample_path, dest)
            start += SAMPLE_LEN

fill_data()
