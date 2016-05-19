#!/usr/bin/env python
# -*- coding: utf-8 -*-
#TODO: ADD THE DESCRIPTION!!!
import sys, os, os.path, time, re
from subprocess import Popen, PIPE, STDOUT, CalledProcessError, check_call, check_output, call as subcall
from collections import deque, namedtuple
import errno
import traceback
import argparse
from smtplib import SMTP
from email import MIMEText
import signal
import shutil
import urllib2
import json
import xml.etree.ElementTree as ET

# Always chdir to the scripts directory
rundir = os.path.dirname(sys.argv[0])
if rundir not in ('', '.') and rundir != os.getcwd():
    os.chdir(rundir)

import testconf as conf
import pipereader
from testbase import boxssh
from functest_util import args2str, real_caps

__version__ = '1.2.2'

SUITMARK = '[' # all messages from a testsuit starts with it, other are tests' internal messages
FAILMARK = '[  FAILED  ]'
STARTMARK = '[ RUN      ]'
BARMARK = '[==========]'
OKMARK = '[       OK ]'

NameRx = re.compile(r'\[[^\]]+\]\s(\S+)')

RESULT = []


def get_signals():
    d = {}
    for name in dir(signal):
        if name.startswith('SIG') and name[3] != '_':
            value = getattr(signal, name)
            if value in d:
                d[value].append(name)
            else:
                d[value] = [name]
    return d

SignalNames = get_signals()

class FuncTestError(RuntimeError):
    pass

FailedTests = []
Changesets = {}
Env = os.environ.copy()
Args = {}


class Build(object): #  contains some build-dependent global variables
    arch = ''
    bin_path = ''
    target_path = ''

    @classmethod
    def load_vars(cls, safe=False):
        vars = dict()
        try:
            execfile(conf.BUILD_CONF_PATH, vars)
        except IOError as err:
            if safe and err.errno == errno.ENOENT:
                return
            print "ERROR: Can't load build variables file: " + err
            sys.exit(1)
        except Exception:
            print "ERROR: Failed to load build variables: " + traceback.format_exc()
            sys.exit(1)
        vars['add_lib_path'](Env)
        cls.arch = vars['ARCH']
        cls.target_path = vars['TARGET_DIR']
        cls.bin_path = vars['BIN_PATH']


class Process(Popen):
    "subprocess.Popen extension"
    _sleep_reiod = 0.05

    def limited_wait(self, timeout):
        "@param timeout: float"
        stop = time.time() + timeout
        while self.poll() is None:
            time.sleep(self._sleep_reiod)
            if time.time() < stop: break


def logPrint(s):
    print s


def logStr(text, *args):
    return "[%s] %s" % (time.strftime("%Y.%m.%d %X %Z"), ((text % args) if args else text))


def log(text, *args):
    text = logStr(text, *args)
    logPrint(text)
    return text


class ToSend(object):
    "Logs accumulator, singleton-class (no objects created)."
    lines = []
    last_line_src = ''
    empty = True
    flushed = False

    @classmethod
    def append(cls, text, *args):
        cls.last_line_src = text
        if text != '':
            text = logStr(text, *args)
        cls.empty = False
        if Args.stdout and cls.flushed:
            logPrint(text)
        else:
            cls.lines.append(text)

    @classmethod
    def count(cls):
        return len(cls.lines)

    @classmethod
    def log(cls, text, *args):
        cls.last_line_src = text
        if text != '':
            text = logStr(text, *args)
        logPrint(text)
        cls.empty = False
        if not Args.stdout:
            cls.lines.append(text)

    @classmethod
    def debug(cls, text):
        if not (Args.stdout and cls.flushed):
            cls.last_line_src = text
            cls.lines.append(logStr("[dup] " + text))

    @classmethod
    def flush(cls):
        # used only with -o mode
        if Args.stdout and not cls.flushed:
            cls.flushed = True
            for text in cls.lines:
                logPrint(text)
            del cls.lines[:]

    @classmethod
    def clear(cls):
        del cls.lines[:]
        cls.empty = True
        cls.flushed = False
        cls.last_line_src= ''

    @classmethod
    def lastLineAppend(cls, text):
        if cls.lines:
            cls.lines[-1] += text
        else:
            cls.log("INTERNAL ERROR: tried to append text to the last line when no lines collected.\n"
                    "Text to append: " + text + "\n"
                    "Called from: " + traceback.format_stack())

    @classmethod
    def cutLastLine(cls):
        if cls.lines:
            del cls.lines[-1]


def debug(text, *args):
    if conf.DEBUG:
        if args:
            text = text % args
        text = "DEBUG: " + text
        logPrint(text)
        ToSend.debug(text)

def email_send(mailfrom, mailto, cc, msg):
    msg['From'] = mailfrom
    msg['To'] = mailto
    if cc:
        if isinstance(cc, basestring):
            cc = [cc]
        mailto = [mailto] + cc
        msg['Cc'] = ','.join(cc)
    smtp = SMTP(conf.SMTP_ADDR)
    if conf.SMTP_LOGIN:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(conf.SMTP_LOGIN, conf.SMTP_PASS)
    #smtp.set_debuglevel(1)
    smtp.sendmail(mailfrom, mailto, msg.as_string())
    smtp.quit()


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


def email_notify(branch, lines):
    text = (
        ("Branch %s tests run report.\n\n" % branch) +
        "\n".join(lines) +
        ("\n\n[Finished at: %s]\n" % time.strftime("%Y.%m.%d %H:%M:%S (%Z)")) + "\n" +
        format_changesets(branch) + "\n"
    )
    msg = MIMEText.MIMEText(text)
    msg['Subject'] = "Autotest run results on %s platform" % get_platform()
    email_send(conf.MAIL_FROM, conf.MAIL_TO, conf.BRANCH_CC_TO.get(branch, []), msg)


def email_build_error(branch, loglines, unit_tests, crash=False, single_project=None, dep_error=None):
    bstr = ("%s unit tests" % branch) if unit_tests else branch
    cause = ("Error building branch " + bstr) if not crash else (("Branch %s build crashes!" % bstr) + crash)
    if single_project:
        special = 'Failed build was restarted for the single failed project: %s\n\n' % single_project
    elif dep_error:
        special = ("DEPENDENCY ERROR DETECTED!\n"
                   "Multithread build has failed on '%s', but singlethreaded has succeeded." % dep_error)
    else:
        special = ''
    text = (
        format_changesets(branch) + "\n\n" +
        special +
        ("%s\nThe build log last %d lines are:\n" % (cause, len(loglines))) +
        "".join(loglines) + "\n"
    )
    if Args.stdout:
        print text
    else:
        msg = MIMEText.MIMEText(text)
        msg['Subject'] = "Autotest scriprt fails to build the branch %s on %s platform" % (bstr, get_platform())
        email_send(conf.MAIL_FROM, conf.MAIL_TO, conf.BRANCH_CC_TO.get(branch, []), msg)


#####################################

class FailTracker(object):
    fails = set()

    @classmethod
    def mark_success(cls, branch):
        if branch in cls.fails:
            debug("Removing failed-test-mark from branch %s", branch)
            cls.fails.discard(branch)
            cls.save()
            ToSend.log('')
            ToSend.log("The branch %s is repaired after previous errors and makes no error now.", branch)
            if (branch in conf.SKIP_TESTS and conf.SKIP_TESTS[branch]) or conf.SKIP_ALL:
                ToSend.log("Note, that some tests have been skipped due to configuration.\nSkipped tests: %s",
                            ', '.join(conf.SKIP_TESTS.get(branch, set()) | conf.SKIP_ALL))

    @classmethod
    def mark_fail(cls, branch):
        if branch not in cls.fails:
            cls.fails.add(branch)
            cls.save()
            log("The branch %s marked as failed.", branch)

    @classmethod
    def load(cls):
        data = ''
        cls.fails =  set()
        if not os.path.isfile(conf.FAIL_FILE):
            return
        try:
            with open(conf.FAIL_FILE) as f:
                data = ' '.join(f.readlines()).strip()
        except IOError, e:
            log("Failed branches list file load error: %s", e) #TODO some another log is required to easily find such messages
            return
        if  data == '':
            debug("No branches was failed earlie")
            return
        try:
            cls.fails = eval(data)
        except Exception, e:
            log("Failed branches list parsing: %s", e)
        #debug("Failed branches list loaded: %s", ', '.join(FailTracker.fails))

    @classmethod
    def save(cls):
        debug("FailTracker.save: %s", cls.fails)
        try:
            with open(conf.FAIL_FILE, "w") as f:
                print >>f, repr(cls.fails)
        except Exception, e:
            ToSend.log("Error saving failed branches list: %s", e)


def check_restart():
    if os.path.isfile(conf.RESTART_FLAG):
        log("Restart flag founnd. Calling: %s", ([sys.executable] + sys.argv,))
        try:
            if conf.RESTART_BY_EXEC:
                sys.stdout.flush()
                sys.stderr.flush()
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                proc = Process([sys.executable] + sys.argv, shell=False)
                log("New copy of %s started with PID %s", sys.argv[0], proc.pid)
                timeout = time.time() + conf.SELF_RESTART_TIMEOUT
                while os.path.isfile(conf.RESTART_FLAG):
                    if time.time() > timeout:
                        raise RuntimeError("Can't start the new copy of process: restart flag hasn't been deleted for %s seconds" % SELF_RESTART_TIMEOUT)
                    time.sleep(0.1)
                log("The old proces goes away.")
                sys.exit(0)
        except Exception:
            log("Failed to restart: %s", traceback.format_exc())
            drop_flag(conf.RESTART_FLAG)


def get_file_time(fname):
    """
    Gets the file last modification time or 0 on any file access errors
    :param fname: string
    :return: int
    """
    try:
        if not os.path.isfile(fname):
            return 0
        return os.stat(fname).st_mtime
    except OSError:
        return 0

def check_control_flags():
    check_restart()
    if os.path.isfile(conf.STOP_FLAG):
        log("Stop flag found. Exiting...")
        os.remove(conf.STOP_FLAG)
        sys.exit(0)


def drop_flag(flag):
    if os.path.isfile(flag):
        os.remove(flag)


def get_name(line):
    m = NameRx.match(line)
    return m.group(1) if m else ''


def check_repeats(repeats):
    if not Args.stdout:
        if repeats > 1:
            ToSend.lastLineAppend("   [ REPEATS %s TIMES ]" % repeats)


def read_unittest_output(proc, reader, suitname):
    last_suit_line = ''
    has_stranges = False
    repeats = 0 # now many times the same 'strange' line repeats
    running_test_name = ''
    complete = False
    to_send_count = 0
    try:
        while reader.state == pipereader.PIPE_READY:
            line = reader.readline(conf.UT_PIPE_TIMEOUT)
            if not complete and len(line) > 0:
                #debug("Line: %s", line.lstrip())
                if line.startswith(SUITMARK):
                    check_repeats(repeats)
                    repeats = 1
                    last_suit_line = line
                    if line.startswith(STARTMARK):
                        running_test_name = get_name(line) # remember to print OK test result and for abnormal termination case
                        to_send_count = ToSend.count()
                    elif line.startswith(FAILMARK) and not complete:
                        #debug("Appending: %s", line.rstrip())
                        FailedTests.append(get_name(line))
                        ToSend.flush()
                        ToSend.append(line)
                        running_test_name = ''
                    elif line.startswith(OKMARK):
                        if running_test_name == get_name(line): # print it out only if there were any 'strange' lines
                            if to_send_count < ToSend.count():
                                ToSend.append(line)
                        else:
                            ToSend.log("WARNING!!! running_test_name != get_name(line): %s; %s", running_test_name, line.rstrip())
                        running_test_name = ''
                    elif line.startswith(BARMARK) and not line[len(BARMARK):].startswith(" Running"):
                        complete = True
                else: # gather test's messages
                    if last_suit_line != '':
                        ToSend.append(last_suit_line)
                        last_suit_line = ''
                    if ToSend.count() and (line == ToSend.last_line_src):
                        repeats += 1
                    else:
                        check_repeats(repeats)
                        repeats = 1
                        ToSend.append(line)
                    has_stranges = True
        else: # end reading
            check_repeats(repeats)

        state_error = reader.state in (pipereader.PIPE_HANG, pipereader.PIPE_ERROR)
        if state_error:
            ToSend.flush()
            ToSend.append(
                ("[ test suit has TIMED OUT (more than %s seconds) on test %s ]" % (conf.UT_PIPE_TIMEOUT, running_test_name))
                if reader.state == pipereader.PIPE_HANG else
                ("[ PIPE ERROR reading test suit output on test %s ]" % running_test_name))
            FailedTests.append(running_test_name)

        before = time.time()
        proc.limited_wait(conf.TEST_TERMINATION_WAIT)

        if proc.poll() is None:
            if not state_error:
                debug("The unittest %s hasn't finished for %.1f seconds", suitname, conf.TEST_TERMINATION_WAIT)
            kill_proc(proc, sudo=True)
            proc.wait()
        else:
            delta = time.time() - before
            if delta >= 0.01:
                debug("The unittest %s finnishing takes %.2f seconds", suitname, delta)

        if proc.returncode != 0:
            ToSend.flush()
            if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
                ToSend.append("[ Test %s of %s suit interrupted abnormally ]", running_test_name, suitname)
                FailedTests.append(running_test_name)
            if proc.returncode < 0:
                if not (proc.returncode == -signal.SIGTERM and reader.state == pipereader.PIPE_HANG): # do not report signal if it was ours kill result
                    signames = SignalNames.get(-proc.returncode, [])
                    signames = ' (%s)' % (','.join(signames),) if signames else ''
                    ToSend.append("[ TEST SUIT %s HAS BEEN INTERRUPTED by signal %s%s during test %s]",
                                  suitname, -proc.returncode, signames, running_test_name)
            else:
                ToSend.append("[ %s TEST SUIT'S RETURN CODE = %s ]", suitname, proc.returncode)
            if FailedTests:
                ToSend.append("Failed tests: %s", FailedTests)
            else:
                FailedTests.append('(unknown)')

    finally:
        if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
            debug("Test %s final result not found!", running_test_name)
            FailedTests.append(running_test_name)
        if has_stranges and not FailedTests:
            ToSend.append("[ Tests passed OK, but has some output. ]")


if os.name == 'posix':
    def exec_unittest(testpath):
        if os.path.basename(testpath) in conf.SUDO_REQUIRED:
            cmd = ['/usr/bin/sudo', '-E', 'LD_LIBRARY_PATH=%s' % Env['LD_LIBRARY_PATH'], testpath]
        else:
            cmd = [testpath]
        return Process(cmd, bufsize=0, stdout=PIPE, stderr=STDOUT, env=Env, **conf.SUBPROC_ARGS)
else:
    def exec_unittest(testpath):
        return Process([testpath], bufsize=0, stdout=PIPE, stderr=STDOUT, env=Env, **conf.SUBPROC_ARGS)


def validate_testpath(testpath):
    if not os.access(testpath, os.F_OK):
        FailedTests.append('(all)')
        ToSend.flush()
        ToSend.append("Testsuit '%s' not found!" % testpath)
        return False
    if not os.access(testpath, os.R_OK|os.X_OK):
        FailedTests.append('(all)')
        ToSend.flush()
        ToSend.append("Testsuit '%s' isn't accessible!" % testpath)
        return False
    return True


def call_test(suitname, reader):
    ToSend.clear()
    del FailedTests[:]
    ToSend.log("[ Calling %s test suit ]", suitname)
    old_coount = ToSend.count()
    proc = None
    try:
        testpath = os.path.join(Build.bin_path, suitname)
        if not validate_testpath(testpath):
            return
        #debug("Calling %s", testpath)
        # sudo is required since some unittest start server
        # also we're to pass LD_LIBRARY_PATH through command line because LD_* env varsn't passed to suid processes
        proc = exec_unittest(testpath)
        reader.register(proc)
        read_unittest_output(proc, reader, suitname)
    except BaseException as e:
        tstr = traceback.format_exc()
        print tstr
        if isinstance(e, Exception):
            ToSend.flush()
            ToSend.append("[[ Tests call error:\n%s\n]]", tstr)
        else:
            ToSend.flush()
            ToSend.log("[[ Tests has been interrupted:\n%s\n]]", tstr)
            raise # it wont be catched and will allow the script to terminate
    finally:
        if proc:
            reader.unregister()
        if ToSend.count() >= old_coount:
            ToSend.append('')


def kill_proc(proc, sudo=False, what="test"):
    "Kills subproces under sudo"
    debug("Killing %s process %s", what, proc.pid)
    if sudo and os.name == 'posix':
        subcall(['/usr/bin/sudo', 'kill', str(proc.pid)], shell=False)
    else:
        os.kill(proc.pid, signal.SIGTERM)
        #subcall(['kill', str(proc.pid)], shell=False)


def get_tests_to_skip(branch):
    to_skip = set()
    if (branch in conf.SKIP_TESTS) or conf.SKIP_ALL:
        to_skip = conf.SKIP_TESTS.get(branch, set()) | conf.SKIP_ALL
        log("Configured to skip tests: %s", ', '.join(to_skip))
    return to_skip


def run_tests(branch):
    log("Running unit tests for branch %s" % branch)
    output = []
    failed = False
    to_skip = get_tests_to_skip(branch)
    reader = pipereader.PipeReader()
    all_fails = []

    if 'all_ut' not in to_skip:
        for name in get_ut_names():
            if name in to_skip: continue
            call_test(name, reader)  # it clears ToSend and FailedTests on start
            if FailedTests:
                RESULT.append(('ut:'+name, False))
                #debug("Test suit %s has some fails: %s", name, FailedTests)
                failedStr = "\n".join(("Tests, failed in the %s test suit:" % name,
                                       "\n".join("\t" + name for name in FailedTests),
                                      ''))
                all_fails.append((name, FailedTests[:]))
                if Args.stdout:
                    ToSend.flush()
                    logPrint('')
                    log(failedStr)
                else:
                    if output:
                        output.append('')
                    output.append(failedStr)
                    output.extend(ToSend.lines)
            else:
                RESULT.append(('ut:'+name, True))
                debug("Test suit %s has NO fails", name)

    ToSend.clear()
    if all_fails:
        failed = True
        if len(all_fails) > 1:
            failsum = "Failed unitests summary:\n" + "\n".join(
                        ("* %s:\n        %s" % (fail[0], ','.join(fail[1])))
                        for fail in all_fails
                    )
            if Args.stdout:
                log(failsum)
            else:
                output.append(failsum)
    elif not Args.no_functest:
        if not perform_func_test(to_skip):
            RESULT.append(('functests', False))
            failed = True
            if Args.stdout:
                output.append('')
                output.extend(ToSend.lines)
            else:
                ToSend.flush()
        else:
            RESULT.append(('functests', True))


    if failed:
        if Args.full:
            FailTracker.mark_fail(branch)
        if not Args.stdout:
            email_notify(branch, output)
    else:
        debug("Branch %s -- SUCCESS!", branch)
        if Args.full:
            ToSend.clear()
            FailTracker.mark_success(branch)
            if ToSend:  # it's not empty if mark_success() really removed previous test-fail status.
                if not Args.stdout:
                    debug("Sending successful test notification.")
                    email_notify(branch, ToSend.lines)
                ToSend.clear()

    return not failed


def filter_branch_names(branches):
    "Check names for exact eq with list, drop duplicates"
    # The problem is `hg in --branch` takes all branches with names beginning with --branch value. :(
    filtered = []
    for name in branches:
        if name in conf.BRANCHES and not name in filtered:
            filtered.append(name)
            # hope it wont be used for huge BRANCHES list
    return filtered


def chs_str(changeset):
    try:
        return "[%(branch)s] %(node)s: %(author)s, %(date)s\n\t%(desc)s" % changeset
    except KeyError, e:
        return "WARNING: no %s key in changeset dict: %s!" % (e.args[0], changeset)


def format_changesets(branch):
    chs = Changesets.get(branch, [])
    if chs and isinstance(chs[0], dict):
        return "Changesets:\n" + "\n".join(
                ("\t%s" % v['line']) if 'line' in v else chs_str(v) for v in chs)
    else:
        return "\n".join(chs)


def get_changesets(branch, bundle_fn):
    debug("Run: " + (' '.join(conf.HG_REVLIST + ["--branch=%s" % branch, bundle_fn])))
    proc = Process(conf.HG_REVLIST + ["--branch=%s" % branch, bundle_fn],
                   bufsize=1, stdout=PIPE, stderr=STDOUT, **conf.SUBPROC_ARGS)
    (outdata, errdata) = proc.communicate()
    if proc.returncode == 0:
        Changesets[branch] = [
            ({"line": line.lstrip()} if line.startswith("\t") else
            dict(zip(['branch','author','node','date','desc'], line.split(';',4))))
            for line in outdata.splitlines()
        ]
        return True
    elif proc.returncode == 1:
        debug("No changes found for branch %s", branch)
    else:
        Changesets[branch] = [
            "Error getting changeset list info.",
            "hg return code = %s" % proc.returncode,
            "STDOUT: %s" % outdata,
            "STDERR: %s" % errdata,
            '']
    return False


def check_new_commits(bundle_fn):
    "Check the repository for new commits in the controlled branches"
    log("Check for new commits")
    try:
        cmd = conf.HG_IN + [ "--branch=%s" % b for b in conf.BRANCHES ] + ['--bundle', bundle_fn]
        debug("Run: %s", ' '.join(cmd))
        ready_branches = check_output(cmd, stderr=STDOUT, **conf.SUBPROC_ARGS)
        if ready_branches:
            # Specifying the current branch (.) turns off all other
            branches = ['.'] if conf.BRANCHES[0] == '.' else filter_branch_names(ready_branches.split(','))
            if conf.BRANCHES[0] != '.':
                ToSend.log('')  # an empty line separator
                log("Commits are found in branches: %s", branches)
            if branches:
                Changesets.clear()
                return [ b for b in branches if get_changesets(b, bundle_fn) ]
    except CalledProcessError, e:
        if e.returncode != 1:
            log("ERROR: `hg in` call returns %s code. Output:\n%s", e.returncode, e.output)
            raise
    if Args.rebuild:
        return conf.BRANCHES
    log("No new commits found for controlled branches.")
    return []


def current_branch_name():
    try:
#        branch_name = check_output(HG_BRANCH, stderr=STDOUT, **SUBPROC_ARGS)
        branch_name = check_output(conf.HG_BRANCH, stderr=None, **conf.SUBPROC_ARGS)
        return branch_name.split("\n")[0]
    except CalledProcessError, e:
        if e.returncode != 1:
            log("ERROR: Failed to find current branch name: `hg branch` call returns %s code. Output:\n%s", e.returncode, e.output)
            raise


def check_mvn_exit(proc, last_lines):
    stop = time.time() + conf.MVN_TERMINATION_WAIT
    while proc.poll() is None and time.time() < stop:
        time.sleep(0.2)
    if proc.returncode is None:
        last_lines.append(log("*** Maven has hanged in the end!"))
        kill_proc(proc, what="mvn")
        if proc.poll() is None:
            time.sleep(0.5)
            proc.poll()
        debug("Maven process was killed. RC = %s", proc.returncode)


build_fail_rx = re.compile(r"^\[INFO\] ([^\.]+)\s+\.+\s+FAILURE")
mvn_rf_prefix = "[ERROR]   mvn <goals> -rf :"

def get_failed_project(last_lines):
    phase = 'start'
    project = ''
    project_name = ''
    for line in last_lines:
        if phase == 'start':
            if line.startswith('[INFO] Reactor Summary:'):
                phase = 'sum'
        elif phase =='sum':
            m = build_fail_rx.match(line)
            if m:
                project_name = m.group(1)
                phase = 'tail'
            elif line.startswith("[INFO] ------------"):
                phase = 'tail'
        elif phase == 'tail':
            if line.startswith('[ERROR] After correcting the problems'):
                phase = 'got'
        elif phase == 'got':
            if line.startswith(mvn_rf_prefix):
                project = line[len(mvn_rf_prefix):].rstrip()
                break
    return (project, project_name or project)


def execute_maven(cmd, kwargs, last_lines):
    if Args.full_build_log:
        kwargs.pop('universal_newlines')
        proc = Process(cmd, **kwargs)
        proc.wait()
    else:
        proc = Process(cmd, bufsize=conf.MVN_BUFFER, stdout=PIPE, stderr=STDOUT, **kwargs)
        for line in proc.stdout:
            last_lines.append(line)
        check_mvn_exit(proc, last_lines)
    return proc.returncode


def nothreads_rebuild(last_lines, branch, unit_tests):
    project, project_name = get_failed_project(last_lines)
    if not project_name:
        project_name = project
    log("[ Restarting maven in single thread mode after fail on '%s']", project_name)
    if call_maven_build(branch, unit_tests, no_threads=True, project_name=project_name):
        #! Project dependencies  error! Report but go on.
        email_build_error(branch, last_lines, unit_tests, dep_error=project_name)
        return True
    else:
        # Other errors - already reported
        return False


def failed_project_single_build(last_lines, branch, unit_tests):
    project, project_name = get_failed_project(last_lines)
    if project == '':
        last_lines.append("ERROR: Can't figure failed project '%s'" % project_name)
        return False
    log("[ Restarting maven to re-build '%s' ]", project_name)
    call_maven_build(branch, unit_tests, no_threads=True, single_project=project, project_name=project_name)
    return True


def call_maven_build(branch, unit_tests=False, no_threads=False, single_project=None, project_name=None):
    last_lines = deque(maxlen=conf.BUILD_LOG_LINES)
    log("Build %s (branch %s)...", "unit tests" if unit_tests else "netoptix_vms", branch)
    kwargs = conf.SUBPROC_ARGS.copy()

    cmd = [conf.MVN, "package", "-e", "-Dbuild.configuration=%s" % conf.MVN_BUILD_CONFIG]
    if conf.MVN_THREADS and not no_threads:
        cmd.extend(["-T", "%d" % conf.MVN_THREADS])
    elif no_threads:
        cmd.extend(["-T", "1"])
    if single_project is not None:
        cmd.extend(['-pl', single_project])
    #cmd.extend(['--projects', 'nx_sdk,nx_storage_sdk,mediaserver_core'])

    if unit_tests:
        kwargs['cwd'] = os.path.join(kwargs["cwd"], conf.UT_SUBDIR)
    debug("MVN: %s", cmd); time.sleep(1.5)

    try:
        retcode = execute_maven(cmd, kwargs, last_lines)
        if retcode != 0:
            log("Error calling maven: ret.code = %s" % retcode)
            if not Args.full_build_log:
                log("The last %d log lines:" % len(last_lines))
                logPrint("".join(last_lines))
                last_lines = list(last_lines)
                last_lines.append("Maven return code = %s" % retcode)
                if not single_project:
                    if not no_threads:
                        return nothreads_rebuild(last_lines, branch, unit_tests)
                    #else: -- removed since singlethread build possible would be enough to get the fault cause
                    #    if failed_project_single_build(last_lines, branch, unit_tests):
                    #        # on success it reports from the recursive call call_maven_build(), so we can return here
                    #        return False
                email_build_error(branch, last_lines, unit_tests, single_project=(project_name if single_project else None))
            return False
    except CalledProcessError:
        tb = traceback.format_exc()
        log("maven call has failed: %s" % tb)
        if not Args.full_build_log:
            log("The last %d log lines:" % len(last_lines))
            logPrint("".join(last_lines))
            email_build_error(branch, last_lines, unit_tests, crash=tb, single_project=(project_name if single_project else None))
        return False
    if no_threads and (project_name is not None):
        pass
    return True


def build_branch(branch):
    if not Args.build_ut_only:
        if not call_maven_build(branch):
            debug("BUILD FAILED!!!")
            RESULT.append(('build', False))
            return False
        else:
            debug("BUILD SUCCESS!!!")
            RESULT.append(('build', True))
    if not call_maven_build(branch, unit_tests=True):
        debug("UT BUILD FAILED!!!")
        RESULT.append(('build-ut', False))
        return False
    else:
        debug("UT BUILD SUCCESS!!!")
        RESULT.append(('build-ut', True))
    return True

def prepare_branch(branch):
    "Prepare the branch for testing, i.e. build the project and unit tests"
    ToSend.log('')  # an empty line separator
    if branch != '.':
        log("Switch to the branch %s" % branch)
    debug("Call %s", conf.HG_PURGE)
    check_call(conf.HG_PURGE, **conf.SUBPROC_ARGS)
    debug("Call %s", conf.HG_UP if branch == '.' else (conf.HG_UP + ['--rev', branch]))
    check_call(conf.HG_UP if branch == '.' else (conf.HG_UP + ['--rev', branch]), **conf.SUBPROC_ARGS)
    #debug("Going to call maven...")
    return build_branch(branch)


def update_repo(branches, bundle_fn):
    if not os.path.exists(bundle_fn):
        if Args.rebuild:
            return
        else:
            log("ERROR: bundle-file %s not found!", bundle_fn)
            sys.exit(1)
    log("Pulling branches: %s" % (', '.join(branches)))
    #debug("Using bundle file %s", bundle_fn)
    #try:
    check_call(conf.HG_PULL + [bundle_fn], **conf.SUBPROC_ARGS)
    #except CalledProcessError, e:
    #    print e
    #    sys.exit(1)


def check_hg_updates():
    "Check for repository updates, get'em, build and test"
    bundle_fn = os.path.join(conf.TEMP, "in.hg")
    branches = check_new_commits(bundle_fn)
    rc = True
    if branches and not Args.hg_only:
        update_repo(branches, bundle_fn)
        for branch in branches:
            if prepare_branch(branch):
                Build.load_vars()
                rc = run_tests(branch) and rc
            else:
                FailTracker.mark_fail(branch)
                rc = False
    if os.access(bundle_fn, os.F_OK):
        os.remove(bundle_fn)
    return rc


def run():
    try:
        if Args.full:
            rc = check_hg_updates()
            if Args.hg_only:
                log("Changesets:\n %s", "\n".join("%s\n%s" % (br, "\n".join("\t%s" % ch for ch in chs)) for br, chs in Changesets.iteritems()))
            return rc
        if Args.test_only:
            log("Test only run...")
        if not Args.test_only:
            if not build_branch(conf.BRANCHES[0]):
                return False
        Build.load_vars()
        rc = run_tests(conf.BRANCHES[0])
        RESULT.append(('run_tests', rc))
        return rc
    except Exception:
        traceback.print_exc()
        return False


#####################################
def check_mediaserver_deb():
    # The same filename used for all versions here:
    # a) To remove (by override) any previous version automatically.
    # b) To use fixed name in the bootstrap.sh script
    try:
        src = get_server_package_name()
    except FuncTestError as err:
        ToSend.log(err)
        ToSend.log("Try to use the previously built deb-package (it could have a diferent version!).")
        src = None
    dest = os.path.join(conf.VAG_DIR, 'networkoptix-mediaserver.deb')
#    debug("Src: %s\nDest: %s", src, dest)
    dest_time = get_file_time(dest)
    if src is None or not os.path.isfile(src):
        if dest_time == 0:
            raise FuncTestError("ERROR: networkoptix-mediaserver deb-package isn't found!")
#        else:
#            debug("No newly made mediaserver package found, using the old one.")
    else:
        src_time = get_file_time(src)
        if src_time > dest_time:
            debug("Using new server package from %s", src)
            shutil.copy(src, dest) # put this name into config
        else:
            pass
#            log("%s is up to date", dest)


def check_testcamera_bin():
    src = get_testcamera_path()
    dest = os.path.join(conf.VAG_DIR, 'testcamera')
    dest_time = get_file_time(dest)
    if not os.path.isfile(src):
        if dest_time == 0:
            log("Testcamera executable file is unavailable. Functests depending on it will be skipped!")
            return None
    else:
        src_time = get_file_time(src)
        if src_time > dest_time:
            debug("Using new testcamera from %s", src)
            shutil.copy(src, dest)
        else:
            debug("Using old testcamera at %s", dest)
        return True

#####################################
# Functional tests block
def start_boxes(boxes, keep = False):
    try:
        # 1. Get the .deb file and testcamera
        check_mediaserver_deb()
        check_testcamera_bin()
        # 2. Start virtual boxes
        if not keep:
            debug("Removing old vargant boxes...")
            check_call(conf.VAGR_DESTROY, shell=False, cwd=conf.VAG_DIR)
        if not boxes:
            log("Creating and starting vagrant boxes...")
        else:
            log("Creating and starting vagrant boxes: %s...", boxes)
        boxlist = boxes.split(',') if len(boxes) else []
        check_call(conf.VAGR_RUN + [conf.BOX_NAMES[b] for b in boxlist], shell=False, cwd=conf.VAG_DIR)
        failed = [b[0] for b in get_boxes_status() if b[0]in boxes and b[1] != 'running']
        if failed:
            ToSend.log("ERROR: failed to start up the boxes: %s", ', '.join(failed))
            return False
        # 3. Wait for all mediaservers become ready (use /ec2/getMediaServers
        #to_check = [b for b in boxlist if b in CHECK_BOX_UP] if boxlist else CHECK_BOX_UP
        #wait_servers_ready([BOX_IP[b] for b in to_check])
        for box in (boxlist or conf.BOX_POST_START.iterkeys()):
            if box in conf.BOX_POST_START:
                boxssh(conf.BOX_IP[box], ['/vagrant/' + conf.BOX_POST_START[box]])
        time.sleep(conf.SLEEP_AFTER_BOX_START)
        return True
    except FuncTestError as e:
        ToSend.log("Virtual boxes start up failed: %s", e.message)
        return False
    except BaseException as e:
        ToSend.log("Exception during virtual boxes start up:\n%s", traceback.format_exc())
        if not isinstance(e, Exception):
            raise # it wont be catched and will allow the script to terminate


def stop_boxes(boxes, destroy=False):
    try:
        if not boxes:
            log("Removing vargant boxes...")
        else:
            log("Removing vargant boxes: %s...", boxes)
        boxlist = [conf.BOX_NAMES[b] for b in boxes.split(',')] if len(boxes) else []
        cmd = conf.VAGR_DESTROY if destroy else conf.VAGR_STOP
        check_call(cmd + boxlist, shell=False, cwd=conf.VAG_DIR)
    except BaseException as e:
        ToSend.log("Exception during virtual boxes start up:\n%s", traceback.format_exc())
        if not isinstance(e, Exception):
            raise # it wont be catched and will allow the script to terminate


def wait_servers_ready(iplist):
    urls = ['http://%s:%s/ec2/getMediaServersEx' % (ip, conf.MEDIASERVER_PORT) for ip in iplist]
    debug("wait_servers_ready: urls: %s", urls)
    not_ready = set(urls)
    # 1. Prepare authentication for http queries
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    for u in urls:
        passman.add_password(None, u, conf.MEDIASERVER_USER, conf.MEDIASERVER_PASS)
    urllib2.install_opener(urllib2.build_opener(urllib2.HTTPDigestAuthHandler(passman)))
    # 2. Wait for responses for query
    # For each URL check number of servers online
    too_slow = time.time() + len(urls) * conf.ALL_START_TIMEOUT_BASE
    while not_ready:
        for url in urls:
            if time.time() > too_slow:
                raise FuncTestError("Server start timed out! Functional tests wasn't performed.")
            if url in not_ready:
                try:
                    jdata = urllib2.urlopen(url, timeout=conf.START_CHECK_TIMEOUT).read()
                    # Check response for 'status' field (Online/Offline) for all servers
                except Exception, e:
                    #debug("wait_servers_ready(%s): urlopen error: %s", url, e,)
                    continue # wait for good response or for global timeout
                try:
                    data = json.loads(jdata)
                except ValueError, e:
                    #debug("wait_servers_ready(%s): json.loads error: %s", url, e)
                    continue # just ignore wrong answer, wait for correct
                count = 0
                #for server in data:
                #    s = {k: server[k] for k in ('id', 'status', 'url', 'networkAddresses') if k in server}
                #    if server.get('status', '') == 'Online':
                #        count += 1
                #if count == len(urls):
                #    debug("Ready response from %s", url)
                #    not_ready.discard(url)
                not_ready.discard(url)
            time.sleep(1)


BASE_FUNCTEST_CMD = [sys.executable, "-u", "functest.py"]
NATCON_ARGS = ["--natcon", '--config', 'nattest.cfg']


def mk_functest_cmd(to_skip):
    only_test = ''
    cmd = BASE_FUNCTEST_CMD[:]
    if Args.timesync:
        cmd.append("--timesync")
        only_test = "timesync"
    elif Args.msarch:
        cmd.append("--msarch")
        only_test = "msarch"
    elif Args.stream:
        cmd.append("--stream")
        only_test = "stream"
    elif Args.natcon:
        cmd.extend(NATCON_ARGS)
        only_test = "natcon"
    else:
        if 'time' in to_skip:
            cmd.append("--skiptime")
        if 'backup' in to_skip:
            cmd.append("--skipbak")
        if 'msarch' in to_skip:
            cmd.append('--skipmsa')
        if "stream" in to_skip:
            cmd.append("--skipstrm")
    debug("Running functional tests: %s", cmd)
    return cmd, only_test


def perform_func_test(to_skip):
    if os.name != 'posix':
        logPrint("\nFunctional tests require POSIX-compatible OS. Skipped.")
        return
    need_stop = False
    reader = proc = None
    success = True
    try:
        if not Args.nobox:
            start_boxes('Box1' if Args.natcon else 'Box1,Box2')
            need_stop = True
        # 4. Call functest/main.py (what about imoirt it and call internally?)
        if os.path.isfile(".rollback"): # TODO: move to config or import from functest.py
            os.remove(".rollback")
        reader = pipereader.PipeReader()
        sub_args = {k: v for k, v in conf.SUBPROC_ARGS.iteritems() if k != 'cwd'}
        unreg = False

        only_test = ''
        if not Args.httpstress:
            unreg = True
            cmd, only_test = mk_functest_cmd(to_skip)
            if only_test != 'natcon':
                proc = Process(cmd, bufsize=0, stdout=PIPE, stderr=STDOUT, **sub_args)
                reader.register(proc)
                if not read_functest_output(proc, reader, only_test):
                    success = False
                    RESULT.append(('main-call-functests', False))
                else:
                    RESULT.append(('main-call-functests', True))

            if (not only_test or only_test == 'natcon') and 'natcon' not in to_skip:
                if not only_test:
                    cmd = BASE_FUNCTEST_CMD + NATCON_ARGS
                    reader.unregister()
                if not Args.nobox:
                    stop_boxes('Box2')
                    start_boxes('Nat,Behind', keep=True)
                debug("Running connection behind NAT test: %s", cmd)
                proc = Process(cmd, bufsize=0, stdout=PIPE, stderr=STDOUT, **sub_args)
                reader.register(proc)
                if not read_misctest_output(proc, reader, "connection behind NAT"):
                    success = False
                    RESULT.append(('functest:natcon', False))
                else:
                    RESULT.append(('functest:natcon', True))

        if not only_test and not Args.natcon and 'httpstress' not in to_skip:
            if unreg:
                reader.unregister()
                unreg = False
            boxssh(conf.BOX_IP['Box1'], ('/vagrant/safestart.sh', 'networkoptix-mediaserver'))  #FIXME rewrite using the generic way with ctl.sh
            url = "%s:%s" % (conf.BOX_IP['Box1'], conf.MEDIASERVER_PORT)
            cmd = [sys.executable, "-u", "stresst.py", "--host", url, "--full", "20,40,60", "--threads", "10"]
            #TODO add test durations to config
            #TODO add -threads value to config
            #TODO add the test duration and a server hang timeout
            ToSend.log("Running http stress test: %s", cmd)
            proc = Process(cmd, bufsize=0, stdout=PIPE, stderr=STDOUT, **sub_args)
            reader.register(proc)
            unreg = True
            #TODO make it a part of the functest.py
            if not read_misctest_output(proc, reader, "http stress"):
                success = False
                RESULT.append(('functest:httpstress', False))
            else:
                RESULT.append(('functest:httpstress', True))

    except FuncTestError, e:
        ToSend.log("Functional test aborted: %s", e.message)
        success = False
    except BaseException, e:
        ToSend.log("Exception during functional test run:\n%s", traceback.format_exc())
        if not isinstance(e, Exception):
            #s = "[[ Functional tests has been interrupted:\n%s\n]]" % tstr
            #ToSend.append(s)
            #log(s)
            raise # it wont be catched and will allow the script to terminate
    finally:
        if reader and proc and unreg:
            reader.unregister()
        if need_stop:
            log("Stopping vagrant boxes...")
            check_call(conf.VAGR_STOP, shell=False, cwd=conf.VAG_DIR)
    return success

#TODO
# record structure:
# * test symbolic id
#
class FuncTestDesc(object):

    def __init__(self, name, title, startMark=None, endMark=None):
        # if startMark is None - the start marker is: "%s Test Start" % title
        # if endMark is None - the end marker is: "%s Test End" % title
        self.name = name
        self.title = title
        self.startMark = ("%s Test Start" % title) if startMark is None else startMark
        self.endMark = ("%s Test End" % title) if endMark is None else endMark


FUNCTEST_TBL = (
    FuncTestDesc('basic', "Basic functional", None, None),
    FuncTestDesc('merge', "Server Merge", None, None),
    FuncTestDesc('sysname', "SystemName", None, None),
    FuncTestDesc('proxy', "Server proxy", None, None),
    FuncTestDesc('timesync', "TimeSync", None, None), # class: TimeSyncTest
    FuncTestDesc('bstorage', "Backup Storage", None, None),
    FuncTestDesc('msarch', "Multiserver Archive", None, None),
    FuncTestDesc('stream', "Streaming", None, None),
    FuncTestDesc('dbup', "DB Upgrade", None, None),
    FuncTestDesc('natcon', "Connection behind NAT", None, None),
)

#TODO
def perform_func_test_new(to_skip):
    if os.name != 'posix':
        logPrint("\nFunctional tests require POSIX-compatible OS. Skipped.")
        return
    need_stop = False
    reader = proc = None
#TODO


class NewFunctestParser(object):

    FAIL_MARK = "FAIL:"
    ERROR_MARK = "ERROR:"

    # Что хочется:
    # - распзнавать тестсюит по стартовой фразе (чтобы не зависеть от порядка),
    #   при этом контролировать случайный повтор одного тестсюита
    # - распознавать произвольный неописанный тестсюит, если он начинается фразой стандартного формата,
    #   и для него тоже контролировать повор
    # - собирать результаты (хотя бы успех или фэйл) по каждому тестсюиту, выводить саммари в конце
    #   (хорошо бы ещё, по возможности, перечислить конкретные упавшие тесты)х

    def __init__(self, first=None):
        """
        @type first: FuncTestDesc
        """
        self.current = first
        self.parser = self.parse_start
        self.collector = []
        self.has_errors = False

    _stage_names = {
        'start' : 'waiting for %s',
        'test'  : '%s test'
    }

    def get_stage(self):
        parser_name = self.parser.im_func.func_name
        assert parser_name.startswith('parse_'), "Wrong %s.parser value: %s" % (self.__class__.__name__, self.parser)
        parser_name = parser_name[6:]
        try:
            return self._stage_names.get[parser_name]
        except KeyError:
            print "WARNING: %s.get_stage: unknown test log parsing stage: %s" % (self.__class__.__name__, parser_name)
            return "test %s, phase " + parser_name


    def parse_start(self, line):
        if line.startswith(self.current.startMark):
            self.parser = self.parse_test
            self.collector[:] = [line]
        pass

    def parse_test(self, line):
        if line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK):
            self.has_errors = True
            self.parser = self.parse_failed
            is_fail = line.startswith(self.FAIL_MARK)
            ToSend.log("%s test %s!", self.current.title, "failed" if is_fail else "reports an error")
            ToSend.log(line)
        elif line.startswith("Basic functional tests end"):
            ToSend.log("Basic functional tests done.")
            self.parser = self.parse_merge_start
            self.stage = 'wait for Merge server test'

    def parse_failed(self, line):
        pass




class FunctestParser(object):
    """
    FSM that parses the functional tests output and controls their results.
    """
    def __init__(self):
        self.collector = []
        self.has_errors = False
        self.stage = 'Main functional tests'
        self.parser = self.parse_main

    if False:
        @property
        def parser(self):
            return self._parser

        #@parser.setter
        #def parser(self, value):
        #    self._parser = value
        #    print "* Set parser: %s" % value

    FAIL_MARK = "FAIL:"
    ERROR_MARK = "ERROR:"

    # Tests structure:
    # The merge test runs only if the main test was successful.
    # The system name test runs only if the main tests was successful.
    # The time synchronization tests run unconditionally.
    # (See functest.DoTests for detals.)
    # I.e. self.has_errors will never be true in the beginning of the merge test of the systen bane test,
    # but it could be true in the beginning of the time synchronization tests.

    # the main tests phase -- don't use self.collector
    # lines are appended to ToSend since the first 'FAIL:' found
    def parse_main(self, line):  # FT_MAIN
        if line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK):
            self.has_errors = True
            self.parser = self.parse_main_failed
            is_fail = line.startswith(self.FAIL_MARK)
            ToSend.log("Functional test %s!", "failed" if is_fail else "reports an error")
            ToSend.log(line)
        elif line.startswith("Basic functional tests end"):
            ToSend.log("Basic functional tests done.")
            self.parser = self.parse_merge_start
            self.stage = 'wait for Merge server test'

    def parse_main_failed(self, line):  # FT_MAIN_FAILED
        ToSend.log(line)
        if line.startswith("FAILED (failures"):
            ToSend.append('')
            self.parser = self.parse_proxy_start  # skip merge and sysname tests
            self.stage = 'wait for server proxy test'

    # Merge test
    MERGE_END = "Server Merge Test: Resource End"

    def parse_merge_start(self, line):  # FT_MERGE
        if line.startswith("Server Merge Test: Resource Start"):
            self.parser = self.parse_merge
            self.stage = 'Merge server test'
            self.collector[:] = [line]

    def parse_merge(self, line):  # FT_MERGE_IN
        if line.startswith(self.MERGE_END):
            self._merge_test_end()
        elif line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK):
            self.has_errors = True
            is_fail = line.startswith(self.FAIL_MARK)
            ToSend.log("Functional test %s on Merge Server test!", "failed" if is_fail else "reports an error")
            for s in self.collector:
                ToSend.log(s)
            ToSend.log(line)
            del self.collector[:]
            self.parser = self.parse_merge_failed
        else:
            self.collector.append(line)

    def parse_merge_failed(self, line):  # FT_MERGE_FAILED
        ToSend.log(line)
        if line.startswith(self.MERGE_END):
            self._merge_test_end()

    def _merge_test_end(self):
        self.parser = self.parse_sysname_start #if success else self.parse_proxy_start
        self.stage = 'wait for SystemName test'
        ToSend.log("Merge Server test done.")

    # Sysname test
    SYSNAME_END = "SystemName test finished"

    def parse_sysname_start(self, line):  # FT_SYSNAME
        if line.startswith("SystemName Test Start"):
            self.stage = 'SystemName test'
            self.parser = self.parse_sysname
            self.collector[:] = [line]

    def parse_sysname(self, line):
        if line.startswith(self.SYSNAME_END):
            self._sysname_test_end()
        elif line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK):
            self.has_errors = True
            is_fail = line.startswith(self.FAIL_MARK)
            ToSend.log("Functional test %s on SystemName test!", "failed" if is_fail else "reports an error")
            for s in self.collector:
                ToSend.log(s)
            ToSend.log(line)
            del self.collector[:]
            self.parser = self.parse_sysname_failed
        else:
            self.collector.append(line)

    def parse_sysname_failed(self, line):
        ToSend.log(line)
        if line.startswith(self.SYSNAME_END):
            self._sysname_test_end()

    def _sysname_test_end(self):
        ToSend.log("SystemName test done.")
        self.stage = "wait for server proxy test"
        self.parser = self.parse_proxy_start

    # Server proxy test
    PROXY_END = "Test complete."

    def parse_proxy_start(self, line):
        if line.startswith("Proxy Test Start"):
            self.parser = self.parse_proxy
            self.stage = 'Server proxy test'
            self.collector[:] = [line]

    def parse_proxy(self, line):  # FT_MERGE_IN
        if line.startswith(self.PROXY_END):
            self._proxy_test_end()
        elif line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK):
            self.has_errors = True
            is_fail = line.startswith(self.FAIL_MARK)
            ToSend.log("Functional test %s on Server Proxy test!", "failed" if is_fail else "reports an error")
            for s in self.collector:
                ToSend.log(s)
            ToSend.log(line)
            del self.collector[:]
            self.parser = self.parse_proxy_failed
        else:
            self.collector.append(line)

    def parse_proxy_failed(self, line):  # FT_MERGE_FAILED
        ToSend.log(line)
        if line.startswith(self.PROXY_END):
            self._proxy_test_end()

    def _proxy_test_end(self):
        self.parser = self.parse_timesync_start  #if success else self.parse_proxy_start
        self.stage = 'wait for timesync test'
        ToSend.log("Server Proxy test done.")

    # Time synchronization tests
    TS_PARTS = [] #it should be filled!
    current_ts_part = 0
    TS_HEAD = "TimeSyncTest suits: "
    TS_START = "TimeSync Test Start: "
    TS_END = "TimeSync Test End"

    def parse_timesync_start(self, line):  # FT_OLD_END
        if line.startswith(self.TS_HEAD):
            type(self).TS_PARTS = [s.strip() for s in line[len(self.TS_HEAD):].split(', ')]
        elif line.startswith(self.TS_START):
            self.ts_name = line[len(self.TS_START):].rstrip()
            if self.ts_name == self.TS_PARTS[self.current_ts_part]:
                self.parser = self.parse_timesync
                self.collector[:] = [line]
            else:
                ToSend.log(line)
                ToSend.log("ERROR: unknow tymesync test part: " + self.ts_name)
                self.parser = self.parse_timesync_failed
            self.stage = "time synchronization test: " + self.ts_name

    def parse_timesync(self, line):
        if line.startswith(self.TS_END):
            self.parser = self.parse_timesync_tail
        elif not self._ts_check_fail(line):
            self.collector.append(line)

    def parse_timesync_failed(self, line):
        ToSend.log(line)
        if line.startswith("FAILED (failures"):
            self._end_timesync()

    def parse_timesync_tail(self, line):
        if not self._ts_check_fail(line) and line.startswith("OK ("):
            self._end_timesync()

    def _ts_check_fail(self, line):
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        ToSend.log("Time synchronization test %s %s!", self.ts_name,
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            ToSend.log(s)
        ToSend.log(line)
        del self.collector[:]
        self.parser = self.parse_timesync_failed
        return True

    def _end_timesync(self):
        ToSend.log("Timesync test %s done", self.ts_name)
        self.current_ts_part += 1
        if self.current_ts_part < len(self.TS_PARTS):
            self.parser = self.parse_timesync_start
            del self.collector[:]
            self.stage = "wait for timestnc test"
        else:
            self.parser = self.parse_bstorage_start
            self.stage = "wait for backup storage test"

    # backup storage test

    BS_START = "Backup Storage Test Start"
    BS_END = "Backup Storage Test End"

    def parse_bstorage_start(self, line):
        if line.startswith(self.BS_START):
            self.ts_name = line[len(self.BS_START):].rstrip()
            self.stage = 'backup storage test'
            #if self.ts_name == self.TS_PARTS[self.current_ts_part]:
            self.parser = self.parse_bstorage
            self.collector[:] = [line]

    def parse_bstorage(self, line):
        if line.startswith(self.BS_END):
            self.parser = self.parse_bstorage_tail
        elif not self._bs_check_fail(line):
            self.collector.append(line)

    def parse_bstorage_failed(self, line): # TODO: it's similar to parse_timesync_failed, refactor it!
        ToSend.log(line)
        if line.startswith("FAILED (failures"):
            ToSend.log("Backup storage test done")
            self.parser = self.parse_msarch_start

    def parse_bstorage_tail(self, line): # TODO: it's similar to parse_timesync_tail, refactor it!
        if not self._bs_check_fail(line) and line.startswith("OK"):
            ToSend.log("Backup storage test done")
            self.parser = self.parse_msarch_start

    def _bs_check_fail(self, line): # TODO: it's similar to _ts_check_fail, refactor it!
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        ToSend.log("Backup storage test %s!",
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            ToSend.log(s)
        ToSend.log(line)
        del self.collector[:]
        self.parser = self.parse_bstorage_failed
        return True

    # multiserver archive test

    MS_START = "Multiserver Archive Test Start"
    MS_END = "Multiserver Archive Test End"

    def parse_msarch_start(self, line):
        if line.startswith(self.MS_START):
            #self.ts_name = line[len(self.MS_START):].rstrip()
            self.stage = 'multiserver archive test'
            #if self.ts_name == self.TS_PARTS[self.current_ts_part]:
            self.parser = self.parse_msarch
            self.collector[:] = [line]

    def parse_msarch(self, line):
        if line.startswith(self.MS_END):
            self.parser = self.parse_msarch_tail
        elif not self._ms_check_fail(line):
            self.collector.append(line)

    def parse_msarch_failed(self, line): # TODO: it's similar to parse_timesync_failed, refactor it!
        ToSend.log(line)
        if line.startswith("FAILED (failures"):
            ToSend.log("Multiserver archive test done")
            self.parser = self.parse_stream_start

    def parse_msarch_tail(self, line): # TODO: it's similar to parse_timesync_tail, refactor it!
        if not self._ms_check_fail(line) and line.startswith("OK"):
            ToSend.log("Multiserver archive test done")
            self.parser = self.parse_stream_start

    def _ms_check_fail(self, line): # TODO: it's similar to _ts_check_fail, refactor it!
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        #print ":::::" + line
        ToSend.log("Multiserver archive test %s!",
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            ToSend.log(s)
        ToSend.log(line)
        del self.collector[:]
        self.parser = self.parse_msarch_failed
        return True

    # streaming test

    STR_START = "Streaming Test Start"
    STR_END = "Streaming Test End"

    def parse_stream_start(self, line):
        if line.startswith(self.STR_START):
            #self.ts_name = line[len(self.STR_START):].rstrip()
            self.stage = 'streaming test'
            #if self.ts_name == self.TS_PARTS[self.current_ts_part]:
            self.parser = self.parse_stream
            self.collector[:] = [line]

    def parse_stream(self, line):
        if line.startswith(self.STR_END):
            self.parser = self.parse_stream_tail
        elif not self._str_check_fail(line):
            self.collector.append(line)

    def parse_stream_failed(self, line): # TODO: it's similar to parse_timesync_failed, refactor it!
        ToSend.log(line)
        if line.startswith("FAILED (failures"):
            ToSend.log("Streaming test done")
            self.parser = self.parse_dbup_start

    def parse_stream_tail(self, line): # TODO: it's similar to parse_timesync_tail, refactor it!
        if not self._str_check_fail(line) and line.startswith("OK"):
            ToSend.log("Streaming test done")
            self.parser = self.parse_dbup_start

    def _str_check_fail(self, line): # TODO: it's similar to _ts_check_fail, refactor it!
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        #print ":::::" + line
        ToSend.log("Streaming test %s!",
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            ToSend.log(s)
        ToSend.log(line)
        del self.collector[:]
        self.parser = self.parse_stream_failed
        return True

    # dbup (DB migration on server upgrade) test

    DBUP_START = "DB Upgrade Start"
    DBUP_END = "DB Upgrade Test End"

    def parse_dbup_start(self, line):
        if line.startswith(self.DBUP_START):
            #self.ts_name = line[len(self.STR_START):].rstrip()
            self.stage = 'db upgrade test'
            #if self.ts_name == self.TS_PARTS[self.current_ts_part]:
            self.parser = self.parse_dbup
            self.collector[:] = [line]

    def parse_dbup(self, line):
        if line.startswith(self.DBUP_END):
            self.parser = self.parse_dbup_tail
        elif not self._dbup_check_fail(line):
            self.collector.append(line)

    def parse_dbup_failed(self, line): # TODO: it's similar to parse_timesync_failed, refactor it!
        ToSend.log(line)
        if line.startswith("FAILED (failures"):
            ToSend.log("DB Upgrade test done")
            self.set_end()

    def parse_dbup_tail(self, line): # TODO: it's similar to parse_timesync_tail, refactor it!
        if not self._dbup_check_fail(line) and line.startswith("OK"):
            ToSend.log("DB Upgrade test done")
            self.set_end()

    def _dbup_check_fail(self, line): # TODO: it's similar to _ts_check_fail, refactor it!
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        #print ":::::" + line
        ToSend.log("DB Upgrade test %s!",
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            ToSend.log(s)
        ToSend.log(line)
        del self.collector[:]
        self.parser = self.parse_dbup_failed
        return True
    #

    def set_end(self):
        self.parser = self.skip_to_the_end
        self.stage = "ending"

    def skip_to_the_end(self, line):
        pass


def read_functest_output(proc, reader, from_test=''):
    """
    :param proc: Process
    :param reader: pipereader.PipeReader
    :param from_test: str
    :return: bool
    """
    last_lines = deque(maxlen=conf.FUNCTEST_LAST_LINES)
    success = True
    p = FunctestParser()
    if from_test == 'timesync':
        p.parser = p.parse_timesync_start
    elif from_test == 'msarch':
        p.parser = p.parse_msarch_start
    elif from_test == 'stream':
        p.parser = p.parse_stream_start

    while reader.state == pipereader.PIPE_READY:
        line = reader.readline(conf.FT_PIPE_TIMEOUT)
        if len(line) > 0:
            last_lines.append(line)
            #debug("FT: %s", line.lstrip())
            if line.startswith("ALL AUTOMATIC TEST ARE DONE"):
                p.set_end()
            else:
                p.parser(line)
    #else: # end reading
    #    pass

    state_error = reader.state in (pipereader.PIPE_HANG, pipereader.PIPE_ERROR)
    if state_error:
        ToSend.log((
            "[ functional tests has TIMED OUT on %s stage ]" if reader.state == pipereader.PIPE_HANG else
            "[ PIPE ERROR reading functional tests output on %s stage ]") % p.stage)
        ToSend.log("Last %s lines:\n%s", len(last_lines), "\n".join(last_lines))
        success = False

    proc.limited_wait(conf.TEST_TERMINATION_WAIT)

    if proc.poll() is None:
        if not state_error:
            debug("Functional test hasn't finished for %.1f seconds after the %s stage", conf.TEST_TERMINATION_WAIT, p.stage)
        kill_proc(proc)
        proc.wait()
        if not state_error:
            debug("The last test stage was %s. Last %s lines are:\n%s" %
                  (p.stage, len(last_lines), "\n".join(last_lines)))
        success = False

    if proc.returncode != 0:
        if proc.returncode < 0:
            if not (proc.returncode == -signal.SIGTERM and reader.state == pipereader.PIPE_HANG): # do not report signal if it was ours kill result
                signames = SignalNames.get(-proc.returncode, [])
                signames = ' (%s)' % (','.join(signames),) if signames else ''
                ToSend.log("[ FUNCTIONAL TESTS HAVE BEEN INTERRUPTED by signal %s%s ]" % (-proc.returncode, signames))
        else:
            ToSend.log("[ FUNCTIONAL TESTS' RETURN CODE = %s ]\n"
                        "The last test stage was %s. Last %s lines are:\n%s" %
                        (proc.returncode, p.stage, len(last_lines), "\n".join(last_lines)))
        success = False
    return success


T_FAIL = 'FAIL: '
T_DONE = 'Test complete.'

def read_misctest_output(proc, reader, name):
    collector = []  # FIXME what about using deque?
    success = True
    reading = True
    while reader.state == pipereader.PIPE_READY:
        line = reader.readline(conf.FT_PIPE_TIMEOUT)
        #print ":DEBUG: " + line.rstrip()
        if reading and len(line) > 0:
            collector.append(line)
            if line.startswith(T_FAIL):
                #print ":DEBUG: Fail detected!"
                success = False
            elif line.startswith(T_DONE):
                log("%s test done." % name.capitalize())
                reading = False

    if not success:
        ToSend.log("%s test failed:\n%s", real_caps(name), "\n".join(collector))
        collector = []

    state_error = reader.state in (pipereader.PIPE_HANG, pipereader.PIPE_ERROR)
    if state_error:
        ToSend.log(
            ("[ %s test has TIMED OUT ]" % name) if reader.state == pipereader.PIPE_HANG else
            ("[ PIPE ERROR reading %s test's output ]" % name))
        success = False

    proc.limited_wait(conf.TEST_TERMINATION_WAIT)

    if proc.returncode is None:
        if not state_error:
            debug("The functional test %s hasn't finished for %.1f seconds", name, conf.TEST_TERMINATION_WAIT)
        kill_proc(proc)
        proc.wait()

    if proc.returncode != 0:
        if proc.returncode < 0:
            if not (proc.returncode == -signal.SIGTERM and reader.state == pipereader.PIPE_HANG): # do not report signal if it was ours kill result
                signames = SignalNames.get(-proc.returncode, [])
                signames = ' (%s)' % (','.join(signames),) if signames else ''
                ToSend.log("[ %s TEST HAVE BEEN INTERRUPTED by signal %s%s ]" % (name.upper(), -proc.returncode, signames))
        else:
            ToSend.log("[ %s TESTS' RETURN CODE = %s ]" % (name.upper(), proc.returncode))
        success = False

    if (not success) and collector:
        ToSend.log("Test's output:\n%s", "\n".join(collector))
    return success


#####################################

def get_boxes_status():
    try:
        data = check_output(conf.VAGR_STAT, stderr=STDOUT, universal_newlines=True, cwd=conf.VAG_DIR, shell=False)
        step = 0
        rx = re.compile(r"(\S+)\s+([^(]+)")
        info = []
        for line in data.split("\n"):
            if step == 0:
                if line.rstrip() == "Current machine states:":
                    step = 1 # skip one empty line
            elif step == 1:
                step = 2
            elif step == 2:
                if line.rstrip() == '':
                    break
                m = rx.search(line)
                if m:
                    info.append([m.group(1), m.group(2).rstrip()])
        return info
    except CalledProcessError, e:
        log("ERROR: `%s` call returns %s code. Output:\n%s", ' '.join(conf.VAGR_STAT), e.returncode, e.output)
        return []


def show_boxes():
    "Print out vargant boxes status."
    info = get_boxes_status()
    if not info:
        logPrint("Empty vagrant reply!")
        return
    namelen = max(len(b[0]) for b in info)
    for box in info:
        logPrint("%s  [%s]" % (box[0].ljust(namelen), box[1]))

#####################################

# which options are allowed to be used with --nobox
FUNCTEST_ARGS = ('functest', 'timesync', 'httpstress', 'msarch', 'natcon', 'stream')
ARGS_EXCLUSIVE = (
    ('nobox', 'boxes', 'boxoff', 'showboxes'),
) + tuple(('no_functest', opt) for opt in FUNCTEST_ARGS)


def any_functest_arg():
    return any(getattr(Args, opt) for opt in FUNCTEST_ARGS)


def check_debug_mode():
    if conf.DEBUG and Args.prod:
        conf.DEBUG = False
    elif not conf.DEBUG and Args.debug:
        conf.DEBUG = True
    if conf.DEBUG:
        logPrint("Debug mode ON")


def check_args_correct():
    if Args.full_build_log and not Args.stdout:
        logPrint("ERROR: --full-build-log option requires --stdout!\n")
        sys.exit(2)
    for block in ARGS_EXCLUSIVE:
        if sum(1 if getattr(Args, opt, None) else 0 for opt in block) > 1:
            logPrint("Arguments %s are mutual exclusive!" % (args2str(block),))
            sys.exit(2)
    if Args.nobox and not any_functest_arg():
        logPrint("ERROR: --nobox is allowed only with options %s\n" % (args2str(FUNCTEST_ARGS),))
        sys.exit(2)
    if Args.add and (Args.boxes is None):
        logPrint("ERROR: --add is usable only with --boxes")
        sys.exit(2)


#def get_architecture():
#    #TODO move all paths into testconf.py !
#    curconf_fn = os.path.join(conf.PROJECT_ROOT, 'build_variables', 'target', 'current_config')
#    av = 'arch='
#    try:
#        with open(curconf_fn) as f:
#            for line in f:
#                if line.startswith(av):
#                    return line[len(av):].rstrip()
#    except IOError as err:
#        if err.errno == errno.ENOENT:
#            pass
#    return ''


def get_server_package_name():
    #TODO move all paths into testconf.py !
    if Build.arch == '':
        Build.load_vars(safe=True)

    if Build.arch == '':
        raise FuncTestError("Can't find server package: architecture not found!")

    deb_path = os.path.join('debsetup', 'mediaserver-deb', Build.arch)
    fn = os.path.join(conf.PROJECT_ROOT, deb_path, 'finalname-server.properties')
    fv = 'server.finalName='
    debfn = ''
    if not os.path.isfile(fn):
        return None
    with open(fn) as f:
        for line in f:
            if line.startswith(fv):
                debfn = line[len(fv):].rstrip() + '.deb'
                break

    if debfn == '':
        raise FuncTestError("Server package .deb file name not found!")

    return os.path.join(conf.PROJECT_ROOT, deb_path, 'deb', debfn)


def get_testcamera_path():
    return os.path.join(conf.PROJECT_ROOT, 'build_environment', 'target', 'bin', conf.MVN_BUILD_CONFIG, 'testcamera')


#def fix_project_root():
#    import testconf
#    testconf.PROJECT_ROOT = Args.path
#    testconf._fix_paths(override=True)
#    vars = globals()
#    for name in ('PROJECT_ROOT', 'TARGET_PATH', 'BIN_PATH', 'LIB_PATH', 'SUBPROC_ARGS'):
#        vars[name] = getattr(testconf, name)
#    debug("Using project root at %s", PROJECT_ROOT)


def set_paths():
    if conf.TEMP == '':
        conf.TEMP = os.getcwd()

    if Args.path is not None:
        conf.PROJECT_ROOT = Args.path
    if conf.PROJECT_ROOT.startswith('~'):
        conf.PROJECT_ROOT = os.path.expanduser(conf.PROJECT_ROOT)
    conf.PROJECT_ROOT = os.path.abspath(conf.PROJECT_ROOT)
    conf.SUBPROC_ARGS['cwd'] = conf.PROJECT_ROOT

    if not os.path.isdir(conf.PROJECT_ROOT):
        raise EnvironmentError(errno.ENOENT, "The project root directory %s isn't found", conf.PROJECT_ROOT)
    if not os.access(conf.PROJECT_ROOT, os.R_OK|os.W_OK|os.X_OK):
        raise IOError(errno.EACCES, "Full access to the project root directory required", conf.PROJECT_ROOT)
    debug("Using project root at %s", conf.PROJECT_ROOT)

    conf.BUILD_CONF_PATH = os.path.join(conf.PROJECT_ROOT, conf.BUILD_CONF_SUBPATH)


def parse_args():
    parser = argparse.ArgumentParser()
    #TODO: add parameters: usage, description

    # Run mode
    # No args -- just build and test current project (could be modified by -p, -t, -u)
    parser.add_argument("-a", "--auto", action="store_true", help="Continuos full autotest mode.")
    parser.add_argument("-t", "--test-only", action='store_true', help="Just run existing tests again (add --noft to skip functests.")
    parser.add_argument("-r", "--rebuild", action='store_true', help="(Re)build even if no new commits found.")
    parser.add_argument("-u", "--build-ut-only", action="store_true", help="Build and run unit tests only, don't (re-)build the project itself.")
    parser.add_argument("-g", "--hg-only", action='store_true', help="Only checks if there any new changes to get.")
    parser.add_argument("-f", "--full", action="store_true", help="Full test for all configured branches. (Not required with -b)")
    parser.add_argument("--functest", "--ft", action="store_true", help="Create virtual boxes and run functional test on them.")
    parser.add_argument("--no-functest", "--noft", action="store_true", help="Only build the project and run unittests.")
    parser.add_argument("--timesync", "--ts", action="store_true", help="Create virtual boxes and run time synchronization functional test only.")
    parser.add_argument("--httpstress", '--hst', action="store_true", help="Create virtual boxes and run HTTP stress test only.")
    parser.add_argument("--msarch", action="store_true", help="Create virtual boxes and run multiserver archive test only.")
    parser.add_argument("--natcon", action="store_true", help="Create virtual boxes for NAT connection test and run this test only.")
    parser.add_argument("--stream", action="store_true", help="Create virtual boxes and run Streaming tests only.")
    parser.add_argument("--nobox", "--nb", action="store_true", help="Do not create and destroy virtual boxes. (For the development and debugging.)")
    parser.add_argument("--conf", action='store_true', help="Show configuration and exit.")
    # change settings
    parser.add_argument("-b", "--branch", action='append', help="Branches to test (as with -f) instead of configured branch list. Multiple times accepted.\n"
                                                                "Use '.' for a current branch (it WILL update to the last commit of the branch, and it will ignore all other -b). ")
    parser.add_argument("-p", "--path", help="Path to the project directory to use instead of the default one")
    parser.add_argument("-T", "--threads", type=int, help="The number of threads to be used by maven (for -T mvn argument). Use '-T 0' to override configured default and use maven's default.")
    # output control
    parser.add_argument("-o", "--stdout", action="store_true", help="Don't send email, print resulting text to stdout.")
    parser.add_argument("-l", "--full-build-log", action="store_true", help="Print full build log, immediate. Use with -o only.")
    parser.add_argument("-w", "--warnings", action='store_true', help="Treat warnings as error, report even if no errors but some strange output from tests")
    parser.add_argument("--debug", action='store_true', help="Run in debug mode (more messages)")
    parser.add_argument("--prod", action='store_true', help="Run in production mode (turn off debug messages)")
    # utillity actions
    parser.add_argument("--boxes", "--box", help="Start virtual boxes and wait the mediaserver comes up.", nargs='?', const="")
    parser.add_argument('--add', action='store_true', help='Start new boxes without closing existing boxes')
    parser.add_argument("--boxoff", "--b0", help="Stop virtual boxes and wait the mediaserver comes up.", nargs='?', const="")
    parser.add_argument("--showboxes", '--sb', action="store_true", help="Check and show vagrant boxes states")

    global Args
    Args = parser.parse_args()
    check_args_correct()
    if Args.auto or Args.hg_only or Args.branch:
        Args.full = True # to simplify checks in run()
    if Args.threads is not None:
        MVN_THREADS = Args.threads
    check_debug_mode()


def set_branches():
    if Args.branch:
        change_branch_list()
    elif not Args.full:
        conf.BRANCHES = ['.']
    if conf.BRANCHES[0] == '.':
        conf.BRANCHES[0] = current_branch_name()
    if Args.full and not Args.branch:
        log("Watched branches: " + ','.join(conf.BRANCHES))


def change_branch_list():
    conf.BRANCHES = Args.branch
    if '.' in conf.BRANCHES and len(conf.BRANCHES) > 1:
        log("WARNING: there is '.' branch in the branch list -- ALL other branches will be skipped!")
        conf.BRANCHES = ['.']


#def get_pom_modules

def get_ut_names():
    """
    Parses unit_tests/pom.xml finding unittests modules names.
    If it fails, returns global TESTS.
    """
    path = os.path.join(conf.PROJECT_ROOT, conf.UT_SUBDIR, "pom.xml")
    #ns = 'http://maven.apache.org/POM/4.0.0'
    try:
        tree = ET.parse(path)
        # extract the default namespace, the root element of pom.xml should be 'project' from this namespace
        m = re.match("(\{[^}]+\}).+", tree.getroot().tag)
        # unfortunately, xml.etree.ElementTree adds namespace to all tags and there is no way to use clear tag names
        pomtests = [el.text.strip() for el in tree.findall('{0}modules/{0}module'.format(m.group(1) if m else ''))]
        if pomtests:
            debug("ut list found: %s", pomtests)
            return pomtests
        else:
            log("WARBING: No <module>s found in %s" % path)
            # and go further to the end of the function
    except Exception, e:
        log("Error loading %s: %s", path, e)
    log("Use default unittest names: %s", conf.TESTS)
    return conf.TESTS


def show_conf():
    # TODO update it!
    print "(Warning: this function is outdated a bit.)"
    print "Configuration parameters used:"
    print "DEBUG = %s" % conf.DEBUG
    print "PROJECT_ROOT = %s" % conf.PROJECT_ROOT
    #print "TARGET_PATH = %s" % TARGET_PATH
    #print "BIN_PATH = %s" % BIN_PATH
    #print "LIB_PATH = %s" % LIB_PATH
    print "BRANCHES = %s" % (', '.join(conf.BRANCHES),)
    print "TESTS = %s" % (', '.join(conf.TESTS),)
    print "HG_CHECK_PERIOD = %s" % conf.HG_CHECK_PERIOD
    print "UT_PIPE_TIMEOUT = %s" % conf.UT_PIPE_TIMEOUT
    print "FT_PIPE_TIMEOUT = %s" % conf.FT_PIPE_TIMEOUT
    print "BUILD_LOG_LINES = %s" % conf.BUILD_LOG_LINES
    print "MVN_THREADS = %s" % conf.MVN_THREADS
    print "Boxes names used:", ", ".join(conf.BOX_NAMES[name] for name in ('Box1', 'Box2', 'Nat', 'Behind'))


def updateBoxesNames():
    dest = conf.BOXES_NAMES_FILE
    rbTime = get_file_time(dest)
    confTime = max(
        get_file_time(conf.__file__),
        get_file_time(conf.testconf_local.__file__) if hasattr(conf, 'testconf_local') else 0
    )
    if rbTime < confTime:
        if os.path.exists(conf.BOXES_NAMES_FILE):
            os.rename(conf.BOXES_NAMES_FILE, conf.BOXES_NAMES_FILE + '.bak')
        with open(conf.BOXES_NAMES_FILE, "wt") as out:
            print >>out, """# -*- mode: ruby -*-
# vi: set ft=ruby :
# AUTOGENERATED FILE, DON'T MODIFY!
# Change the BOX_NAMES dict in the testconf.py or, better, testconf_local.py instead
module Boxes"""
            for name, value in conf.BOX_NAMES.iteritems():
                print >>out, '    %s = "%s"' % (name, value)
            print >>out, "end"
            print >>out, "# Created at %s" % (time.asctime())



def run_auto_loop():
    "Runs check-build-test sequence for all branches repeatedly."
    while True:
        t = time.time()
        log("Checking...")
        run()
        t = max(conf.MIN_SLEEP, conf.HG_CHECK_PERIOD - (time.time() - t))
        log("Sleeping %s secs...", t)
        wake_time = time.time() + t
        while time.time() < wake_time:
            time.sleep(1)
            check_control_flags()
    log("Finishing...")


def main():
    parse_args()
    drop_flag(conf.RESTART_FLAG)
    drop_flag(conf.STOP_FLAG)
    set_paths()
    set_branches()

    if Args.conf:
        show_conf() # changes done by other options are shown here
        return True

    updateBoxesNames()

    if Args.showboxes:
        show_boxes()
        return True

    if Args.boxes is not None:
        start_boxes(Args.boxes, keep=Args.add)
        return True

    if Args.boxoff is not None:
        stop_boxes(Args.boxoff, True)
        return True

    if Args.auto:
        log("Starting...")
    else:
        RunTime.go()

    FailTracker.load()

    if Args.auto:
        run_auto_loop()

    elif (not Args.no_functest) and any_functest_arg():  # virtual boxes functest only
        ToSend.clear()
        if not perform_func_test(get_tests_to_skip(conf.BRANCHES[0])):
            if ToSend.count() and not Args.stdout:
                email_notify("Debug %s" % (
                    "func" if Args.functest else
                    "timesync" if Args.timesync else
                    "http-stress" if Args.httpstress else
                    "multiserver archive" if Args.msarch else
                    "streaming" if Args.stream else
                    "NAT-connection" if Args.natcon else
                    "UNKNOWN!!!"),
                ToSend.lines)
            return False
        return True

    else:
        return run()


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf8')
    try:
        if not main():
            debug("Something isn't OK, returning code 1")
            debug("Results: %s", RESULT)
            sys.exit(1)
        else:
            debug("Results: %s", RESULT)
    finally:
        RunTime.report()

# TODO: with -o turn off output lines accumulator, just print 'em
# Check . branch processing in full test
#
