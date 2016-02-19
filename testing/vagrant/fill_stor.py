#!/usr/bin/python
__author__ = 'Danil Lavrentyuk'
"""Creates camera data storage directories and fills then with test data files.
Call with 4 necessary arguments:
    - data filling mode: random, multiserv, ms-gen
    - the base storage path
    - a camera physicalId
    - test specific:
      - a test step for 'random' mode
      - a server number for 'multiserv' mode

"""
import sys
import os
import os.path
import time
import shutil
import random

mypath = os.path.dirname(os.path.abspath(sys.argv[0]))
sample_path = os.path.join(mypath, 'sample.mkv')
#WARNING! It changes the sample start time, recorded in the sample file, so changing that file format you MUST modify this script!
if not os.path.isfile(sample_path):
    print "Sample file %s doesn't exist" % sample_path
    sys.exit(2)

SAMPLE_LEN = 65 # sample video length, in seconds
SAMPLE_LEN_MS = SAMPLE_LEN * 1000

HOUR = 60*60
DAY = HOUR*24

def mkpath(path, log=False):
    if not os.path.isdir(path):
        if log:
            print "Creating %s" % path
        os.makedirs(path)


def mk_base_time(offset):
    """ Finds the moment in the past by offset from the current moment,
    then truncate down to the nearest hour border.
    """
    t = int(time.time())
    gt = time.gmtime(t)
    return t - gt.tm_sec - gt.tm_min * 60 - offset


def time2path(dt):
    """Generates subdirectories path for video files, based on date and hour: YEAR/MONTH/DAY/HOUR
    """
    if dt < 1400000000:
        dt += time_base
    tm = time.gmtime(dt)
    return time_dir_fmt % tm[0:4]


def time2fn(t):
    "Creates a recorded video file name by format START_LENGTH.mkv, where START and LENGTH are mesured in miliseconds."
    return "%d_%d.mkv" % (int(t*1000), SAMPLE_LEN_MS)


def mk_rec_path(d, h):
    """Creates timestamp and subdirectories path for specified day and hour since time_base
    """
    t = d*DAY + h*HOUR + time_base
    return t, time2path(t)


if len(sys.argv) < 5:
    print "Not enough parameters!"
    sys.exit(1)

run_mode, base_path, camera, special = sys.argv[1:5]

generate_mode = False
genfile = None
if run_mode == 'ms-gen':
    generate_mode = True
    run_mode = 'multiserv'
    genfile = open("fill_stor_data_%s.dat" % special, 'w')

if run_mode not in ['random', 'multiserv']:
    print "Wrong mode: '%s'" % run_mode
    sys.exit(1)

if not generate_mode and not os.path.isdir(base_path):
    print "The base storage directory %s isn't found!" % base_path
    sys.exit(2)

START_OFFSET = {
    'random': 10 * DAY,
    'multiserv': 3 * DAY,
} [run_mode]

time_base =  mk_base_time(START_OFFSET)
time_dir_fmt = os.path.join("%s","%02d","%02d","%02d")

RANDOM_FILL_PATHS = {k: [mk_rec_path(*p) for p in v] for k, v in (
    ('step1', (
        (0, 1),  (0, 2),  (0, 3),  (0, 4),
        (1, 0),  (1, 1),  (1, 23),
        (2, 0),  (2, 1),  (2, 22), (2, 23),
        (3, 0),
    )),
    ('step2', (
        (4, 5),  (4, 6),  (4, 7),  (4, 20),
        (5, 21), (5, 22), (5, 23),
        (6, 0),  (6, 1),  (6, 2),
    )),
)}


def create_datepaths(base):
    for t, p in RANDOM_FILL_PATHS[special]:
        mkpath(os.path.join(base, p))


def create_datepaths_short(base): # a shorten debug version
    for t, p in RANDOM_FILL_PATHS[special][:1]:
        mkpath(os.path.join(base, p))


def fill_data_random():
    start = 0
    for tm, path in RANDOM_FILL_PATHS[special]:
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


def fill_data_short(): # a shorten debug version
    tm, path = RANDOM_FILL_PATHS[0]
    start = tm
    #print "Start: %s, end %s, d %s" % (start, end, end-start)
    start += max(0, (random.random()-0.5)*3)
    for base in (hi_path, low_path):
        dest = os.path.join(base, path, time2fn(start))
        print "Copy %s to %s" % (sample_path, dest)
        shutil.copyfile(sample_path, dest)
    start += SAMPLE_LEN


MULTISERV_FILL_TEMPALTE = { # a sample how to fill one hour
    '0': ((0, 300), (481, 720), (1401, 1800), (2131, 2550), (3000, 3333)),
    '1': ((301, 480), (721, 1400), (1801, 2130), (2551, 2999), (3334, 3599)),
}

def _choose_multiserv_base_dir(varpath):
    return random.randint(0,1) if generate_mode else random.choice(varpath)

TIME_MARK = 'START_TIMED'
TIME_MARK_LEN = len(TIME_MARK)
TIME_MARK_POS = 537 # Note: this position could depend on the sample file, check it if you change that file
TIME_STAMP_POS = TIME_MARK_POS + TIME_MARK_LEN + 2

def verify_timestamp_mark():
    global TIME_MARK_POS
    with open(sample_path, "rb") as f:
        f.seek(TIME_MARK_POS)
        data = f.read(TIME_MARK_LEN)
        if data == TIME_MARK:
            return
        print "No time mark %s found at position %s" % (TIME_MARK, TIME_MARK_POS)
        # now try to find it
        buf = ''
        offset = 0
        f.seek(0)
        while True:
            data = f.read(4096)
            if len(data) == 0:
                print "ERROR! Can't find place for the start timestamp in the sample file"
                sys.exit(3)
            buf += data
            p = buf.find(TIME_MARK)
            if p > -1:
                TIME_MARK_POS = offset + p
                global TIME_STAMP_POS
                TIME_STAMP_POS = TIME_MARK_POS + TIME_MARK_LEN + 2
                print "New time mark position found: %s" % TIME_MARK_POS
                return
            else:
                offset += len(buf) - TIME_MARK_LEN
                buf = buf[-TIME_MARK_LEN:]


def copy_sample(dest, timestr):
    shutil.copyfile(sample_path, dest)
    with open(dest, "r+b") as f:
        f.seek(TIME_STAMP_POS)
        f.write(timestr)


def fill_data_multiserv(serv):
    template = MULTISERV_FILL_TEMPALTE[serv]
    for h in xrange(START_OFFSET / HOUR):
        ht = h * HOUR
        p = time2path(time_base + ht)
        varpath = (os.path.join(hi_path, p), os.path.join(low_path, p))
        if not generate_mode:
            mkpath(varpath[0])
            mkpath(varpath[1])
        base = _choose_multiserv_base_dir(varpath)
        t = ht
        for begin, end in template:
            t = max(t, ht +  begin)
            pre_end = ht + end - SAMPLE_LEN
            while t < pre_end:
                if generate_mode:
                    print  >>genfile, "%s %d %d" % ('hi' if base == 0 else 'lo', ht, t-ht)
                else:
                    fn = time2fn(time_base + t)
                    dest = os.path.join(base, fn)
                    print "Copy %s to %s" % (sample_path, dest)
                    copy_sample(dest, fn[:13]) # NOTE: the first 13 chars in the file name is this chank start time in milliseconds
                    #TODO: modify destination file start time!
                newbase = _choose_multiserv_base_dir(varpath)
                if newbase == base:
                    t += SAMPLE_LEN
                else: # in differend path (high or low) samples may overlap
                    t += int(SAMPLE_LEN * (0.5 + random.random() / 2))
                base = newbase


def fill_data_multi(serv):
    fpath = os.path.join(mypath, "multiserv_starts.py")
    if not os.path.isfile(fpath):
        print "Pregenereated start times not found! Run random multiserv filling."
        fill_data_multiserv(serv)
        return
    tmp = {}
    execfile(fpath, tmp)
    chunk_starts = tmp['chunk_starts'][serv]
    for part in ('hi', 'lo'):
        base = hi_path if part == 'hi' else low_path
        for hour, starts in chunk_starts[part]:
            ht = time_base + hour
            subdir = os.path.join(base, time2path(ht))
            mkpath(subdir)
            for t in starts:
                fn = time2fn(time_base + hour + t)
                dest = os.path.join(subdir, fn)
                print "Copy %s to %s" % (sample_path, dest)
                copy_sample(dest, fn[:13]) # NOTE: the first 13 chars in the file name is this chank start time in milliseconds
                #TODO: modify destination file start time!


hi_path = os.path.join(base_path, 'hi_quality', camera)
low_path = os.path.join(base_path, 'low_quality', camera)

if not generate_mode:
    mkpath(hi_path, False)
    mkpath(low_path, False)

if run_mode == 'random':
    if special not in RANDOM_FILL_PATHS.iterkeys():
        print "Wrong step value: %s. Allowed values: %s" % (special, ', '.join(RANDOM_FILL_PATHS.iterkeys()))
        sys.exit(3)
    create_datepaths(hi_path)
    create_datepaths(low_path)
    fill_data_random()
elif run_mode == 'multiserv':
    verify_timestamp_mark()
    if special not in MULTISERV_FILL_TEMPALTE:
        print "Wrong server number value: %s. Allowed values: %s" % (special, ', '.join(MULTISERV_FILL_TEMPALTE.iterkeys()))
        sys.exit(3)
    if generate_mode:
        fill_data_multiserv(special)
    else:
        fill_data_multi(special)
else:
    print "Unknown mode: '%s'" % run_mode

if genfile:
    genfile.close()
