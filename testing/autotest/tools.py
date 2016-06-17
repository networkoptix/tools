# -*- coding: utf-8 -*-
""" Miscellaneous classes and
"""
__author__ = 'Danil Lavrentyuk'

import errno, os, signal, sys, time, traceback
from subprocess import Popen, call as subcall

from .logger import debug

def _get_signals():
    d = {}
    for name in dir(signal):
        if name.startswith('SIG') and name[3] != '_':
            value = getattr(signal, name)
            if value in d:
                d[value].append(name)
            else:
                d[value] = [name]
    return d

SignalNames = _get_signals()

class Process(Popen):
    "subprocess.Popen extension"
    _sleep_reiod = 0.01

    def limited_wait(self, timeout):
        """@param timeout: float
        Returns True if timed out
        """
        stop = time.time() + timeout
        while self.poll() is None:
            if time.time() > stop: return True
            time.sleep(self._sleep_reiod)
        return False

def kill_proc(proc, sudo=False, what="test"):
    "Kills subproces under sudo"
    debug("Killing %s process %s", what, proc.pid)
    if sudo and os.name == 'posix':
        subcall(['/usr/bin/sudo', 'kill', str(proc.pid)], shell=False)
    else:
        os.kill(proc.pid, signal.SIGTERM)
        #subcall(['kill', str(proc.pid)], shell=False)


class RunTime(object):
    start = None
    @classmethod
    def go(cls):
        cls.start = time.time()

    @classmethod
    def report(cls):
        if cls.start is not None:
            spend = time.time() - cls.start
            hr = int(spend / 3600)
            mn = int((spend - hr*3600) / 60)
            ms = ("%.2f" % spend).split('.')[1]
            print "Execution time: %02d:%02d:%02d.%s" % (hr, mn, int(spend % 60), ms)


def get_platform():
    if os.name == 'posix':
        return 'POSIX'
    elif os.name == 'nt':
        return 'Windows'
    else:
        return os.name


class Build(object): #  contains some build-dependent global variables
    arch = ''
    bin_path = ''
    target_path = ''
    lib_path = ''
    qt_lib = ''

    @classmethod
    def load_vars(cls, conf, env, safe=False):
        _vars = dict()
        try:
            execfile(conf.BUILD_CONF_PATH, _vars)
        except IOError as err:
            if safe and err.errno == errno.ENOENT:
                return
            print "ERROR: Can't load build variables file: %s" % (err,)
            sys.exit(1)
        except Exception:
            print "ERROR: Failed to load build variables: " + traceback.format_exc()
            sys.exit(1)
        _vars['add_lib_path'](env) # used in exec_unittest only.
        cls.arch = _vars['ARCH']
        cls.target_path = _vars['TARGET_DIR']
        cls.bin_path = _vars['BIN_PATH']
        cls.lib_path = _vars['LIB_PATH']
        cls.qt_lib = _vars['QT_LIB']


