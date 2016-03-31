#!/usr/bin/env python
# -*- coding: utf-8 -*-
#TODO: ADD THE DESCRIPTION!!!
import sys, os, os.path, time, re
from subprocess import Popen, PIPE, STDOUT, CalledProcessError, check_call, check_output, call as subcall
from collections import deque
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

from testconf import *
import pipereader
from testboxes import boxssh
from functest_util import args2str, real_caps

__version__ = '1.2.2'

SUITMARK = '[' # all messages from a testsuit starts with it, other are tests' internal messages
FAILMARK = '[  FAILED  ]'
STARTMARK = '[ RUN      ]'
BARMARK = '[==========]'
OKMARK = '[       OK ]'

NameRx = re.compile(r'\[[^\]]+\]\s(\S+)')

RESTART_FLAG = './.restart'
STOP_FLAG = './.stop'
RESTART_BY_EXEC = True

FAIL_FILE = './fails.py' # where to save failed branches list

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


ToSend = []
FailedTests = []
Changesets = {}
Env = os.environ.copy()

Args = {}


def log_print(s):
    print s


def log(text, *args):
    log_print("[%s] %s" % (time.strftime("%Y.%m.%d %X %Z"), ((text % args) if args else text)))


def log_to_send(text, *args):
    if args:
        text = text % args
    log(text)
    ToSend.append(text)

def debug(text, *args):
    if DEBUG:
        if args:
            log_print("DEBUG: " + (text % args))
        else:
            log_print("DEBUG: " + text)


def email_send(mailfrom, mailto, cc, msg):
    msg['From'] = mailfrom
    msg['To'] = mailto
    if cc:
        if isinstance(cc, basestring):
            cc = [cc]
        mailto = [mailto] + cc
        msg['Cc'] = ','.join(cc)
    smtp = SMTP(SMTP_ADDR)
    if SMTP_LOGIN:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_LOGIN, SMTP_PASS)
    #smtp.set_debuglevel(1)
    smtp.sendmail(mailfrom, mailto, msg.as_string())
    smtp.quit()


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
    if Args.stdout:
        print text
    else:
        msg = MIMEText.MIMEText(text)
        msg['Subject'] = "Autotest run results on %s platform" % get_platform()
        email_send(MAIL_FROM, MAIL_TO, BRANCH_CC_TO.get(branch, []), msg)


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
        email_send(MAIL_FROM, MAIL_TO, BRANCH_CC_TO.get(branch, []), msg)


#####################################

class FailTracker(object):
    fails = set()

    @classmethod
    def mark_success(cls, branch):
        if branch in cls.fails:
            cls.fails.discard(branch)
            cls.save()
            log_to_send('')
            log_to_send("The branch %s is repaired after previous errors and makes no error now.", branch)
            if (branch in SKIP_TESTS and SKIP_TESTS[branch]) or SKIP_ALL:
                log_to_send("Note, that some tests have been skipped due to configuration.\nSkipped tests: %s",
                            ', '.join(SKIP_TESTS.get(branch, set()) | SKIP_ALL))

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
        if not os.path.isfile(FAIL_FILE):
            return
        try:
            with open(FAIL_FILE) as f:
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
        debug("Failed branches list loaded: %s", ', '.join(FailTracker.fails))

    @classmethod
    def save(cls):
        debug("FailTracker.save: %s", cls.fails)
        try:
            with open(FAIL_FILE, "w") as f:
                print >>f, repr(cls.fails)
        except Exception, e:
            log("Error saving failed branches list: %s", e)


def check_restart():
    if os.path.isfile(RESTART_FLAG):
        log("Restart flag founnd. Calling: %s", ([sys.executable] + sys.argv,))
        try:
            if RESTART_BY_EXEC:
                sys.stdout.flush()
                sys.stderr.flush()
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                proc = Popen([sys.executable] + sys.argv, shell=False)
                log("New copy of %s started with PID %s", sys.argv[0], proc.pid)
                timeout = time.time() + SELF_RESTART_TIMEOUT
                while os.path.isfile(RESTART_FLAG):
                    if time.time() > timeout:
                        raise RuntimeError("Can't start the new copy of process: restart flag hasn't been deleted for %s seconds" % SELF_RESTART_TIMEOUT)
                    time.sleep(0.1)
                log("The old proces goes away.")
                sys.exit(0)
        except Exception:
            log("Failed to restart: %s", traceback.format_exc())
            drop_flag(RESTART_FLAG)


def check_control_flags():
    check_restart()
    if os.path.isfile(STOP_FLAG):
        log("Stop flag found. Exiting...")
        os.remove(STOP_FLAG)
        sys.exit(0)


def drop_flag(flag):
    if os.path.isfile(flag):
        os.remove(flag)


def get_name(line):
    m = NameRx.match(line)
    return m.group(1) if m else ''


def check_repeats(repeats):
    if repeats > 1:
        ToSend[-1] += "   [ REPEATS %s TIMES ]" % repeats


def read_unittest_output(proc, reader):
    last_suit_line = ''
    has_errors = False
    has_stranges = False
    repeats = 0 # now many times the same 'strange' line repeats
    running_test_name = ''
    complete = False
    to_send_count = 0
    try:
        while reader.state == pipereader.PIPE_READY:
            line = reader.readline(UT_PIPE_TIMEOUT)
            if not complete and len(line) > 0:
                #debug("Line: %s", line.lstrip())
                if line.startswith(SUITMARK):
                    check_repeats(repeats)
                    repeats = 1
                    last_suit_line = line
                    if line.startswith(STARTMARK):
                        running_test_name = get_name(line) # remember to print OK test result and for abnormal termination case
                        to_send_count = len(ToSend)
                    elif line.startswith(FAILMARK) and not complete:
                        debug("Appending: %s", line.rstrip())
                        FailedTests.append(get_name(line))
                        ToSend.append(line)
                        running_test_name = ''
                        has_errors = True
                    elif line.startswith(OKMARK):
                        if running_test_name == get_name(line): # print it out only if there were any 'strange' lines
                            if to_send_count < len(ToSend):
                                ToSend.append(line)
                        else:
                            debug("!!!! running_test_name == get_name(line): %s; %s", running_test_name, line.rstrip())
                        running_test_name = ''
                    elif line.startswith(BARMARK) and not line[len(BARMARK):].startswith(" Running"):
                        complete = True
                else: # gather test's messages
                    if last_suit_line != '':
                        ToSend.append(last_suit_line)
                        last_suit_line = ''
                    if ToSend and (line == ToSend[-1]):
                        repeats += 1
                    else:
                        check_repeats(repeats)
                        repeats = 1
                        ToSend.append(line)
                    has_stranges = True
        else: # end reading
            check_repeats(repeats)

        if reader.state in (pipereader.PIPE_HANG, pipereader.PIPE_ERROR):
            ToSend.append((
                "[ test suit has TIMED OUT on test %s ]" if reader.state == pipereader.PIPE_HANG else
                "[ PIPE ERROR reading test suit output on test %s ]") % running_test_name)
            FailedTests.append(running_test_name)
            has_errors = True

        if proc.poll() is None:
            kill_test(proc, sudo=True)
            proc.wait()

        if proc.returncode != 0:
            if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
                ToSend.append("[ Test %s interrupted abnormally ]" % running_test_name)
                FailedTests.append(running_test_name)
            if proc.returncode < 0:
                if not (proc.returncode == -signal.SIGTERM and reader.state == pipereader.PIPE_HANG): # do not report signal if it was ours kill result
                    signames = SignalNames.get(-proc.returncode, [])
                    signames = ' (%s)' % (','.join(signames),) if signames else ''
                    ToSend.append("[ TEST SUIT HAS BEEN INTERRUPTED by signal %s%s ]" % (-proc.returncode, signames))
            else:
                ToSend.append("[ TEST SUIT'S RETURN CODE = %s ]" % proc.returncode)
            has_errors = True

        if has_stranges and not has_errors:
            ToSend.append("[ Tests passed OK, but has some output. ]")

    finally:
        if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
            FailedTests.append(running_test_name)


def call_test(testname, reader):
    log_to_send("[ Calling %s test suit ]", testname)
    old_len = len(ToSend)
    proc = None
    try:
        testpath = os.path.join(BIN_PATH, testname)
        if not os.access(testpath, os.F_OK):
            FailedTests.append('(all)')
            ToSend.append("Testsuit '%s' not found!" % testpath)
            return
        if not os.access(testpath, os.R_OK|os.X_OK):
            FailedTests.append('(all)')
            ToSend.append("Testsuit '%s' isn't accessible!" % testpath)
            return
        #debug("Calling %s", testpath)
        # sudo is required since some unittest start server
        # also we're to pass LD_LIBRARY_PATH through command line because LD_* env varsn't passed to suid processes
        #FIXME! Make it windows compatible! sudo and LD_LIBRARY_PATH iren't for Windows
        proc = Popen(['/usr/bin/sudo', '-E', 'LD_LIBRARY_PATH=%s' % Env['LD_LIBRARY_PATH'], testpath], bufsize=0, stdout=PIPE, stderr=STDOUT, env=Env, **SUBPROC_ARGS)
        #print "Test is started with PID", proc.pid
        reader.register(proc)
        read_unittest_output(proc, reader)
    except BaseException, e:
        tstr = traceback.format_exc()
        print tstr
        if isinstance(e, Exception):
            ToSend.append("[[ Tests call error:")
            ToSend.append(tstr)
            ToSend.append("]]")
        else:
            s = "[[ Tests has been interrupted:\n%s\n]]" % tstr
            ToSend.append(s)
            log(s)
            raise # it wont be catched and will allow the script to terminate
    finally:
        if proc:
            reader.unregister()
        if len(ToSend) == old_len:
            debug("No interesting output from these tests")
            del ToSend[-1]
        else:
            ToSend.append('')


def kill_test(proc, sudo=False):
    "Kills subproces under sudo"
    debug("Killing test process %s", proc.pid)
    if sudo and os.name == 'posix':
        subcall(['/usr/bin/sudo', 'kill', str(proc.pid)], shell=False)
    else:
        os.kill(proc.pid, signal.SIGTERM)
        #subcall(['kill', str(proc.pid)], shell=False)

def get_to_skip(branch):
    to_skip = set()
    if (branch in SKIP_TESTS) or SKIP_ALL:
        to_skip = SKIP_TESTS.get(branch, set()) | SKIP_ALL
        log("Configured to skip tests: %s", ', '.join(to_skip))
    return to_skip

def run_tests(branch):
    log("Running unit tests for branch %s" % branch)
    lines = []
    to_skip = get_to_skip(branch)
    reader = pipereader.PipeReader()

    if 'all_ut' not in to_skip:
        for name in get_ut_names():
            if name in to_skip:
                continue
            del ToSend[:]
            del FailedTests[:]
            call_test(name, reader)
            if FailedTests:
                debug("Failed tests: %s", FailedTests)
                if lines:
                    lines.append('')
                lines.append("Tests, failed in the %s test suit:" % name)
                lines.extend("\t" + name for name in FailedTests)
                lines.append('')
                lines.extend(ToSend)

    if not lines and not Args.no_functest:
        del ToSend[:]
        perform_func_test(to_skip)
        if ToSend:
            lines.append('')
            lines.extend(ToSend)
            del ToSend[:]

    if not lines:
        FailTracker.mark_success(branch)
        if ToSend:
            email_notify(branch, ToSend)
            del ToSend[:]

    if lines:
        #debug("Tests output:\n" + "\n".join(lines))
        FailTracker.mark_fail(branch)
        email_notify(branch, lines)


def filter_branch_names(branches):
    "Check names for exact eq with list, drop duplicates"
    # The problem is `hg in --branch` takes all branches with names beginning with --branch value. :(
    filtered = []
    for name in branches:
        if name in BRANCHES and not name in filtered:
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
    debug("Run: " + (' '.join(HG_REVLIST + ["--branch=%s" % branch, bundle_fn])))
    proc = Popen(HG_REVLIST + ["--branch=%s" % branch, bundle_fn], bufsize=1, stdout=PIPE, stderr=STDOUT, **SUBPROC_ARGS)
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
        cmd = HG_IN + [ "--branch=%s" % b for b in BRANCHES ] + ['--bundle', bundle_fn]
        debug("Run: %s", ' '.join(cmd))
        ready_branches = check_output(cmd, stderr=STDOUT, **SUBPROC_ARGS)
        if ready_branches:
            # Specifying the current branch (.) turns off all other
            branches = ['.'] if BRANCHES[0] == '.' else filter_branch_names(ready_branches.split(','))
            if BRANCHES[0] != '.':
                log_to_send('')  # an empty line separator
                log("Commits are found in branches: %s", branches)
            if branches:
                Changesets.clear()
                return [ b for b in branches if get_changesets(b, bundle_fn) ]
    except CalledProcessError, e:
        if e.returncode != 1:
            log("ERROR: `hg in` call returns %s code. Output:\n%s", e.returncode, e.output)
            raise
    log("No new commits found for controlled branches.")
    return []


def current_branch_name():
    try:
#        branch_name = check_output(HG_BRANCH, stderr=STDOUT, **SUBPROC_ARGS)
        branch_name = check_output(HG_BRANCH, stderr=None, **SUBPROC_ARGS)
        return branch_name.split("\n")[0]
    except CalledProcessError, e:
        if e.returncode != 1:
            log("ERROR: Failed to find current branch name: `hg branch` call returns %s code. Output:\n%s", e.returncode, e.output)
            raise


def update_repo(branches, bundle_fn):
    log("Pulling branches: %s" % (', '.join(branches)))
    #debug("Using bundle file %s", bundle_fn)
    #try:
    check_call(HG_PULL + [bundle_fn], **SUBPROC_ARGS)
    #except CalledProcessError, e:


def check_mvn_exit(proc, last_lines):
    stop = time.time() + MVN_TERMINATION_WAIT
    while proc.poll() is None and time.time() < stop:
        time.sleep(0.2)
    if proc.returncode is None:
        last_lines.append("*** Maven has hanged in the end!")
        log("Maven has hanged in the end!")
        kill_test(proc)
        if proc.poll() is None:
            time.sleep(0.5)
            proc.poll()
        debug("Unittest proces was killed. RC = %s", proc.returncode)


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
        proc = Popen(cmd, **kwargs)
        proc.wait()
    else:
        proc = Popen(cmd, bufsize=MVN_BUFFER, stdout=PIPE, stderr=STDOUT, **kwargs)
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
        # Project dependencies  error! Report but go on.
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
    last_lines = deque(maxlen=BUILD_LOG_LINES)
    log("Build %s (branch %s)...", "unit tests" if unit_tests else "netoptix_vms", branch)
    kwargs = SUBPROC_ARGS.copy()

    cmd = [MVN, "package", "-e", "-Dbuild.configuration=release"]
    if MVN_THREADS and not no_threads:
        cmd.extend(["-T", "%d" % MVN_THREADS])
    elif no_threads:
        cmd.extend(["-T", "1"])
    if single_project is not None:
        cmd.extend(['-pl', single_project])
    #cmd.extend(['--projects', 'nx_sdk,nx_storage_sdk,mediaserver_core'])

    if unit_tests:
        kwargs['cwd'] = os.path.join(kwargs["cwd"], UT_SUBDIR)
    debug("MVN: %s", cmd); time.sleep(1.5)

    try:
        retcode = execute_maven(cmd, kwargs, last_lines)
        if retcode != 0:
            log("Error calling maven: ret.code = %s" % retcode)
            if not Args.full_build_log:
                log("The last %d log lines:" % len(last_lines))
                log_print("".join(last_lines))
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
            log_print("".join(last_lines))
            email_build_error(branch, last_lines, unit_tests, crash=tb, single_project=(project_name if single_project else None))
        return False
    if no_threads and (project_name is not None):
        pass
    return True


def prepare_branch(branch):
    log_to_send('')  # an empty line separator
    if branch != '.':
        log("Switch to the branch %s" % branch)
    debug("Call %s", HG_PURGE)
    check_call(HG_PURGE, **SUBPROC_ARGS)
    debug("Call %s", HG_UP if branch == '.' else (HG_UP + ['--rev', branch]))
    check_call(HG_UP if branch == '.' else (HG_UP + ['--rev', branch]), **SUBPROC_ARGS)
    #debug("Going to call maven...")
    return call_maven_build(branch) and call_maven_build(branch, unit_tests=True)


def perform_check():
    "Check for repository updates, get'em, build and test"
    bundle_fn = os.path.join(TEMP, "in.hg")
    branches = check_new_commits(bundle_fn)
    if branches and not Args.hg_only:
        update_repo(branches, bundle_fn)
        for branch in branches:
            if prepare_branch(branch):
                run_tests(branch)
            else:
                FailTracker.mark_fail(branch)
    if os.access(bundle_fn, os.F_OK):
        os.remove(bundle_fn)


def run():
    try:
        if Args.full:
            perform_check()
            if Args.hg_only:
                log("Changesets:\n %s", "\n".join("%s\n%s" % (br, "\n".join("\t%s" % ch for ch in chs)) for br, chs in Changesets.iteritems()))
        else:
            if Args.test_only:
                log("Test only run...")
            if Args.test_only or (
                    (Args.build_ut_only or call_maven_build(BRANCHES[0])) and call_maven_build(BRANCHES[0], unit_tests=True)):
                run_tests(BRANCHES[0])
    except Exception:
        traceback.print_exc()


#####################################
def get_architecture():
    #TODO move all paths into testconf.py !
    curconf_fn = os.path.join(PROJECT_ROOT, 'build_variables/target/current_config')
    av = 'arch='
    try:
        with open(curconf_fn) as f:
            for line in f:
                if line.startswith(av):
                    return line[len(av):].rstrip()
    except IOError as err:
        if err.errno == errno.ENOENT:
            pass
    return ''


def get_server_package_name():
    #TODO move all paths into testconf.py !
    arch = get_architecture()

    if arch == '':
        raise FuncTestError("Can't find server package: architecture not found!")

    deb_path = os.path.join('debsetup', 'mediaserver-deb', arch)
    fn = os.path.join(PROJECT_ROOT, deb_path, 'finalname-server.properties')
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

    return os.path.join(PROJECT_ROOT, deb_path, 'deb', debfn)


def check_mediaserver_deb():
    # The same filename used for all versions here:
    # a) To remove (by override) any previous version automatically.
    # b) To use fixed name in the bootstrap.sh script
    try:
        src = get_server_package_name()
    except FuncTestError as err:
        print err
        print "Try to use the previously built deb-package (it could have a diferent version!)."
        src = None
    dest = os.path.join(VAG_DIR, 'networkoptix-mediaserver.deb')
#    debug("Src: %s\nDest: %s", src, dest)
    dest_stat = os.stat(dest) if os.path.isfile(dest) else None
    if src is None or not os.path.isfile(src):
        if dest_stat is None:
            raise FuncTestError("ERROR: networkoptix-mediaserver deb-package isn't found!")
#        else:
#            debug("No newly made mediaserver package found, using the old one.")
    else:
        src_stat = os.stat(src)
        if dest_stat is None or (src_stat.st_mtime > dest_stat.st_mtime or src_stat.st_size != dest_stat.st_size):
#            log("%s -> %s", src, dest)
            shutil.copy(src, dest) # put this name into config
        else:
            pass
#            log("%s is up to date", dest)


def start_boxes(boxes, keep = False):
    try:
        # 1. Get the .deb file
        check_mediaserver_deb()
        # 2. Start virtual boxes
        if not keep:
            log("Removing old vargant boxes...")
            check_call(VAGR_DESTROY, shell=False, cwd=VAG_DIR)
        if not boxes:
            log("Creating and starting vagrant boxes...")
        else:
            log("Creating and starting vagrant boxes: %s...", boxes)
        boxlist = boxes.split(',') if len(boxes) else []
        check_call(VAGR_RUN + boxlist, shell=False, cwd=VAG_DIR)
        failed = [b[0] for b in get_boxes_status() if b[0]in boxes and b[1] != 'running']
        if failed:
            log("ERROR: failed to start up the boxes: %s", ', '.join(failed))
            return False
        # 3. Wait for all mediaservers become ready (use /ec2/getMediaServers
        #to_check = [b for b in boxlist if b in CHECK_BOX_UP] if boxlist else CHECK_BOX_UP
        #wait_servers_ready([BOX_IP[b] for b in to_check])
        for box in (boxlist or BOX_POST_START.iterkeys()):
            if box in BOX_POST_START:
                boxssh(BOX_IP[box], ['/vagrant/' + BOX_POST_START[box]])
        time.sleep(SLEEP_AFTER_BOX_START)
        return True
    except FuncTestError as e:
        log("Virtual boxes start up failed: %s", e.message)
        return False
    except BaseException as e:
        log_to_send("Exception during virtual boxes start up:\n%s", traceback.format_exc())
        if not isinstance(e, Exception):
            raise # it wont be catched and will allow the script to terminate


def stop_boxes(boxes, destroy=False):
    try:
        if not boxes:
            log("Removing vargant boxes...")
        else:
            log("Removing vargant boxes: %s...", boxes)
        boxlist = boxes.split(',') if len(boxes) else []
        cmd = VAGR_DESTROY if destroy else VAGR_STOP
        check_call(cmd + boxlist, shell=False, cwd=VAG_DIR)
    except BaseException as e:
        log_to_send("Exception during virtual boxes start up:\n%s", traceback.format_exc())
        if not isinstance(e, Exception):
            raise # it wont be catched and will allow the script to terminate


#####################################
# Functional tests block
def wait_servers_ready(iplist):
    urls = ['http://%s:%s/ec2/getMediaServersEx' % (ip, MEDIASERVER_PORT) for ip in iplist]
    print "wait_servers_ready: urls: %s" % (urls,)
    not_ready = set(urls)
    # 1. Prepare authentication for http queries
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    for u in urls:
        passman.add_password(None, u, MEDIASERVER_USER, MEDIASERVER_PASS)
    urllib2.install_opener(urllib2.build_opener(urllib2.HTTPDigestAuthHandler(passman)))
    # 2. Wait for responses for query
    # For each URL check number of servers online
    too_slow = time.time() + len(urls) * ALL_START_TIMEOUT_BASE
    while not_ready:
        for url in urls:
            if time.time() > too_slow:
                raise FuncTestError("Server start timed out! Functional tests wasn't performed.")
            if url in not_ready:
                try:
                    jdata = urllib2.urlopen(url, timeout=START_CHECK_TIMEOUT).read()
                    # Check response for 'status' field (Online/Offline) for all servers
                except Exception, e:
                    print "wait_servers_ready(%s): urlopen error: %s" % (url, e,)
                    continue # wait for good response or for global timeout
                try:
                    data = json.loads(jdata)
                except ValueError, e:
                    print "wait_servers_ready(%s): json.loads error: %s" % (url, e,)
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
    log("Running functional tests: %s", cmd)
    return cmd, only_test

FUNCTEST_TBL = (
    ('timesync', ),
    ('bstorage', ),
    ('msarch', ),
    ('stream', ),
    ('natcon', ),
)

def perform_func_test_new(to_skip):
    if os.name != 'posix':
        print "\nFunctional tests require POSIX-compatible OS. Skipped."
        return
    need_stop = False
    reader = proc = None


def perform_func_test(to_skip):
    if os.name != 'posix':
        print "\nFunctional tests require POSIX-compatible OS. Skipped."
        return
    need_stop = False
    reader = proc = None
    try:
        if not Args.nobox:
            start_boxes('box1' if Args.natcon else 'box1,box2')
            need_stop = True
        # 4. Call functest/main.py (what about imoirt it and call internally?)
        if os.path.isfile(".rollback"): # TODO: move to config or import from functest.py
            os.remove(".rollback")
        reader = pipereader.PipeReader()
        sub_args = {k: v for k, v in SUBPROC_ARGS.iteritems() if k != 'cwd'}
        unreg = False

        only_test = ''
        if not Args.httpstress:
            unreg = True
            cmd, only_test = mk_functest_cmd(to_skip)
            if only_test != 'natcon':
                proc = Popen(cmd, bufsize=0, stdout=PIPE, stderr=STDOUT, **sub_args)
                reader.register(proc)
                read_functest_output(proc, reader, only_test)

            if (not only_test or only_test == 'natcon') and 'natcon' not in to_skip:
                if not only_test:
                    cmd = BASE_FUNCTEST_CMD + NATCON_ARGS
                    reader.unregister()
                if not Args.nobox:
                    stop_boxes('box2')
                    start_boxes('boxnat,boxbehind', keep=True)
                log("Running connection behind NAT test: %s", cmd)
                proc = Popen(cmd, bufsize=0, stdout=PIPE, stderr=STDOUT, **sub_args)
                reader.register(proc)
                read_misctest_output(proc, reader, "connection behind NAT")

        if not only_test and not Args.natcon and 'httpstress' not in to_skip:
            if unreg:
                reader.unregister()
                unreg = False
            boxssh(BOX_IP['box1'], ('/vagrant/safestart.sh', 'networkoptix-mediaserver'))  #FIXME rewrite using the generic way with ctl.sh
            url = "%s:%s" % (BOX_IP['box1'], MEDIASERVER_PORT)
            cmd = [sys.executable, "-u", "stresst.py", "--host", url, "--full", "20,40,60", "--threads", "10"]
            #TODO add test durations to config
            #TODO add -threads value to config
            #TODO add the test duration and a server hang timeout
            log("Running http stress test: %s", cmd)
            proc = Popen(cmd, bufsize=0, stdout=PIPE, stderr=STDOUT, **sub_args)
            reader.register(proc)
            unreg = True
            #TODO make it a part of the functest.py
            read_misctest_output(proc, reader, "http stress")

    except FuncTestError, e:
        log("Functional test aborted: %s", e.message)
    except BaseException, e:
        log_to_send("Exception during functional test run:\n%s", traceback.format_exc())
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
            check_call(VAGR_STOP, shell=False, cwd=VAG_DIR)


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

        @parser.setter
        def parser(self, value):
            self._parser = value
            print "* Set parser: %s" % value

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
            log_to_send("Functional test %s!", "failed" if is_fail else "reports an error")
            log_to_send(line)
        elif line.startswith("Main tests passed OK"):
            log("Main functest done.")
            self.parser = self.parse_merge_start
            self.stage = 'wait for Merge server test'

    def parse_main_failed(self, line):  # FT_MAIN_FAILED
        log_to_send(line)
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
            log_to_send("Functional test %s on Merge Server test!", "failed" if is_fail else "reports an error")
            for s in self.collector:
                log_to_send(s)
            log_to_send(line)
            del self.collector[:]
            self.parser = self.parse_merge_failed
        else:
            self.collector.append(line)

    def parse_merge_failed(self, line):  # FT_MERGE_FAILED
        log_to_send(line)
        if line.startswith(self.MERGE_END):
            self._merge_test_end()

    def _merge_test_end(self):
        self.parser = self.parse_sysname_start #if success else self.parse_proxy_start
        self.stage = 'wait for SystemName test'
        log("Merge Server test done.")

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
            log_to_send("Functional test %s on SystemName test!", "failed" if is_fail else "reports an error")
            for s in self.collector:
                log_to_send(s)
            log_to_send(line)
            del self.collector[:]
            self.parser = self.parse_sysname_failed
        else:
            self.collector.append(line)

    def parse_sysname_failed(self, line):
        log_to_send(line)
        if line.startswith(self.SYSNAME_END):
            self._sysname_test_end()

    def _sysname_test_end(self):
        log("SystemName test done.")
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
            log_to_send("Functional test %s on Server Proxy test!", "failed" if is_fail else "reports an error")
            for s in self.collector:
                log_to_send(s)
            log_to_send(line)
            del self.collector[:]
            self.parser = self.parse_proxy_failed
        else:
            self.collector.append(line)

    def parse_proxy_failed(self, line):  # FT_MERGE_FAILED
        log_to_send(line)
        if line.startswith(self.PROXY_END):
            self._proxy_test_end()

    def _proxy_test_end(self):
        self.parser = self.parse_timesync_start  #if success else self.parse_proxy_start
        self.stage = 'wait for timesync test'
        log("Server Proxy test done.")

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
                log_to_send(line)
                log_to_send("ERROR: unknow tymesync test part: " + self.ts_name)
                self.parser = self.parse_timesync_failed
            self.stage = "time synchronization test: " + self.ts_name

    def parse_timesync(self, line):
        if line.startswith(self.TS_END):
            self.parser = self.parse_timesync_tail
        elif not self._ts_check_fail(line):
            self.collector.append(line)

    def parse_timesync_failed(self, line):
        log_to_send(line)
        if line.startswith("FAILED (failures"):
            self._end_timesync()

    def parse_timesync_tail(self, line):
        if not self._ts_check_fail(line) and line.startswith("OK ("):
            self._end_timesync()

    def _ts_check_fail(self, line):
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        log_to_send("Time synchronization test %s %s!", self.ts_name,
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            log_to_send(s)
        log_to_send(line)
        del self.collector[:]
        self.parser = self.parse_timesync_failed
        return True

    def _end_timesync(self):
        log("Timesync test %s done", self.ts_name)
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
        log_to_send(line)
        if line.startswith("FAILED (failures"):
            log("Backup storage test done")
            self.parser = self.parse_msarch_start

    def parse_bstorage_tail(self, line): # TODO: it's similar to parse_timesync_tail, refactor it!
        if not self._bs_check_fail(line) and line.startswith("OK"):
            log("Backup storage test done")
            self.parser = self.parse_msarch_start

    def _bs_check_fail(self, line): # TODO: it's similar to _ts_check_fail, refactor it!
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        log_to_send("Backup storage test %s!",
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            log_to_send(s)
        log_to_send(line)
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
        log_to_send(line)
        if line.startswith("FAILED (failures"):
            log("Multiserver archive test done")
            self.parser = self.parse_stream_start

    def parse_msarch_tail(self, line): # TODO: it's similar to parse_timesync_tail, refactor it!
        if not self._ms_check_fail(line) and line.startswith("OK"):
            log("Multiserver archive test done")
            self.parser = self.parse_stream_start

    def _ms_check_fail(self, line): # TODO: it's similar to _ts_check_fail, refactor it!
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        #print ":::::" + line
        log_to_send("Multiserver archive test %s!",
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            log_to_send(s)
        log_to_send(line)
        del self.collector[:]
        self.parser = self.parse_msarch_failed
        return True

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
        log_to_send(line)
        if line.startswith("FAILED (failures"):
            log("Streaming test done")
            self.set_end()

    def parse_stream_tail(self, line): # TODO: it's similar to parse_timesync_tail, refactor it!
        if not self._str_check_fail(line) and line.startswith("OK"):
            log("Streaming test done")
            self.set_end()

    def _str_check_fail(self, line): # TODO: it's similar to _ts_check_fail, refactor it!
        if not (line.startswith(self.FAIL_MARK) or line.startswith(self.ERROR_MARK)):
            return False
        self.has_errors = True
        #print ":::::" + line
        log_to_send("Streaming test %s!",
                    "failed" if line.startswith(self.FAIL_MARK) else "reports an error")
        for s in self.collector:
            log_to_send(s)
        log_to_send(line)
        del self.collector[:]
        self.parser = self.parse_stream_failed
        return True
    #

    def set_end(self):
        self.parser = self.skip_to_the_end
        self.stage = "ending"

    def skip_to_the_end(self, line):
        pass


def read_functest_output(proc, reader, from_test=''):
    last_lines = deque(maxlen=FUNCTEST_LAST_LINES)
    p = FunctestParser()
    if from_test == 'timesync':
        p.parser = p.parse_timesync_start
    elif from_test == 'msarch':
        p.parser = p.parse_msarch_start
    elif from_test == 'stream':
        p.parser = p.parse_stream_start
    while reader.state == pipereader.PIPE_READY:
        line = reader.readline(FT_PIPE_TIMEOUT)
        if len(line) > 0:
            last_lines.append(line)
            #debug("FT: %s", line.lstrip())
            #debug("FT: %s", line.lstrip())
            if line.startswith("ALL AUTOMATIC TEST ARE DONE"):
                p.set_end()
            else:
                p.parser(line)
    else: # end reading
        pass

    if reader.state in (pipereader.PIPE_HANG, pipereader.PIPE_ERROR):
        log_to_send((
            "[ functional tests has TIMED OUT on %s stage ]" if reader.state == pipereader.PIPE_HANG else
            "[ PIPE ERROR reading functional tests output on %s stage ]") % p.stage)
        log_to_send("Last %s lines:\n%s", len(last_lines), "\n".join(last_lines))
        #has_errors = True

    t = time.time() + 5.0 # wait a bit
    while proc.poll() is None and time.time() < t:
        time.sleep(0.1)

    if proc.poll() is None:
        kill_test(proc)
        proc.wait()
        debug("The last test stage was %s. Last %s lines are:\n%s" %
              (p.stage, len(last_lines), "\n".join(last_lines)))

    if proc.returncode != 0:
        if proc.returncode < 0:
            if not (proc.returncode == -signal.SIGTERM and reader.state == pipereader.PIPE_HANG): # do not report signal if it was ours kill result
                signames = SignalNames.get(-proc.returncode, [])
                signames = ' (%s)' % (','.join(signames),) if signames else ''
                log_to_send("[ FUNCTIONAL TESTS HAVE BEEN INTERRUPTED by signal %s%s ]" % (-proc.returncode, signames))
        else:
            log_to_send("[ FUNCTIONAL TESTS' RETURN CODE = %s ]\n"
                        "The last test stage was %s. Last %s lines are:\n%s" %
                        (proc.returncode, p.stage, len(last_lines), "\n".join(last_lines)))
        #has_errors = True


T_FAIL = 'FAIL: '
T_DONE = 'Test complete.'

def read_misctest_output(proc, reader, name):
    collector = []
    has_errors = False
    reading = True
    while reader.state == pipereader.PIPE_READY:
        line = reader.readline(FT_PIPE_TIMEOUT)
        #print ":DEBUG: " + line.rstrip()
        if reading and len(line) > 0:
            collector.append(line)
            if line.startswith(T_FAIL):
                #print ":DEBUG: Fail detected!"
                has_errors = True
            elif line.startswith(T_DONE):
                log("%s test done." % name.capitalize())
                reading = False

    if has_errors:
        log_to_send("%s test failed:\n%s", real_caps(name), "\n".join(collector))
        collector = []

    if reader.state in (pipereader.PIPE_HANG, pipereader.PIPE_ERROR):
        log_to_send(
            ("[ %s test has TIMED OUT ]" % name) if reader.state == pipereader.PIPE_HANG else
            ("[ PIPE ERROR reading %s test's output ]" % name))
        has_errors = True

    if proc.poll() is None:
        stop = time.time() + 1.0
        time.sleep(0.05)
        while proc.poll() is None and time.time() < stop:
            time.sleep(0.05)
        if proc.returncode is None:
            kill_test(proc)
            proc.wait()

    if proc.returncode != 0:
        if proc.returncode < 0:
            if not (proc.returncode == -signal.SIGTERM and reader.state == pipereader.PIPE_HANG): # do not report signal if it was ours kill result
                signames = SignalNames.get(-proc.returncode, [])
                signames = ' (%s)' % (','.join(signames),) if signames else ''
                log_to_send("[ %s TEST HAVE BEEN INTERRUPTED by signal %s%s ]" % (name.upper(), -proc.returncode, signames))
        else:
            log_to_send("[ %s TESTS' RETURN CODE = %s ]" % (name.upper(), proc.returncode))
        has_errors = True

    if has_errors and collector:
        log_to_send("Test's output:\n%s", "\n".join(collector))


#####################################

def get_boxes_status():
    try:
        data = check_output(VAGR_STAT, stderr=STDOUT, universal_newlines=True, cwd=VAG_DIR, shell=False)
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
        log("ERROR: `%s` call returns %s code. Output:\n%s", ' '.join(VAGR_STAT), e.returncode, e.output)
        return []


def show_boxes():
    "Print out vargant boxes status."
    info = get_boxes_status()
    if not info:
        print "Empty vagrant reply!"
        return
    namelen = max(len(b[0]) for b in info)
    for box in info:
        print "%s  [%s]" % (box[0].ljust(namelen), box[1])

#####################################

# which options are allowed to be used with --nobox
FUNCTEST_ARGS = ('functest', 'timesync', 'httpstress', 'msarch', 'natcon', 'stream')
ARGS_EXCLUSIVE = (
    ('nobox', 'boxes', 'boxoff', 'showboxes'),
) + tuple(('no_functest', opt) for opt in FUNCTEST_ARGS)


def any_functest_arg():
    return any(getattr(Args, opt) for opt in FUNCTEST_ARGS)

def check_args_correct():
    if Args.full_build_log and not Args.stdout:
        print "ERROR: --full-build-log option requires --stdout!\n"
        exit(1)
    for block in ARGS_EXCLUSIVE:
        if sum(1 if getattr(Args, opt, None) else 0 for opt in block) > 1:
            print "Arguments %s are mutual exclusive!" % (args2str(block),)
            exit(1)
    if Args.nobox and not any_functest_arg():
        print "ERROR: --nobox is allowed only with options %s\n" % (args2str(FUNCTEST_ARGS),)
        exit(1)
    if Args.add and (Args.boxes is None):
        print "ERROR: --add is usable only with --boxes"
        exit(1)

def parse_args():
    parser = argparse.ArgumentParser()
    #TODO: add parameters: usage, description

    # Run mode
    # No args -- just build and test current project (could be modified by -p, -t, -u)
    parser.add_argument("-a", "--auto", action="store_true", help="Continuos full autotest mode.")
    parser.add_argument("-t", "--test-only", action='store_true', help="Just run existing tests again (add --noft to skip functests.")
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
        global MVN_THREADS
        MVN_THREADS = Args.threads
    check_debug_mode()
    if Args.auto:
        log("Starting...")


def check_debug_mode():
    global DEBUG
    if DEBUG and Args.prod:
        DEBUG = False
    elif not DEBUG and Args.debug:
        DEBUG = True


def set_paths():
    if not os.path.isdir(PROJECT_ROOT):
        raise EnvironmentError(errno.ENOENT, "The project root directory not found", PROJECT_ROOT)
    if not os.access(PROJECT_ROOT, os.R_OK|os.W_OK|os.X_OK):
        raise IOError(errno.EACCES, "Full access to the project root directory required", PROJECT_ROOT)
    if Env.get('LD_LIBRARY_PATH'):
        Env['LD_LIBRARY_PATH'] += os.pathsep + LIB_PATH
    else:
        Env['LD_LIBRARY_PATH'] = LIB_PATH
    #debug("LD_LIBRARY_PATH=%s",Env['LD_LIBRARY_PATH'])


def set_branches():
    global BRANCHES
    if Args.branch:
        change_branch_list()
    elif not Args.full:
        BRANCHES = ['.']
    if BRANCHES[0] == '.':
        BRANCHES[0] = current_branch_name()
    if Args.full and not Args.branch:
        log("Watched branches: " + ','.join(BRANCHES))


def change_branch_list():
    global BRANCHES
    BRANCHES = Args.branch
    if '.' in BRANCHES and len(BRANCHES) > 1:
        log("WARNING: there is '.' branch in the branch list -- ALL other branches will be skipped!")
        BRANCHES = ['.']


#def get_pom_modules

def get_ut_names():
    """
    Parses unit_tests/pom.xml finding unittests modules names.
    If it fails, returns global TESTS.
    """
    path = os.path.join(PROJECT_ROOT, UT_SUBDIR, "pom.xml")
    #ns = 'http://maven.apache.org/POM/4.0.0'
    try:
        tree = ET.parse(path)
        # extract the default namespace, the root element of pom.xml should be 'project' from this namespace
        m = re.match("(\{[^}]+\}).+", tree.getroot().tag)
        # unfortunately, xml.etree.ElementTree adds namespace to all tags and there is no way to use clear tag names
        pomtests = [el.text.strip() for el in tree.findall('{0}modules/{0}module'.format(m.group(1) if m else ''))]
        if pomtests:
            print "DEBUG: ut list found: %s" % (pomtests,)
            return pomtests
        else:
            print "No <module>s found in %s" % path
            # and go further to the end of the function
    except Exception, e:
        print "Error loading %s: %s" % (path, e)
    print "Use default unittest names: %s" % (TESTS, )
    return TESTS


def show_conf():
    print "(Warning: this function is outdated a bit.)"
    print "Configuration parameters used:"
    print "DEBUG = %s" % DEBUG
    print "PROJECT_ROOT = %s" % PROJECT_ROOT
    print "BRANCHES = %s" % (', '.join(BRANCHES),)
    print "TESTS = %s" % (', '.join(TESTS),)
    print "HG_CHECK_PERIOD = %s milliseconds" % HG_CHECK_PERIOD
    print "UT_PIPE_TIMEOUT = %s" % UT_PIPE_TIMEOUT
    print "FT_PIPE_TIMEOUT = %s" % FT_PIPE_TIMEOUT
    print "BUILD_LOG_LINES = %s" % BUILD_LOG_LINES
    print "MVN_THREADS = %s" % MVN_THREADS


def run_auto_loop():
    "Runs check-build-test sequence for all branches repeatedly."
    while True:
        t = time.time()
        log("Checking...")
        run()
        t = max(MIN_SLEEP, HG_CHECK_PERIOD - (time.time() - t))
        log("Sleeping %s secs...", t)
        wake_time = time.time() + t
        while time.time() < wake_time:
            time.sleep(1)
            check_control_flags()
    log("Finishing...")


def main():
    drop_flag(RESTART_FLAG)
    drop_flag(STOP_FLAG)
    parse_args()
    set_paths()
    set_branches()

    if Args.conf:
        show_conf() # changes done by other options are shown here
        return

    if Args.showboxes:
        show_boxes()
        return

    if DEBUG:
        print "Debug mode ON"

    if Args.boxes is not None:
        start_boxes(Args.boxes, keep=Args.add)
        return

    if Args.boxoff is not None:
        stop_boxes(Args.boxoff, True)
        return

    FailTracker.load()

    if Args.auto:
        run_auto_loop()

    elif not Args.no_functest and any_functest_arg():  # virtual boxes functest only
        ToSend[:] = []
        perform_func_test(get_to_skip(BRANCHES[0]))
        if ToSend:
            email_notify("Debug %s" % (
                "func" if Args.functest else
                "timesync" if Args.timesync else
                "http-stress" if Args.httpstress else
                "multiserver archive" if Args.msarch else
                "streaming" if Args.stream else
                "NAT-connection" if Args.natcon else
                "UNKNOWN!!!"),
            ToSend)

    else:
        run()


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf8')
    main()

# TODO: with -o turn off output lines accumulator, just print 'em
# Check . branch processing in full test
#
