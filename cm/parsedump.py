#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
__author__ = 'Danil Lavrentyuk'
import sys
import os.path
import re
from subprocess import Popen, PIPE
from hashlib import md5
from argparse import ArgumentParser

root_path = "/home/danil/develop/devtools/ci"
filt_path = "/usr/bin/c++filt"

Faults = dict() # crash-path -> [filepaths]
NewPaths = dict() # filepath -> new_filepath
faults_fname = "faults.list"
store_base = 'dump_store'

Signal = None
Args = None


def demangle_names(names):
    try:
        p = Popen([filt_path], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate(input="\n".join(names))
    except Exception:
        print "DEBUG: call %s failed: %s" % (filt_path, sys.exc_info())
        return names
    if p.returncode:
        print "DEBUG: %s returned code %s. STDERR: %s" % (filt_path, p.returncode, err)
        return names
    newnames = out.split("\n")
    if len(names) != len(newnames):
        print "%s changed function names number: %s to %s" % (filt_path, len(names), len(newnames))
        return names
    return newnames

line_rx = re.compile("^([^\(]+)?(?:\(([^?]+)\))?\[([^\]]+)\]")

gdb_frame_rx = re.compile("^\#\d+\s+\w+ in (.+?) \(")
gdb_frame_sgort_rx = re.compile("^\#\d+\s+(.+?) \(")

crash_signal_rx = re.compile("^[^(]+\(\d+\)")

GDB_MARK = "Program terminated with signal"
GDB_MARK_LEN = len(GDB_MARK)

CDB_EXC = "   ExceptionCode: "
CDB_EXC_LEN = len(CDB_EXC)
CDB_PREMARK = "  *** Stack trace for last set context"
CDB_MARK = "Call Site"



def parse_crash(f, fpath):
    try:
        f.next() # skip one empty line
    except StopIteration:
        return []
    call_path = []
    call_file = ''
    for line in f:
        if line.rstrip() == '':
            break
        m = line_rx.match(line)
        if not m:
            print "ERROR in %s:\n\tcan't parse line: %s" % (fpath, line.rstrip())
            continue
        fn, func = m.group(1, 2)
        if func is not None:
            name, _ = func.split('+', 2)
            if len(name) > 0:
                call_path.append(name)
                continue
        if fn is not None and len(fn) > 0:
            call_file = fn
    return call_path if call_path else (['file:'+call_file,] if call_file != '' else [])

def parse_gdb(f, fpath):
    call_path = []
    fail_point = False
    for line in f:
        if not fail_point:
            if line.startswith('#0'):
                m = gdb_frame_rx.match(line) or gdb_frame_sgort_rx.match(line)
                if m:
                    name = m.group(1)
                    if name not in ('', '??'):
                        call_path.append(name)
                        fail_point = True
            elif line.startswith('(gdb)'):
                fail_point = True
        if line.startswith("Thread 1 "):
            break
    else:
        print "WARNING: no thread 1 found in ", fpath
        return call_path + ['<WARNING: no thread 1 found in gdb-bt!>']

    for line in f:
        m = gdb_frame_rx.match(line)
        if m:
            name = m.group(1)
            if name not in ('', '??'):
                call_path.append(name)
    return call_path

def cdb_skip_to_stack(f):
    for line in f:
        if line.startswith(CDB_MARK):
            return True
    return False

def parse_cdb(f, fpath):
    if not cdb_skip_to_stack(f):
        print "WARNING: No stack trace found in %s!" % fpath
        return []
    # here all lines from CDB_MARK to an emplty line is the calltstack
    call_path = []
    for line in f:
        line = line.rstrip()
        if line == '':
            break
        call_path.append(line)
    return call_path

def check_crash(line, stream):
    if line.strip() == '': # Search for the first empty line
        try:
            line = stream.next()
        except StopIteration:
            return None
        m = crash_signal_rx.match(line)
        if m:
            return m.group(0)
    return None

def check_gdb(line, stream):
    if line.startswith(GDB_MARK):
        signal = line[GDB_MARK_LEN:].strip()
        if signal.endswith('.'):
            signal = signal[:-1]
        try:
            num, name = signal.split(',')
            return "%s (%s)" % (name.lstrip(), num)
        except Exception, e:
            return "Unparsed signal %s (error %s)" % (signal, e)
    return None

def check_cdb(line, stream):
    if line.startswith(CDB_EXC):
        return line[CDB_EXC_LEN:].strip()
    if line.startswith(CDB_PREMARK):  # no exception line found!
        return 'UNKNOWN'
    return None

FORMATS = ('crash', 'gdb-bt', 'cdb-bt')
CHECKER = dict(zip(FORMATS, (check_crash, check_gdb, check_cdb)))
PARSER = dict(zip(FORMATS, (parse_crash, parse_gdb, parse_cdb)))


def parse_dump(stream, fmt, path):
    for line in stream:
        signal = CHECKER[fmt](line, stream)
        if signal is not None:
            return ['<%s>' % signal] + PARSER[fmt](stream, path)
    return None


def store_dump(data, key, fpath, fext, storage):
    dirname = os.path.join(storage, md5('\n'.join(key)).hexdigest() if key else 'UNTRACED')
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    #TODO make sure thr is directory uniq for each key!
    if not fext.startswith('.'):
        fext = '.' + fext
    fbase = md5(fpath).hexdigest()
    fname = os.path.join(dirname, fbase + fext)
    dup = 0
    while os.path.isfile(fname):
        fname = os.path.join(dirname, fbase + '-' + str(dup) + fext)
        dup += 1
    NewPaths[fpath] = fname
    with open(fname, 'wt') as f:
        print >>f, '[%s]\n' % (fpath,)
        f.writelines(data)


def read_and_parse(fmt, fpath):
    data = open(fpath).readlines()
    calls = parse_dump(iter(data), fmt, fpath)
    if calls is not None:
        print fpath
        calls = demangle_names(calls)
        print "\n".join("\t"+c for c in calls)
        return data, tuple(calls)
    else:
        return data, '<UNKNOWN>' # not a tuple, because <UNKNOWN> is a special key!

def main(fmt):
    base = os.path.join(root_path, fmt) # base directory where to store loaded files (with their subpaths)
    storage = os.path.join(root_path, store_base) # storage for downloaded dumps
    if Args.store and not os.path.isdir(storage):
        os.mkdir(storage)
    for dirpath, dirnames, filenames in os.walk(base):
        for fname in filenames:
            if fname.endswith('.' + fmt):
                fpath = os.path.join(dirpath, fname)
                original_path = fpath[len(base):]
                data, key = read_and_parse(fmt, fpath)
                Faults.setdefault(key, []).append(original_path)
                if Args.store:
                    store_dump(data, key, original_path, fmt, storage)


def print_fault_case(f, calls, fnames):
    if calls == None:
        print >>f, "<UNKNOWN>:"
    else:
        calls = demangle_names(calls)
        print >>f, "Key: %s" % repr(calls)
        print >>f, "Stack:"
        for func in calls:
            print >>f, "\t" + func
    print >>f, "Files (%s):" % len(fnames)
    for fname in fnames:
        print >>f, "\t%s" % (NewPaths[fname] if Args.store else fname,)
    print >>f


def singe_file_run(fname):
    fmt = Args.format if Args.format != 'all' else ''
    for s in FORMATS:
        if fname.endswith(s):
            fmt = s
            break
    if not fmt:
        print "Specify your file format"
        return
    data, key = read_and_parse(fmt, fname)
    print "Key: "


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument('format', choices=('all',) + FORMATS, default='all', help="Crash dump file format to parse. Default: all", metavar="FORMAT", nargs='?')
    parser.add_argument('-s', '--store', action='store_true', help="Store crash dump files in directories, groupped by trsce paths")
    parser.add_argument('-f', '--file', help="Parse the specified crash dump file, don't go to the crash server")
    Args = parser.parse_args()

    if Args.file is not None:
        singe_file_run(Args.file)
        sys.exit(0)
    else:
        for fmt in (FORMATS if Args.format == 'all' else [Args.format]):
            main(fmt)

    with open(os.path.join(root_path, faults_fname), "wt") as f:
        unknown = Faults.pop('<UNKNOWN>', None)
        sig_only = []
        for k in sorted(Faults.keys(), key=lambda x: (len(Faults[x]), x), reverse=True):
            if len(k) == 1:
                sig_only.append(k)
            else:
                print_fault_case(f, k, Faults[k])
        if sig_only:
            for k in sig_only:
                print_fault_case(f, k, Faults[k])
        if unknown is not None:
            print_fault_case(f, None, unknown)

