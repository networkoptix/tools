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
        return "Changesets:\n" + "\n".join(
            "\t%s" % v['line'] if 'line' in v else
            "[%(branch)s] %(node)s: %(author)s, %(date)s\n\t%(desc)s" % v
            for v in chs)
    else:
        return "\n".join(chs)

def email_notify(branch, lines):
    text = (
        ("Branch %s unit tests run report.\n\n" % branch) +
        "\n".join(lines) +
        ("\n\n[Finished at: %s]\n" % time.strftime("%Y.%m.%d %H:%M:%S (%Z)")) + "\n" +
        format_changesets(branch) + "\n"
    )
    if Args.stdout:
        print text
    else:
        msg = MIMEText.MIMEText(text)
        msg['Subject'] = "Autotest run results"
        email_send(MAIL_FROM, MAIL_TO, msg)


def email_build_error(branch, loglines, crash=False):
    cause = ("Error building branch " + branch) if not crash else (("Branch %s build crashes!" % branch) + crash)
    text = (
        format_changesets(branch) + "\n\n" +
        ("%s\nThe build log last %d lines are:\n" % (cause, len(loglines))) +
        "".join(loglines) + "\n"
    )
    if Args.stdout:
        print text
    else:
        msg = MIMEText.MIMEText(text)
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
        testpath = os.path.join(BIN_PATH, testname)
        if not os.access(testpath, os.F_OK):
            FailedTests.append('(all)')
            ToSend.append("Testsuit '%s' not found!" % testpath)
            return
        if not os.access(testpath, os.R_OK|os.X_OK):
            FailedTests.append('(all)')
            ToSend.append("Testsuit '%s' isn't accessible!" % testpath)
            return
        proc = Popen([testpath], bufsize=0, stdout=PIPE, stderr=STDOUT, env=Env, **SUBPROC_ARGS)
        #print "Test is started with PID", proc.pid
        poller.register(proc.stdout, READ_ONLY)
        perfom_test(poller, proc)
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
        if proc: poller.unregister(proc.stdout)
        if len(ToSend) == old_len:
            debug("No interesting output from these tests")
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
        cmd = HG_IN + [ "--branch=%s" % b for b in BRANCHES ] + ['--bundle', bundle_fn]
        debug("Run: %s", ' '.join(cmd))
        ready_branches = subprocess.check_output(cmd, **SUBPROC_ARGS)
        if ready_branches:
            branches = ['.'] if BRANCHES[0] == '.' else filter_branch_names(ready_branches.split(','))
            if BRANCHES[0] != '.':
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
    line = "Build unit tests" if unit_tests else "Build netoptix_vms"
    if branch != '.':
        line += " (branch %s)" % branch
    log("%s..." % line)
    kwargs = SUBPROC_ARGS.copy()
    cmd = [MVN, "package", "-e"]
    if MVN_THREADS:
        cmd.extend(["-T", "%d" % MVN_THREADS])
    if unit_tests:
        kwargs['cwd'] = os.path.join(kwargs["cwd"], UT_SUBDIR)
        branch += ' unit tests'
    #debug("MVN: %s", cmd)
    time.sleep(1)
    try:
        if Args.full_build_log:
            kwargs.pop('universal_newlines')
            proc = Popen(cmd, **kwargs)
            proc.wait()
        else:
            proc = Popen(cmd, bufsize=50000, stdout=PIPE, stderr=STDOUT, **kwargs)
            for line in proc.stdout:
                last_lines.append(line)
            if proc.poll() is None:
                debug("Maven call has stoped print lines but isn't terminated yet")
                proc.terminate()
        if proc.returncode != 0:
            log("Error calling maven: ret.code = %s" % proc.returncode)
            if not Args.full_build_log:
                log("The last %d log lines:" % len(last_lines))
                log_print("".join(last_lines))
                email_build_error(branch, last_lines)
            return False
    except CalledProcessError:
        tb = traceback.format_exc()
        log("maven call has failed: %s" % tb)
        if not Args.full_build_log:
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
    if branches and not Args.hg_only:
        update_repo(branches, bundle_fn)
        for branch in branches:
            if prepare_branch(branch):
                run_tests(branch)
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
                    (Args.build_ut_only or call_maven_build('.')) and call_maven_build('.', unit_tests=True)):
                run_tests('.')
    except Exception:
        traceback.print_exc()


def parse_args():
    parser = argparse.ArgumentParser()
    #TODO: add parameters:
    # usage
    # description
    #----
    # Run mode
    # No args -- just build and test current project
    # (could be modified by -p, -t, -u)
    parser.add_argument("-t", "--test-only", action='store_true', help="Just run existing unit tests again")
    parser.add_argument("-u", "--build-ut-only", action="store_true", help="Build and run unit tests only, don't (re-)build the project itself.")
    parser.add_argument("-a", "--auto", action="store_true", help="Continuos full autotest mode.")
    parser.add_argument("-g", "--hg-only", action='store_true', help="Only checks if there any new changes to get")
    parser.add_argument("-f", "--full", action="store_true", help="Full test for all configuged branches. (Not required with -b)")
    parser.add_argument("--conf", action='store_true', help="Show configuration and exit")
    # change settings
    parser.add_argument("-b", "--branch", action='append', help="Branches to test (as with -f) instead of configured branch list. Use '.' for a current branch. Multiple times accepted.")
    parser.add_argument("-p", "--path", help="Path to the project directory to use instead the default one")
    parser.add_argument("-T", "--threads", type=int, help="Number of threads to be used by maven (for -T mvn argument)")
    # output control
    parser.add_argument("-o", "--stdout", action="store_true", help="Don't send email, print resulting text to stdout.")
    parser.add_argument("-l", "--full-build-log", action="store_true", help="Print full build log, immediate. Use with -o only.")
    parser.add_argument("-w", "--warnings", action='store_true', help="Treat warnings as error, report even if no errors but some strange output from tests")
    parser.add_argument("--debug", action='store_true', help="Run in debug mode (more messages)")
    parser.add_argument("--prod", action='store_true', help="Run in production mode (turn off debug messages)")
    #
    global Args
    Args = parser.parse_args()
    if Args.full_build_log and not Args.stdout:
        print "ERROR: --full-build-log option requires --stdout!"
        exit(1)
    if Args.auto or Args.hg_only or Args.branch:
        Args.full = True # to simplify checks in run()
    if Args.threads:
        global MVN_THREADS
        MVN_THREADS = Args.threads


def check_debug_mode():
    global DEBUG
    if DEBUG and Args.prod:
        DEBUG = False
    elif not DEBUG and Args.debug:
        DEBUG = True
    if DEBUG and not Args.conf:
        print "Debug mode ON"


def set_paths():
    if not os.path.isdir(PROJECT_ROOT):
        raise EnvironmentError(errno.ENOENT, "The project root directory not found", PROJECT_ROOT)
    if not os.access(PROJECT_ROOT, os.R_OK|os.W_OK|os.X_OK):
        raise IOError(errno.EACCES, "Full access to the project root directory required", PROJECT_ROOT)

    if Env.get('LD_LIBRARY_PATH'):
        Env['LD_LIBRARY_PATH'] += os.pathsep + LIB_PATH
    else:
        Env['LD_LIBRARY_PATH'] = LIB_PATH


def change_branch_list():
    global BRANCHES
    BRANCHES = Args.branch
    if '.' in BRANCHES and len(BRANCHES) > 1:
        log("WARNING: there is '.' branch in the branch list -- ALL other branches will be skipped!")
        BRANCHES = ['.']


def show_conf():
    print "Configuration parameters used:"
    print "DEBUG = %s" % DEBUG
    print "PROJECT_ROOT = %s" % PROJECT_ROOT
    print "BRANCHES = %s" % (', '.join(BRANCHES),)
    print "TESTS = %s" % (', '.join(TESTS),)
    print "HG_CHECK_PERIOD = %s milliseconds" % HG_CHECK_PERIOD
    print "PIPE_TIMEOUT = %s" % PIPE_TIMEOUT
    print "BUILD_LOG_LINES = %s" % BUILD_LOG_LINES
    print "MVN_THREADS = %s" % MVN_THREADS


def main():
    parse_args()
    check_debug_mode()
    if Args.auto:
        log("Starting...")

    set_paths()

    if Args.branch:
        change_branch_list()

    if Args.conf:
        show_conf() # changes done by other options are shown here
        exit(0)

    if Args.full:
        log("Watched branches: " + ','.join(BRANCHES))

    if Args.auto:
        while True:
            t = time.time()
            log("Checking...")
            run()
            t = max(MIN_SLEEP, HG_CHECK_PERIOD - (time.time() - t))
            log("Sleeping %s secs...", t)
            time.sleep(t)
        log("Finishing...")
    else:
        run()


if __name__ == '__main__':
    main()

# TODO: with -o turn off output lines accumulator, just print 'em
# Check . branch processing in full test
#