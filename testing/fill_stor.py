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
    print "The base storage path and a camera physical id arguments are necessary!"
    sys.exit(1)

base_path = sys.argv[1]
camera = sys.argv[2]
step = sys.argv[3] if len(sys.argv) >= 4 else 'step1'

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
START_OFFSET = 10 * DAY


def mk_base_time(offset):
    t = int(time.time())
    gt = time.gmtime(t)
    return t - gt.tm_sec - gt.tm_min * 60 - offset

time_base =  mk_base_time(START_OFFSET)
time_dir_fmt = os.path.join("%s","%02d","%02d","%02d")


def time2path(dt):
    if dt < 1400000000:
        dt += time_base
    tm = time.gmtime(dt)
    return time_dir_fmt % tm[0:4]


def time2fn(t):
    return "%d_%d.mkv" % (int(t*1000), SAMPLE_LEN_MS)

def mk_rec_path(d, h):
    t = d*DAY + h*HOUR + time_base
    return t, time2path(t)

RECORDED_PATHS = { k: [mk_rec_path(*p) for p in v] for k, v in (
    ('step1', (
        (0, 1),  (0, 2),  (0, 3),  (0, 4),
        (1, 0),  (1, 1),  (1, 23),
        (2, 0),  (2, 1),  (2, 22), (2, 23),
        (3, 0),
    )),
    ('step2', (
        (4, 5),  (4, 6),  (4, 20),
        (5, 21), (5, 22), (5, 23),
        (6, 0),  (6, 1),  (6, 2),
    )),
)}

if step not in RECORDED_PATHS.iterkeys():
    print "Wrong step value: %s. Allowed values: %s" % (step, ', '.join(RECORDED_PATHS.iterkeys()))
    sys.exit(3)

#print "DEBUG: step %s recorded paths: %s" % (step, RECORDED_PATHS[step])

def create_datepaths(base):
    for t, p in RECORDED_PATHS[step]:
        mk(os.path.join(base, p))

def create_datepaths_(base): # the shorten debug version
    for t, p in RECORDED_PATHS[step][:1]:
        mk(os.path.join(base, p))

create_datepaths(hi_path)
create_datepaths(low_path)

def fill_data():
    start = 0
    for tm, path in RECORDED_PATHS[step]:
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

def fill_data_(): # the shorten debug version
    tm, path = RECORDED_PATHS[0]
    start = tm
    #print "Start: %s, end %s, d %s" % (start, end, end-start)
    start += max(0, (random.random()-0.5)*3)
    for base in (hi_path, low_path):
        dest = os.path.join(base, path, time2fn(start))
        print "Copy %s to %s" % (sample_path, dest)
        shutil.copyfile(sample_path, dest)
    start += SAMPLE_LEN


fill_data()
