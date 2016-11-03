#!/usr/bin/env python
__author__ = 'Danil Lavrentyuk'
import sys
import os
import os.path
import pprint
from gen2py import combine_iter

SAMPLE_LEN = 65 # sample video length, in seconds
SAMPLE_LEN_MS = SAMPLE_LEN * 1000

mypath = os.path.dirname(os.path.abspath(sys.argv[0]))

src_file_name = os.path.join(mypath, "multiserv_starts.py")
dest_file_name = os.path.join(mypath, "multiserv_intervals.py")

if not os.path.isfile(src_file_name):
    print "Pregenereated start times not found!"
    sys.exit(1)

joined = [] # list of intervals for both servers joined
single = [[], []] # pair of lists for separated server

tmp = {}
execfile(src_file_name, tmp)
chunk_starts = tmp['chunk_starts']

dest = open(dest_file_name, "wt")

for s in ('0', '1'):
    serv = int(s)
    last_element = None
    last_end = -1
    single[serv] = data = []
    for start in combine_iter(chunk_starts[s]):
        #print "last_end %s, start %s" % (last_end, start),
        if start > last_end:
            #print "make new element"
            last_element = {
                "start": start * 1000,
                "duration": SAMPLE_LEN_MS
            }
            data.append(last_element)
        else:
            #print "extend"
            last_element["duration"] += SAMPLE_LEN_MS - (last_end - start) * 1000
        last_end = start + SAMPLE_LEN
        last_element["last_end"] = last_end * 1000

print >>dest, "time_periods_single = " + pprint.pformat(single, width=80)
print >>dest

p = [0, 0]
last_end = -1
last_element = None
last_i = -1
while p[0] < len(single[0]) or p[1] < len(single[1]):
    if p[0] < len(single[0]) and p[1] < len(single[1]):
        if single[0][p[0]]["start"] == single[1][p[1]]["start"]:
            print "Equal starts at serv0[%s] and serv1[%s]!" % p
            sys.exit(2)
        i = 0 if single[0][p[0]]["start"] < single[1][p[1]]["start"] else 1
    elif p[0] >= len(single[0]):
        i = 1
    elif p[1] >= len(single[1]):
        i = 0
    else:
        print "Can't choose i!"
        sys.exit(2)
    new_start = single[i][p[i]]["start"]
    if new_start < last_end:
        if last_i != i:
            if last_i is None:
                last_i = i
            else:
                print "Intersection between servers at time mark %s" % single[i][p[i]]["start"]
                sys.exit(2)
        else:
            print "Unjoined intersection at server %s at time mark %s" % (i, single[i][p[i]]["start"])
            sys.exit(2)
    else:
        if last_i == i:
            print "Unjoined connection at server %s at time mark %s" % (i, single[i][p[i]]["start"])
            sys.exit(2)
        last_i = i
        if new_start == last_end:
            last_element["duration"] += single[i][p[i]]["duration"]
            print "# Joined servers (new - %s) at position %s" % (i, new_start)
        else:
            last_element = {
                "start": new_start,
                "duration": single[i][p[i]]["duration"]
            }
            joined.append(last_element)
    p[i] += 1


print >>dest, "time_periods_joined = " + pprint.pformat(joined, width=80)

