#!/usr/bin/env python
#TODO: ADD THE DESCRIPTION!!!
import sys, os, os.path, time, re
from subprocess import Popen, PIPE, STDOUT, CalledProcessError, check_call, check_output
from collections import deque
import errno
import traceback
import argparse
from smtplib import SMTP
from email import MIMEText
import signal

from testconf import *

SUITMARK = '[' # all messages from a testsuit starts with it, other are tests' internal messages
FAILMARK = '[  FAILED  ]'
STARTMARK = '[ RUN      ]'
BARMARK = '[==========]'
OKMARK = '[       OK ]'

NameRx = re.compile(r'\[[^\]]+\]\s(\S+)')

PIPE_READY = 0
PIPE_EOF = 1
PIPE_HANG = 2

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

class PipeReaderBase(object):
    def __init__(self):
        self.fd = None
        self.buf = ''
        self.state = PIPE_READY

    def register(self, fd):
        if self.fd is not None and self.fd != fd:
            raise RuntimeError("PipeReader: double fd register")
        self.fd = fd
        self.state = PIPE_READY # new fd -- new process, so the reader is ready again

    def unregister(self):
        if self.fd is None:
            raise RuntimeError("PipeReader.unregister: fd was not registered")
        self._unregister()
        self.fd = None

    def _unregister(self):
        raise NotImplementedError()

    def read_ch(self, timeout=0):
        # ONLY two possible results:
        # 1) return the next character
        # 2) return '' and change self.state
        raise NotImplementedError()

    def readline(self, timeout=0):
        if self.state != PIPE_READY:
            return None
        while True:
            ch = self.read_ch(timeout)
            if ch is None or ch == '':
                return self.buf
            if ch == '\n' or ch == '\r': # use all three: \n, \r\n, \r
                if len(self.buf) > 0:
                    debug(self.buf)
                    try:
                        return self.buf
                    finally:
                        self.buf = ''
                else:
                    pass # all empty lines are skipped (so \r\n doesn't produce fake empty line)
            else:
                self.buf += ch


if os.name == 'posix':
    import select
    READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
    READY = select.POLLIN | select.POLLPRI

    #def check_poll_res(res):
    #    return bool(res[0][1] & READY)

    class PipeReader(PipeReaderBase):
        def __init__(self):
            super(PipeReader, self).__init__()
            self.poller = select.poll()

        def register(self, fd):
            super(PipeReader, self).register(fd)
            self.poller.register(fd, READ_ONLY)

        def _unregister(self):
            self.poller.unregister(self.fd)

        def read_ch(self, timeout):
            res = self.poller.poll(timeout)
            if res:
                if res[0][1] & READY:
                    return self.fd.read(1)
                # EOF
                self.state = PIPE_EOF
            else:
                self.state = PIPE_HANG
            return ''

else:
    print "Windoze is temporary unsupported!"
    os.exit(1)
    import msvcrt
    import pywintypes
    import win32pipe

    class PipeReader(object):
        def __init__(self):
            super(PipeReader, self).__init__()

        def register(self, fd):
            raise NotImplementedError()

        def unregister(self, fd):
            raise NotImplementedError()

        def readline(self, timeout=0):
            raise NotImplementedError()

    class WinPoller(object):
        def __init__(self):
            self.fdlist = []

        def register(self, fd, flags=None):
            # flags are ignored, just for compatibility
            self.fdlist.append(fd.fileno() if hasattr(fd, 'fileno') else fd)

        def unregister(self, fd):
            if hasattr(fd, 'fileno'):
                fd = fd.fileno()
            try:
                self.fdlist.remove(fd)
            except ValueError:
                pass

        def poll(self, timeout):
            iready, oready, eready = select.select(self.fdlist, [], [], timeout)
            if eready:
                print "!"
                print "!!!!!! eready: %s !!!!!!" % eready
                print "!"
            return iready

    def check_poll_res(res):
        return bool(res)

ToSend = []
FailedTests = []
Changesets = {}
Env = os.environ.copy()

Args = {}

DEBUG = True


def log_print(s):
    print s


def log(text, *args):
    log_print("[%s] %s" % (time.strftime("%Y:%m:%d %X %Z"), ((text % args) if args else text)))


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


def read_test_output(proc, reader):
    last_suit_line = ''
    has_errors = False
    has_stranges = False
    repeats = 0 # now many times the same 'strange' line repeats
    running_test_name = ''
    complete = False
    to_send_count = 0
    try:
        while reader.state == PIPE_READY:
            line = reader.readline(PIPE_TIMEOUT)
            if not complete and len(line) > 0:
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
        else: # end reading
            check_repeats(repeats)

        if reader.state == PIPE_HANG:
            ToSend.append("[ TEST SUIT HAS TIMED OUT on test %s ]" % running_test_name)
            FailedTests.append(running_test_name)
            has_errors = True

        if proc.poll() is None:
            proc.terminate()
            proc.wait()

        if proc.returncode != 0:
            if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
                ToSend.append("[ Test %s interrupted abnormally ]" % running_test_name)
                FailedTests.append(running_test_name)
            if proc.returncode < 0:
                if not (proc.returncode == -signal.SIGTERM and reader.state == PIPE_HANG): # do not report signal if it was ours proc.terminate()
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
        reader.register(proc.stdout)
        read_test_output(proc, reader)
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


def run_tests(branch):
    log("Running unit tests for branch %s" % branch)
    lines = []
    reader = PipeReader()

    for name in TESTS:
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
            branches = ['.'] if BRANCHES[0] == '.' else filter_branch_names(ready_branches.split(','))
            if BRANCHES[0] != '.':
                debug("Commits are found in branches: %s", branches)
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
        branch_name = check_output(HG_BRANCH, stderr=STDOUT, **SUBPROC_ARGS)
        return branch_name.split("\n")[0]
    except CalledProcessError, e:
        if e.returncode != 1:
            log("ERROR: Failed to find current branch name: `hg branch` call returns %s code. Output:\n%s", e.returncode, e.output)
            raise


def update_repo(branches, bundle_fn):
    log("Pulling branches: %s" % (', '.join(branches)))
    debug("Using bundle file %s", bundle_fn)
    #try:
    check_call(HG_PULL + [bundle_fn], **SUBPROC_ARGS)
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
            stop = time.time() + 15
            while proc.poll() is None and time.time() < stop:
                time.sleep(0.2)
            if proc.returncode is None:
                last_lines.append("*** Maven has hanged in the end!")
                log("Maven has hanged in the end!")
                proc.terminate()
                if proc.poll() is None:
                    time.sleep(0.5)
                    proc.poll()
                debug("proc.terminate() called. RC = %s", proc.returncode)
        if proc.returncode != 0:
            log("Error calling maven: ret.code = %s" % proc.returncode)
            if not Args.full_build_log:
                log("The last %d log lines:" % len(last_lines))
                log_print("".join(last_lines))
                email_build_error(branch, list(last_lines) + ["Maven return code = %s" % proc.returncode])
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
    if branch != '.':
        log("Switch to the banch %s" % branch)
    check_call(HG_PURGE, **SUBPROC_ARGS)
    check_call(HG_UP if branch == '.' else (HG_UP + ['--rev', branch]), **SUBPROC_ARGS)
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
    parser.add_argument("-f", "--full", action="store_true", help="Full test for all configured branches. (Not required with -b)")
    parser.add_argument("--conf", action='store_true', help="Show configuration and exit")
    # change settings
    parser.add_argument("-b", "--branch", action='append', help="Branches to test (as with -f) instead of configured branch list. Multiple times accepted.\n"
                                                                "Use '.' for a current branch (it WILL update to the last commit of the branch, and it will ignore all other -b). ")
    parser.add_argument("-p", "--path", help="Path to the project directory to use instead the default one")
    parser.add_argument("-T", "--threads", type=int, help="Number of threads to be used by maven (for -T mvn argument). Use '-T 0' to override internal default and use maven's default.")
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
    if Args.threads is not None:
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
    if BRANCHES[0] == '.':
        BRANCHES[0] = current_branch_name()

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
