#!/usr/bin/env python
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


from testconf import *

__version__ = 1.1

SUITMARK = '[' # all messages from a testsuit starts with it, other are tests' internal messages
FAILMARK = '[  FAILED  ]'
STARTMARK = '[ RUN      ]'
BARMARK = '[==========]'
OKMARK = '[       OK ]'

NameRx = re.compile(r'\[[^\]]+\]\s(\S+)')

PIPE_NONE = 0
PIPE_READY = 1
PIPE_EOF = 2
PIPE_HANG = 3
PIPE_ERROR = 4

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

class PipeReaderBase(object):
    def __init__(self):
        self.fd = None
        self.proc = None
        self.buf = ''
        self.state = PIPE_NONE

    def register(self, proc):
        if self.fd is not None and self.fd != fd:
            raise RuntimeError("PipeReader: double fd register")
        self.proc = proc
        self.buf = ''
        self.fd = proc.stdout
        self.state = PIPE_READY # new fd -- new process, so the reader is ready again

    def unregister(self):
        if self.fd is None:
            raise RuntimeError("PipeReader.unregister: fd was not registered")
        self._unregister()
        self.fd = None
        self.proc = None

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
#        while self.proc.poll() is None:
        while True:
            ch = self.read_ch(timeout)
            if ch is None or ch == '':
                if self.proc.poll() is not None:
                    break
                return self.buf
            if ch == '\n' or ch == '\r': # use all three: \n, \r\n, \r
                if len(self.buf) > 0:
                    #debug('::'+self.buf)
                    try:
                        return self.buf
                    finally:
                        self.buf = ''
                else:
                    pass # all empty lines are skipped (so \r\n doesn't produce fake empty line)
            else:
                self.buf += ch
        self.state = PIPE_EOF
        return self.buf


if os.name == 'posix':
    import select
    READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
    READY = select.POLLIN | select.POLLPRI

    class PipeReader(PipeReaderBase):
        def __init__(self):
            super(PipeReader, self).__init__()
            self.poller = select.poll()

        def register(self, proc):
            super(PipeReader, self).register(proc)
            self.poller.register(self.fd, READ_ONLY)

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
    import msvcrt
    import pywintypes
    import win32pipe

    class PipeReader(PipeReaderBase):

        def register(self, proc):
            super(PipeReader, self).register(proc)
            self.osf = msvcrt.get_osfhandle(self.fd)

        def read_ch(self, timeout):
            endtime = (time.time() + timeout) if timeout > 0 else 0
            while self.proc.poll() is None:
                try:
                    _, avail, _ = win32pipe.PeekNamedPipe(self.osf, 1)
                except pywintypes.error:
                    self.state = PIPE_ERROR
                    return ''
                if avail:
                    return os.read(self.fd, 1)
                if endtime:
                    t = time.time()
                    if endtime > t:
                        time.sleep(min(0.01, endtime- t))
                    else:
                        self.state = PIPE_HANG
                        return ''


    def check_poll_res(res):
        return bool(res)

ToSend = []
FailedTests = []
Changesets = {}
Env = os.environ.copy()

Args = {}


def log_print(s):
    print s


def log(text, *args):
    log_print("[%s] %s" % (time.strftime("%Y:%m:%d %X %Z"), ((text % args) if args else text)))


def log_to_send(text, *args):
    if args:
        text = text % args
    log(text)
    print "L: " + text
    ToSend.append(text)

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
        email_send(MAIL_FROM, MAIL_TO, msg)


def email_build_error(branch, loglines, unit_tests, crash=False, single_project=None):
    bstr = ("%s unit tests" % branch) if unit_tests else branch
    cause = ("Error building branch " + bstr) if not crash else (("Branch %s build crashes!" % bstr) + crash)
    text = (
        format_changesets(branch) + "\n\n" +
        ('' if not single_project else 'Failed build was restarted for the single failed project: %s\n\n' % single_project) +
        ("%s\nThe build log last %d lines are:\n" % (cause, len(loglines))) +
        "".join(loglines) + "\n"
    )
    if Args.stdout:
        print text
    else:
        msg = MIMEText.MIMEText(text)
        msg['Subject'] = "Autotest scriprt fails to build the branch %s on %s platform" % (bstr, get_platform())
        email_send(MAIL_FROM, MAIL_TO, msg)


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
        while reader.state == PIPE_READY:
            line = reader.readline(PIPE_TIMEOUT)
            if not complete and len(line) > 0:
                debug("Line: %s", line.lstrip())
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

        if reader.state in (PIPE_HANG, PIPE_ERROR):
            ToSend.append((
                "[ test suit has TIMED OUT on test %s ]" if reader.state == PIPE_HANG else
                "[ PIPE ERROR reading test suit output on test %s ]") % running_test_name)
            FailedTests.append(running_test_name)
            has_errors = True

        if proc.poll() is None:
            kill_test(proc)
            proc.wait()

        if proc.returncode != 0:
            if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
                ToSend.append("[ Test %s interrupted abnormally ]" % running_test_name)
                FailedTests.append(running_test_name)
            if proc.returncode < 0:
                if not (proc.returncode == -signal.SIGTERM and reader.state == PIPE_HANG): # do not report signal if it was ours kill result
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
        #debug("Calling %s", testpath)
        # sudo is required since some unittest start server
        # also we're to pass LD_LIBRARY_PATH through command line because LD_* env varsn't passed to suid processes
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
    if sudo:
        subcall(['/usr/bin/sudo', 'kill', str(proc.pid)], shell=False)
    else:
        subcall(['kill', str(proc.pid)], shell=False)

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

    if not lines:
        del ToSend[:]
        perform_func_test()
        if ToSend:
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
#        branch_name = check_output(HG_BRANCH, stderr=STDOUT, **SUBPROC_ARGS)
        branch_name = check_output(HG_BRANCH, stderr=None, **SUBPROC_ARGS)
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
    return (project, project_name)


def failed_project_single_build(last_lines, branch, unit_tests):
    project, project_name = get_failed_project(last_lines)
    if project == '':
        last_lines.append("ERROR: Can't figure failed project '%s'", project_name)
        return False
    log("[ Restarting maven to re-build '%s' ]", project_name)
    call_maven_build(branch, unit_tests, no_threads=True, single_project=project, single_name=project_name or project)
    return True


def call_maven_build(branch, unit_tests=False, no_threads=False, single_project=None, single_name=None):
    last_lines = deque(maxlen=BUILD_LOG_LINES)
    log("Build %s (branch %s)...", "unit tests" if unit_tests else "netoptix_vms", branch)
    kwargs = SUBPROC_ARGS.copy()
    cmd = [MVN, "package", "-e"]
    if MVN_THREADS and not no_threads:
        cmd.extend(["-T", "%d" % MVN_THREADS])
    if single_project is not None:
        cmd.extend(['-pl', single_project])
    if unit_tests:
        kwargs['cwd'] = os.path.join(kwargs["cwd"], UT_SUBDIR)
    debug("MVN: %s", cmd); time.sleep(1.5)
    try:
        if Args.full_build_log:
            kwargs.pop('universal_newlines')
            proc = Popen(cmd, **kwargs)
            proc.wait()
        else:
            proc = Popen(cmd, bufsize=MVN_BUFFER, stdout=PIPE, stderr=STDOUT, **kwargs)
            for line in proc.stdout:
                last_lines.append(line)
            check_mvn_exit(proc, last_lines)
        if proc.returncode != 0:
            log("Error calling maven: ret.code = %s" % proc.returncode)
            if not Args.full_build_log:
                log("The last %d log lines:" % len(last_lines))
                log_print("".join(last_lines))
                last_lines = list(last_lines)
                last_lines.append("Maven return code = %s" % proc.returncode)
                if not single_project:
                    if failed_project_single_build(last_lines, branch, unit_tests):
                        return False
                email_build_error(branch, last_lines, unit_tests, single_project=single_name)
            return False
    except CalledProcessError:
        tb = traceback.format_exc()
        log("maven call has failed: %s" % tb)
        if not Args.full_build_log:
            log("The last %d log lines:" % len(last_lines))
            log_print("".join(last_lines))
            email_build_error(branch, last_lines, unit_tests, crash=tb, single_project=single_name)
        return False
    return True


def prepare_branch(branch):
    if branch != '.':
        log("Switch to the banch %s" % branch)
    debug("Call %s", HG_PURGE)
    check_call(HG_PURGE, **SUBPROC_ARGS)
    debug("Call %s", HG_UP if branch == '.' else (HG_UP + ['--rev', branch]))
    check_call(HG_UP if branch == '.' else (HG_UP + ['--rev', branch]), **SUBPROC_ARGS)
    debug("Going to call maven...")
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
                    (Args.build_ut_only or call_maven_build(BRANCHES[0])) and call_maven_build(BRANCHES[0], unit_tests=True)):
                run_tests(BRANCHES[0])
    except Exception:
        traceback.print_exc()

#####################################
# Functional tests block
def get_server_package_name():
    #TODO move all paths into testconf.py !
    curconf_fn = os.path.join(PROJECT_ROOT, 'build_variables/target/current_config')
    av = 'arch='
    arch=''
    with open(curconf_fn) as f:
        for line in f:
            if line.startswith(av):
                arch=line[len(av):].rstrip()
                break

    if arch == '':
        raise FuncTestError("Can't find server package: architecture not found!")


    fn = os.path.join(PROJECT_ROOT, 'debsetup/mediaserver-deb/%s/finalname-server.properties' % arch)
    fv = 'server.finalName='
    debfn = ''
    with open(fn) as f:
        for line in f:
            if line.startswith(fv):
                debfn = line[len(fv):].rstrip() + '.deb'
                break

    if debfn == '':
        raise FuncTestError("Server package .deb file name not found!")

    return os.path.join(PROJECT_ROOT, 'debsetup/mediaserver-deb/%s/deb/%s' % (arch, debfn))


def wait_servers_ready():
    urls = ['http://%s:%s/ec2/getMediaServersEx' % (ip, MEDIASERVER_PORT) for ip in VG_BOXES_IP]
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
                    continue # wait for good response or for global timeout
                try:
                    data = json.loads(jdata)
                except ValueError, e:
                    continue # just ignore wrong answer, wait for correct
                count = 0
                for server in data:
                    if server.get('status', '') == 'Online':
                        count += 1
                if count == len(urls):
                    debug("Ready response from %s", url)
                    not_ready.discard(url)


def perform_func_test():
    if os.name != 'posix':
        print "\nFunctional tests require POSIX-compatible OS. Skipped."
        return
    need_stop = False
    reader = proc = None
    try:
        # 1. Get the .deb file and fix vagrant/bootstrap.sh
        # The same filename used for all versions here:
        # a) To remove (by override) any previous version automatically.
        # b) To use fixed name in the bootstrap.sh script
        shutil.copy(get_server_package_name(), './networkoptix-mediaserver.deb') # put this name into config
        # 2. Start virtual boxes
        log("Removing old vargant boxes..")
        check_call(VAGR_DESTROY, shell=False)
        log("Creating and starting vagrant boxes...")
        need_stop = True
        check_call(VAGR_RUN, shell=False)
        # 3. Wait for all mediaservers become ready (use /ec2/getMediaServers
        wait_servers_ready()
        # 4. Call functest/main.py (what about imoirt it and call internally?)
        if os.path.isfile(".rollback"): # TODO: move to config or import from functest.py
            os.remove(".rollback")
        reader = PipeReader()
        sub_args = {k: v for k, v in SUBPROC_ARGS.iteritems() if k != 'cwd'}
        log("Running functional tests: %s", [sys.executable, "functest.py", "--autorollback"])
        proc = Popen([sys.executable, "functest.py", "--autorollback"], bufsize=0, stdout=PIPE, stderr=STDOUT, env=Env, **sub_args)
        reader.register(proc)
        read_functest_output(proc, reader)
        #import functest
        #functest.DoTests()
    except FuncTestError, e:
        log("Functional test aborted: %s", e.message)
    except BaseException, e:
        tstr = traceback.format_exc()
        print tstr
        log("Exception during functional test run:\n%s", traceback.format_exc())
        if isinstance(e, Exception):
            pass
            #ToSend.append("[[ Tests call error:")
            #ToSend.append(tstr)
            #ToSend.append("]]")
        else:
            s = "[[ Functional tests has been interrupted:\n%s\n]]" % tstr
            #ToSend.append(s)
            log(s)
            raise # it wont be catched and will allow the script to terminate
    finally:
        if reader and proc:
            reader.unregister()
        if need_stop:
            log("Stopping vagrant boxes...")
            check_call(VAGR_STOP, shell=False)

FT_MAIN = 0
FT_MAIN_FAILED = 1
FT_MERGE = 2
FT_MERGE_IN = 3
FT_MERGE_FAILED = 4
FT_SYSNAME = 5
FT_SYSNAME_IN = 6
FT_SYSNAME_FAILED = 7
FT_END = 20

FT_FAIL_MARK = "FAIL:"
FT_FAIL_END_MAIN = "FAILED (failures"
FT_MAIN_END = "Main tests passed OK"
FT_MERGE_MARK = "Server Merge Test:Resource Start"
FT_MERGE_END = "Server Merge Test:Resource End"
FT_SYSNAME_MARK = "SystemName Test Start"
FT_SYSNAME_END = "SystemName test rollback done"
FT_END_MARK = "ALL AUTOMATIC TEST ARE DONE"


def read_functest_output(proc, reader):
    has_errors = False
    to_send_count = 0
    phase = FT_MAIN
    collector = []
    try:
        while reader.state == PIPE_READY:
            line = reader.readline(PIPE_TIMEOUT)
            if len(line) > 0:
                #debug("FTLine: %s", line.lstrip())
                if line.startswith(FT_END_MARK):
                    phase = FT_END
                else:
                    if phase == FT_MAIN:
                        if line.startswith(FT_FAIL_MARK):
                            has_errors = True
                            phase = FT_MAIN_FAILED
                            log_to_send("Functional test failed!")
                            log_to_send(line)
                            pass
                        elif line.startswith(FT_MAIN_END):
                            log("Main functest done.")
                            phase = FT_MERGE
                    elif phase == FT_MAIN_FAILED:
                        log_to_send(line)
                        if line.startswith(FT_FAIL_END_MAIN):
                            phase = FT_END # there won't be more tests

                    elif phase == FT_MERGE:
                        if line.startswith(FT_MERGE_MARK):
                            phase = FT_MERGE_IN
                            collector = [line]
                    elif phase == FT_MERGE_IN:
                        if line.startswith(FT_MERGE_END):
                            if has_errors:
                                log_to_send(line)
                            phase = FT_SYSNAME
                            log("Merge Server test done.")
                        elif has_errors:
                            log_to_send(line)
                        elif line.startswith(FT_FAIL_MARK):
                            has_errors = True
                            log_to_send("Functional test failed on Merge Server test!")
                            for s in collector:
                                log_to_send(s)
                            del collector[:]
                            log_to_send(line)
                            phase = FT_MERGE_FAILED
                        else:
                            collector.append(line)
                    elif phase == FT_MERGE_FAILED:
                        log_to_send(line)
                        if line.startswith(FT_MERGE_END):
                            phase = FT_SYSNAME
                            log("Merge Server test done.")

                    elif phase == FT_SYSNAME:
                        if line.startswith(FT_SYSNAME_MARK):
                            phase = FT_SYSNAME_IN
                            collector = [line]
                    elif phase == FT_SYSNAME_IN:
                        if line.startswith(FT_SYSNAME_END):
                            if has_errors:
                                log_to_send(line)
                            phase = FT_END
                            log("SystemName test done.")
                        elif has_errors:
                            log_to_send(line)
                        elif line.startswith(FT_FAIL_MARK):
                            has_errors = True
                            log_to_send("Functional test failed on SystemName test!")
                            for s in collector:
                                log_to_send(s)
                            log_to_send(line)
                            phase = FT_SYSNAME_FAILED
                        else:
                            collector.append(line)
                    elif phase == FT_SYSNAME_FAILED:
                        log_to_send(line)
                        if line.startswith(FT_SYSNAME_END):
                            phase = FT_END
                            log("SystemName test done.")

        else: # end reading
            pass

        if reader.state in (PIPE_HANG, PIPE_ERROR):
            ToSend.append(
                "[ functional tests has TIMED OUT ]" if reader.state == PIPE_HANG else
                "[ PIPE ERROR reading functional tests output  ]")
            #FailedTests.append(running_test_name)
            has_errors = True

        if proc.poll() is None:
            kill_test(proc)
            proc.wait()

        if proc.returncode != 0:
            #if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
            #    ToSend.append("[ Test %s interrupted abnormally ]" % running_test_name)
            #    FailedTests.append(running_test_name)
            if proc.returncode < 0:
                if not (proc.returncode == -signal.SIGTERM and reader.state == PIPE_HANG): # do not report signal if it was ours kill result
                    signames = SignalNames.get(-proc.returncode, [])
                    signames = ' (%s)' % (','.join(signames),) if signames else ''
                    log_to_send("[ FUNCTIONAL TESTS HAVE BEEN INTERRUPTED by signal %s%s ]" % (-proc.returncode, signames))
            else:
                log_to_send("[ FUNCTIONAL TESTS' RETURN CODE = %s ]" % proc.returncode)
            has_errors = True

    finally:
        pass
        #if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
        #    FailedTests.append(running_test_name)




#####################################

def parse_args():
    parser = argparse.ArgumentParser()
    #TODO: add parameters: usage, description

    # Run mode
    # No args -- just build and test current project (could be modified by -p, -t, -u)
    parser.add_argument("-a", "--auto", action="store_true", help="Continuos full autotest mode.")
    parser.add_argument("-t", "--test-only", action='store_true', help="Just run existing unit tests again.")
    parser.add_argument("-u", "--build-ut-only", action="store_true", help="Build and run unit tests only, don't (re-)build the project itself.")
    parser.add_argument("-g", "--hg-only", action='store_true', help="Only checks if there any new changes to get.")
    parser.add_argument("-f", "--full", action="store_true", help="Full test for all configured branches. (Not required with -b)")
    parser.add_argument("-v", "--virt", action="store_true", help="Create virtual boxes and run functional test on them.")
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
    #debug("LD_LIBRARY_PATH=%s",Env['LD_LIBRARY_PATH'])


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

    global BRANCHES
    if Args.branch:
        change_branch_list()
    elif not Args.full:
        BRANCHES = ['.']
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
    elif Args.virt: # temporary, later becomes a part of the run()
        ToSend[:] = []
        perform_func_test()
        if ToSend:
            email_notify("Debug func tests", ToSend)

    else:
        run()


if __name__ == '__main__':
    main()

# TODO: with -o turn off output lines accumulator, just print 'em
# Check . branch processing in full test
#
