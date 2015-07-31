#!/usr/bin/env python
#TODO: ADD THE DESCRIPTION!!!
import sys, os, os.path, time, re
import subprocess
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from collections import deque
import errno
import select
import traceback
from smtplib import SMTP
from email import MIMEText

from testconf import *

SUITMARK = '[' # all messages from a testsuit starts with it, other are tests' internal messages
FAILMARK = '[  FAILED  ]'
STARTMARK = '[ RUN      ]'
OKMARK = '[       OK ]'

NameRx = re.compile(r'\[[^\]]+\]\s(\S+)')

READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
READY = select.POLLIN | select.POLLPRI

ToSend = []
Env = os.environ.copy()

DEBUG = 1


def log_print(s):
    print s

def log(text):
    log_print("[%s] %s" % (time.strftime("%Y:%m:%d %X %Z"), text))


def debug(text, *args):
    if DEBUG:
        if args:
            log_print("DEBUG: " + (text % args))
        else:
            log_print("DEBUG: " + text)


def email_send(mailfrom, mailto, msg):
    msg['From'] = mailfrom
    msg['To'] = mailto
    smtp = SMTP('localhost')
    #smtp.set_debuglevel(1)
    smtp.sendmail(mailfrom, mailto, msg.as_string())
    smtp.quit()


def email_notify(lines):
    msg = MIMEText.MIMEText(
        "\n".join(lines) +
        ("\n\n[Finished at: %s]" % time.strftime("%Y.%m.%d %H:%M:%S (%Z)"))
    )
    msg['Subject'] = "Autotest run results"
    email_send(MAIL_FROM, MAIL_TO, msg)


def email_build_error(branch, loglines, crash=False):
    cause = "Error building branch %s" if not crash else ("Branch %s build crashes!" + ("Traceback: "))
    msg = MIMEText.MIMEText(
        ("%s\nThe build log last %d lines are:\n" % (cause, len(loglines))) +
        "\n".join(loglines) + "\n"
    )
    msg['Subject'] = "Autotest scriprt fails to build the branch " + branch
    email_send(MAIL_FROM, MAIL_TO, msg)

def get_name(line):
    m = NameRx.match(line)
    return m.group(1) if m else ''


def check_repeats(repeats):
    if repeats > 1:
        ToSend[-1] += "   [ REPEATS %s TIMES ]" % repeats


def perfom_test(poller, proc):
    line = ''
    last_suit_line = ''
    has_errors = False
    has_stranges = False
    repeats = 0 # now many times the same 'strange' line repeats
    running_test_name = ''
    while True:
        res = poller.poll(PIPE_TIMEOUT)
        if res:
            event = res[0][1]
            if not(event & READY):
                break
            ch = proc.stdout.read(1)
            if ch == '\n':
                if len(line) > 0:
                    if line.startswith(SUITMARK):
                        if line.startswith(FAILMARK):
                            ToSend.append(line) # line[len(FAILMARK):].strip())
                            last_suit_line = ''
                            running_test_name = ''
                            has_errors = True
                        elif line.startswith(OKMARK):
                            if running_test_name == get_name(line): # print it out only if there were any 'strange' lines
                                ToSend.append(line)
                                running_test_name = ''
                        else:
                            last_suit_line = line
                    else: # gother test's messages
                        if last_suit_line != '':
                            ToSend.append(last_suit_line)
                            if last_suit_line.startswith(STARTMARK):
                                running_test_name = get_name(last_suit_line) # remember to print OK test result
                            last_suit_line = ''
                        if ToSend and (line == ToSend[-1]):
                            repeats += 1
                        else:
                            check_repeats(repeats)
                            repeats = 1
                            ToSend.append(line)
                        has_stranges = True
                    line = ''
            else:
                line += ch
        else:
            check_repeats(repeats)
            ToSend.append("[ TEST SUIT HAS TIMED OUT ]")
            has_errors = True
            break
    if proc.poll() is None:
        proc.terminate()

    if proc.returncode:
        check_repeats(repeats)
        ToSend.append("[ TEST SUIT RETURNS CODE %s ]" % proc.returncode)
        has_errors = True

    if has_stranges and not has_errors:
        ToSend.append("[ Tests passed OK, but has some output. ]")



def call_test(testname, poller):
    debug("[ Calling %s tests ]" % testname)
    ToSend.append("[ Calling %s tests ]" % testname)
    old_len = len(ToSend)
    proc = None
    try:
        proc = Popen([os.path.join(BIN_PATH, testname)], bufsize=0, stdout=PIPE, stderr=STDOUT,
                    env=Env, **SUBPROC_ARGS)
        #print "Test is started with PID", proc.pid
        poller.register(proc.stdout, READ_ONLY)
        perfom_test(poller, proc)
    except BaseException, e:
        tstr = traceback.format_exc()
        if isinstance(e, Exception):
            ToSend.append("[[ Tests call error:")
            ToSend.append(tstr)
            ToSend.append("]]")
        else:
            ToSend.append("[[ Tests has been interrupted:")
            ToSend.append(tstr)
            ToSend.append("]]")
            raise
    finally:
        if proc: poller.unregister(proc.stdout)
        if len(ToSend) == old_len:
            debug("No intereating output from these tests")
            del ToSend[-1]
        else:
            ToSend.append('')


def run_tests(branch):
    log("Running unit tests for branch %s" % branch)
    ToSend = []
    poller = select.poll()

    for name in TESTS:
        call_test(name, poller)

    if ToSend:
        debug("Tests output:\n" + "\n".join(ToSend))
        email_notify(ToSend)


def filter_branch_names(branches):
    "Check names for exact eq with list, drop duplicates"
    # The problem is `hg in --branch` takes all branches with names beginning with --branch value. :(
    filtered = []
    for name in branches:
        if name in BRANCHES and not name in filtered:
            filtered.append(name)
            # hope it wont be used for huge BRANCHES list
    return filtered


def check_new_commits(bundle_fn):
    "Check the repository for new commits in the controlled branches"
    log("Check for new commits")
    try:
        ready_branches = subprocess.check_output(HG_IN + ['--bundle', bundle_fn], **SUBPROC_ARGS)
        if ready_branches:
            debug("Commits found in branches: %s", ready_branches)
            branches = filter_branch_names(ready_branches.split(','))
            debug("Filtered branches: %s", branches)
            if branches:
                return branches
    except CalledProcessError, e:
        if e.returncode != 1:
            debug("hg in call returns %s code. Output:\n%s", e.returncode, e.output)
            raise
    log("No new commits found for controlled branches.")
    return []


def update_repo(branches, bundle_fn):
    log("Pulling branches %s" % (', '.join(branches)))
    debug("Using bundle file %s", bundle_fn)
    #try:
    subprocess.check_call(HG_PULL + [bundle_fn], **SUBPROC_ARGS)
    #except CalledProcessError, e:


def call_maven_build(branch, unit_tests=False):
    last_lines = deque(maxlen=BUILD_LOG_LINES)
    log("Build netoptix_vms...")
    kwargs = SUBPROC_ARGS
    try:
        if unit_tests:
            kwargs = kwargs.copy()
            kwargs["cwd"] = os.path.join(kwargs["cwd"], UT_SUBDIR)
            branch += ' unit tests'
        log("Build branch %s..." % branch)
        proc = Popen([MVN, "package"], bufsize=50000, stdout=PIPE, stderr=STDOUT, **kwargs)
        for line in proc.stdout:
            last_lines.append(line)
            print ":: " + line,
            #if proc.poll() is not None:
            #    break
        if proc.poll() is None:
            debug("Maven call has stoped print lines but isn't terminated yet")
            proc.terminate()
        if proc.returncode != 0:
            log("Error calling maven")
            log("The last %d log lines:" % len(last_lines))
            log_print("".join(last_lines))
            email_build_error(branch, last_lines)
            return False
    except CalledProcessError:
        tb = traceback.format_exc()
        log("maven call has failed: %s" % tb)
        log("The last %d log lines:" % len(last_lines))
        log_print("".join(last_lines))
        email_build_error(branch, last_lines, crash=tb)
        return False
    return True


def prepare_branch(branch):
    log("Switch to the banch %s" % branch)
    subprocess.check_call(HG_PURGE, **SUBPROC_ARGS)
    subprocess.check_call(HG_UP + [branch], **SUBPROC_ARGS)
    return call_maven_build(branch) and call_maven_build(branch, unit_tests=True)


def perform_check():
    "Check for repository updates, get'em, build and test"
    bundle_fn = os.path.join(TEMP, "in.hg")
    branches = check_new_commits(bundle_fn)
    if branches:
        update_repo(branches, bundle_fn)
        for branch in branches:
            if prepare_branch(branch):
                run_tests(branch)



def run():
    log("Starting...")
#    start_cwd = os.getcwd()
#    if TEMP == '':
#        global TEMP
#        TEMP = start_cwd
#    if old_cwd != PROJECT_ROOT:
#        os.chdir(PROJECT_ROOT)
 #       log("Switched to the project directory %s" % PROJECT_ROOT)
    if not os.path.isdir(PROJECT_ROOT):
        raise EnvironmentError(errno.ENOENT, "The project root directory not found", PROJECT_ROOT)
    if not os.access(PROJECT_ROOT, os.R_OK|os.W_OK|os.X_OK):
        raise IOError(errno.EACCES, "Full access to the project root directory required", PROJECT_ROOT)
    log("Watched branches: " + ','.join(BRANCHES))

    if Env.get('LD_LIBRARY_PATH'):
        Env['LD_LIBRARY_PATH'] += os.pathsep + LIB_PATH
    else:
        Env['LD_LIBRARY_PATH'] = LIB_PATH

    while True:
        t = time.time()
        try:
            perform_check()
        except Exception:
            traceback.print_exc()
        time.sleep(max(MIN_SLEEP, HG_CHECK_PERIOD - (time.time() - t)))
    log("Finishing...")


if __name__ == '__main__':
    run()