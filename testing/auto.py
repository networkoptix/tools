#!/usr/bin/env python
#TODO: ADD THE DESCRIPTION!!!
import sys, os, os.path, time, re
import subprocess
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from collections import deque
import errno
import select
import traceback
import argparse
from smtplib import SMTP
from email import MIMEText

from testconf import *

SUITMARK = '[' # all messages from a testsuit starts with it, other are tests' internal messages
FAILMARK = '[  FAILED  ]'
STARTMARK = '[ RUN      ]'
BARMARK = '[==========]'
OKMARK = '[       OK ]'

NameRx = re.compile(r'\[[^\]]+\]\s(\S+)')

READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
READY = select.POLLIN | select.POLLPRI

ToSend = []
FailedTests = []
Changesets = {}
Env = os.environ.copy()

Args = {}

DEBUG = True


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
    smtp = SMTP(SMTP_ADDR)
    if SMTP_LOGIN:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_LOGIN, SMTP_PASS)
    #smtp.set_debuglevel(1)
    smtp.sendmail(mailfrom, mailto, msg.as_string())
    smtp.quit()


def format_changesets(branch):
    chs = Changesets.get(branch, [])
    if chs and isinstance(chs[0], dict):
        #for v in chs:
        #    debug("Changeset: %s", v)
        return "Changesets:\n" + "\n".join(
            "\t%s" % v['line'] if 'line' in v else
            "[%(branch)s] %(node)s: %(author)s, %(date)s\n\t%(desc)s" % v
            for v in chs)
    else:
        return "\n".join(chs)

def email_notify(branch, lines):

    msg = MIMEText.MIMEText(
        ("Branch %s unit tests run report.\n\n" % branch) +
        "\n".join(lines) +
        ("\n\n[Finished at: %s]\n" % time.strftime("%Y.%m.%d %H:%M:%S (%Z)")) + "\n" +
        format_changesets(branch) + "\n"
    )
    msg['Subject'] = "Autotest run results"
    email_send(MAIL_FROM, MAIL_TO, msg)


def email_build_error(branch, loglines, crash=False):
    cause = ("Error building branch " + branch) if not crash else (("Branch %s build crashes!" % branch) + crash)
    msg = MIMEText.MIMEText(
        format_changesets(branch) + "\n\n" +
        ("%s\nThe build log last %d lines are:\n" % (cause, len(loglines))) +
        "".join(loglines) + "\n"
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
    complete = False
    to_send_count = 0
    try:
        while True:
            res = poller.poll(PIPE_TIMEOUT)
            if res:
                event = res[0][1]
                if not(event & READY):
                    break
                ch = proc.stdout.read(1)
                if complete:
                    continue
                if ch == '\n':
                    if len(line) > 0:
                        debug(line.rstrip())
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
                                debug("Complete!")
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
                        line = ''
                else:
                    line += ch
            else:
                check_repeats(repeats)
                ToSend.append("[ TEST SUIT HAS TIMED OUT on test %s]" % running_test_name)
                FailedTests.append(running_test_name)
                has_errors = True
                break

        if proc.poll() is None:
            proc.terminate()
            proc.wait()

        if proc.returncode != 0:
            check_repeats(repeats)
            if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
                ToSend.append("[ Test %s interrupted abnormally ]" % running_test_name)
                FailedTests.append(running_test_name)
            ToSend.append("[ TEST SUIT RETURNS CODE %s ]" % proc.returncode)
            has_errors = True

        if has_stranges and not has_errors:
            ToSend.append("[ Tests passed OK, but has some output. ]")

    finally:
        if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
            FailedTests.append(running_test_name)


def call_test(testname, poller):
    debug("[ Calling %s test suit ]" % testname)
    ToSend.append("[ Calling %s test suit ]" % testname)
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
    lines = []
    poller = select.poll()

    for name in TESTS:
        del ToSend[:]
        del FailedTests[:]
        call_test(name, poller)
        if FailedTests:
            debug("Failed tests: %s", FailedTests)
            if lines:
                lines.append('')
            lines.append("Tests, failed in the %s test suit:" % name)
            lines.extend("\t" + name for name in FailedTests)
            lines.append('')
            lines.extend(ToSend)

    if lines:
        debug("Tests output:\n" + "\n".join(lines))
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


def get_changesets(branch, bundle_fn):
    debug("Run: " + (' '.join(HG_REVLIST + ["--branch=%s" % branch, bundle_fn])))
    proc = subprocess.Popen(HG_REVLIST + ["--branch=%s" % branch, bundle_fn], bufsize=1, stdout=PIPE, stderr=STDOUT, **SUBPROC_ARGS)
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
        debug("Run: %s", ' '.join(HG_IN + ['--bundle', bundle_fn]))
        ready_branches = subprocess.check_output(HG_IN + ['--bundle', bundle_fn], **SUBPROC_ARGS)
        if ready_branches:
            branches = filter_branch_names(ready_branches.split(','))
            debug("Commits are found in branches: %s", branches)
            if branches:
                Changesets.clear()
                return [ b for b in branches if get_changesets(b, bundle_fn) ]
    except CalledProcessError, e:
        if e.returncode != 1:
            debug("`hg in` call returns %s code. Output:\n%s", e.returncode, e.output)
            raise
    log("No new commits found for controlled branches.")
    return []


def update_repo(branches, bundle_fn):
    log("Pulling branches: %s" % (', '.join(branches)))
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
            kwargs = SUBPROC_ARGS.copy()
            kwargs['cwd'] = os.path.join(kwargs["cwd"], UT_SUBDIR)
            branch += ' unit tests'
        log("Build branch %s..." % branch)
        proc = Popen([MVN, "package", "-e"], bufsize=50000, stdout=PIPE, stderr=STDOUT, **kwargs)
        for line in proc.stdout:
            last_lines.append(line)
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
        if not Args.check_only:
            update_repo(branches, bundle_fn)
        for branch in branches:
            if (not Args.check_only) and prepare_branch(branch):
                run_tests(branch)
    if os.access(bundle_fn, os.F_OK):
        os.remove(bundle_fn)



def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--warnings", action='store_true', help="Treat warnings as errors")
    parser.add_argument("-t", "--test-only", action='store_true', help="Just run existing unit tests again")
    parser.add_argument("-b", "--build", action='store_true', help="Build all (including unit tests) and run unit tests")
    parser.add_argument("-c", "--check-only", action='store_true', help="Only checks if there any new changes to get")
    parser.add_argument("--debug", action='store_true', help="Run in debug mode")
    parser.add_argument("--prod", action='store_true', help="Run in production mode")
    global Args
    Args = parser.parse_args()
    global DEBUG
    if DEBUG and Args.prod:
        DEBUG = False
    elif not DEBUG and Args.debug:
        DEBUG = True
    if DEBUG:
        print "Debug mode ON"
    log("Starting...")
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
            if Args.test_only:
                run_tests('(test only run)')
                break
            elif Args.build:
                br = "(build and run tests)"
                if call_maven_build(br) and call_maven_build(br, unit_tests=True):
                    run_tests(br)
            else:
                perform_check()
                if Args.check_only:
                    debug("Changesets:\n %s", "\n".join("%s\n%s" % (br, "\n".join("\t%s" % ch for ch in chs)) for br, chs in Changesets.iteritems()))
                    break
        except Exception:
            traceback.print_exc()
        time.sleep(max(MIN_SLEEP, HG_CHECK_PERIOD - (time.time() - t)))
    log("Finishing...")


if __name__ == '__main__':
    run()