#!/usr/bin/env python
# -*- coding: utf-8 -*-
#TODO: ADD THE DESCRIPTION!!!
import sys, os, os.path, time, re
from subprocess import PIPE, STDOUT, CalledProcessError, check_call, check_output, list2cmdline
from collections import deque, namedtuple
import errno
import traceback
import argparse
import signal
import shutil
import urllib2
import json

# Always chdir to the scripts directory
rundir = os.path.dirname(sys.argv[0])
if rundir not in ('', '.') and rundir != os.getcwd():
    os.chdir(rundir)

import testconf as conf

if os.name == 'posix':
    import autotest.posix
    autotest.posix.fix_ulimit(conf.ULIMIT_NOFILE_REQUIRED)

import autotest.pipereader as pipereader
import autotest.ut as ut
from autotest.logger import raw_log, log, debug, set_debug, ToSend
from autotest.mailer import emailTestResult, emailBuildError, read_changesets, log_changesets
from autotest.tools import Process, kill_proc, RunTime, SignalNames, Build, get_file_time, \
    real_caps, args2str, boxssh

__version__ = '1.4.0'

def check_conf():
    """ Configuration values sanity check.
    """
    #TODO make more cheks!
    names = set(conf.BOX_NAMES.itervalues())
    if len(names) < len(conf.BOX_NAMES):
        keymap = (p for p in ((name, [k for k, v in conf.BOX_NAMES.iteritems() if v == name]) for name in names)
                  if len(p[1]) > 1)
        raw_log("ERROR: duplicated virtual box name in configuration: %s" % ('; '.join("%s: %s" % (k, ', '.join(v)) for k, v in keymap)))
        sys.exit(3)


class FuncTestError(RuntimeError):
    pass

RESULT = None
Env = os.environ.copy()
Args = {}

#####################################

class FailTracker(object):
    fails = set()

    @classmethod
    def mark_success(cls, branch):
        if branch in cls.fails:
            #debug("Removing failed-test-mark from branch %s", branch)
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
                        raise RuntimeError("Can't start the new copy of process: restart flag hasn't been deleted for %s seconds" % conf.SELF_RESTART_TIMEOUT)
                    time.sleep(0.1)
                log("The old proces goes away.")
                sys.exit(0)
        except Exception:
            log("Failed to restart: %s", traceback.format_exc())
            drop_flag(conf.RESTART_FLAG)


def check_control_flags():
    check_restart()
    if os.path.isfile(conf.STOP_FLAG):
        log("Stop flag found. Exiting...")
        os.remove(conf.STOP_FLAG)
        sys.exit(0)


def drop_flag(flag):
    if os.path.isfile(flag):
        os.remove(flag)


def get_tests_to_skip(branch):
    to_skip = set()
    if (branch in conf.SKIP_TESTS) or conf.SKIP_ALL:
        to_skip = conf.SKIP_TESTS.get(branch, set()) | conf.SKIP_ALL
        log("Configured to skip tests: %s", ', '.join(to_skip))
    return to_skip


def run_tests(branch):
    log("Running unit tests for branch %s", branch)
    to_skip = get_tests_to_skip(branch)
    ut_fails = []
    failsum = ''
    ft_failed = False
    output = []

    def _emailResult(what):
        emailTestResult(branch, output, fail=what, testName=(Args.single_ut or ''), summary=failsum)

    output = ut.iterate_unittests(branch, to_skip, RESULT, ut_fails)
    # all ToSend.lines should be in the output now
    ToSend.clear()
    if ut_fails:
        failsum = "Failed unitests summary:\n" + "\n".join(
                    ("* %s:\n        %s" % (fail[0], ','.join(fail[1])))
                    for fail in ut_fails
                )
        if len(ut_fails) > 1:
            if Args.stdout:
                log(failsum)
            else:
                output.append(failsum)
        if Args.full:
            FailTracker.mark_fail(branch)
        if not Args.stdout:
            _emailResult('unittests')
            failsum = ''
        output = []

    # now run functests
    if not Args.no_functest and (conf.FT_AFTER_FAILED_UT or not ut_fails):
        if not perform_func_test(to_skip):
            RESULT.append(('functests', False))
            ft_failed = True
            if Args.stdout and not ToSend.flushed and not ToSend.empty:
                raw_log("--- post functest log tail flushing ---")
                ToSend.flush()
                raw_log("--- . ---")
            else:
                output.append('')
                output.extend(ToSend.lines)
            if Args.full:
                FailTracker.mark_fail(branch)
            if not Args.stdout:
                _emailResult('functional tests')
        else:
            RESULT.append(('functests', True))

    if not (ut_fails or ft_failed):
        debug("Branch %s -- SUCCESS!", branch)
        if Args.full:
            ToSend.clear()
            FailTracker.mark_success(branch)
            if ToSend:  # it's not empty if mark_success() really removed previous test-fail status.
                if not Args.stdout:
                    debug("Sending successful test notification.")
                    emailTestResult(branch, ToSend.lines)
                ToSend.clear()
        return True

    return False


def filter_branch_names(branches):
    "Check names for exact eq with list, drop duplicates"
    # The problem is `hg in --branch` takes all branches with names beginning with --branch value. :(
    filtered = []
    for name in branches:
        if name in conf.BRANCHES and not name in filtered:
            filtered.append(name)
            # hope it wont be used for huge BRANCHES list
    return filtered


def check_new_commits(bundle_fn):
    "Check the repository for new commits in the controlled branches"
    log("Check for new commits")
    try:
        cmd = conf.HG_IN + [ "--branch=%s" % b for b in conf.BRANCHES ] + ['--bundle', bundle_fn]
        debug("Run: %s", ' '.join(cmd))
        ready_branches = check_output(cmd, stderr=STDOUT, cwd=conf.PROJECT_ROOT, **conf.SUBPROC_ARGS)
        if ready_branches:
            # Specifying the current branch (.) turns off all other
            branches = ['.'] if conf.BRANCHES[0] == '.' else filter_branch_names(ready_branches.split(','))
            if conf.BRANCHES[0] != '.':
                ToSend.log('')  # an empty line separator
                log("Commits are found in branches: %s", branches)
            if branches:
                return read_changesets(branches, bundle_fn)
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
        branch_name = check_output(conf.HG_BRANCH, stderr=None, cwd=conf.PROJECT_ROOT, **conf.SUBPROC_ARGS)
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


def mvn_cmd(cmd, *args):
    return [conf.MVN, cmd, "-Dbuild.configuration=%s" % conf.MVN_BUILD_CONFIG] + list(args)


def call_maven_clean(unit_tests):
    cmd = mvn_cmd("clean")
    kwargs = conf.SUBPROC_ARGS.copy()
    kwargs['cwd'] = conf.PROJECT_ROOT
    if unit_tests:
        kwargs['cwd'] = os.path.join(kwargs["cwd"], conf.UT_SUBDIR)
    try:
        check_output(cmd, stderr=STDOUT, **kwargs)
        return None
    except CalledProcessError as err:
        raw_log(err.output)
        msg = "WARNING: 'mvn clean' call failed with code %s!" % err.returncode
        log(msg)
        return "\n".join((err.output, msg))


def nothreads_rebuild(last_lines, branch, unit_tests):
    project, project_name = get_failed_project(last_lines)
    if not project_name:
        project_name = project
    log("[ Calling mvn clean ]")
    clean_res = call_maven_clean(unit_tests)
    log("[ Restarting maven in single thread mode after fail on '%s']", project_name)
    if call_maven_build(branch, unit_tests,
                        no_threads=True, project_name=project_name, preOutput=clean_res):
        #! Project dependencies  error! Report but go on.
        emailBuildError(branch, last_lines, unit_tests, dep_error=project_name)
        return True
    else:
        # Other errors - already reported
        return False


#def failed_project_single_build(last_lines, branch, unit_tests):
#    project, project_name = get_failed_project(last_lines)
#    if project == '':
#        last_lines.append("ERROR: Can't figure failed project '%s'" % project_name)
#        return False
#    log("[ Restarting maven to re-build '%s' ]", project_name)
#    call_maven_build(branch, unit_tests, no_threads=True, single_project=project, project_name=project_name)
#    return True


def call_maven_build(branch,
        unit_tests=False, no_threads=False, single_project=None, project_name=None, preOutput=''):
    last_lines = deque(maxlen=conf.BUILD_LOG_LINES)
    if preOutput:
        last_lines.extend(preOutput.split("\n"))
    log("Build %s (branch %s)...", "unit tests" if unit_tests else "netoptix_vms", branch)
    kwargs = conf.SUBPROC_ARGS.copy()
    kwargs['cwd'] = conf.PROJECT_ROOT

    if (not conf.MVN_THREADS) or conf.MVN_THREADS == 1:
        no_threads = True
    cmd = mvn_cmd("package", "-e", "-T", "1" if no_threads else str(conf.MVN_THREADS))
    if single_project is not None:
        cmd.extend(['-pl', single_project])
    #cmd.extend(['--projects', 'nx_sdk,nx_storage_sdk,mediaserver_core'])

    if unit_tests:
        kwargs['cwd'] = os.path.join(kwargs["cwd"], conf.UT_SUBDIR)
    debug("MVN: %s", cmd); time.sleep(1.5)

    try:
        retcode = execute_maven(cmd, kwargs, last_lines)
        if not unit_tests:
            Build.load_vars(conf, Env, safe=True)
        if retcode != 0:
            log("Error calling maven: ret.code = %s" % retcode)
            if not Args.full_build_log:
                if single_project or no_threads:
                    log("The last %d log lines:" % len(last_lines))
                raw_log("".join(last_lines))
                last_lines = list(last_lines)
                last_lines.append("Maven return code = %s" % retcode)
                if not single_project:
                    if not no_threads:
                        return nothreads_rebuild(last_lines, branch, unit_tests)
                    #else: -- removed since singlethread build possible would be enough to get the fault cause
                    #    if failed_project_single_build(last_lines, branch, unit_tests):
                    #        # on success it reports from the recursive call call_maven_build(), so we can return here
                    #        return False
                emailBuildError(branch, last_lines, unit_tests, single_project=(project_name if single_project else None))
            return False
    except CalledProcessError:
        tb = traceback.format_exc()
        log("maven call failed: %s" % tb)
        if not Args.full_build_log:
            log("The last %d log lines:" % len(last_lines))
            raw_log("".join(last_lines))
            emailBuildError(branch, last_lines, unit_tests, crash=tb, single_project=(project_name if single_project else None))
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

def prepare_and_build(branch):
    "Prepare the branch for testing, i.e. build the project and unit tests"
    ToSend.log('')  # an empty line separator
    if branch != '.':
        log("Switch to the branch %s" % branch)
    if branch in conf.BUILD_ONLY_BRANCHES:
        debug("The branch %s configured build-only." % branch)
    debug("Call %s", conf.HG_PURGE)
    check_call(conf.HG_PURGE, cwd=conf.PROJECT_ROOT, **conf.SUBPROC_ARGS)
    cmd = conf.HG_UP[:]
    if branch != '.':
        cmd.append(branch)
    debug("Call %s", cmd)
    check_call(cmd, cwd=conf.PROJECT_ROOT, **conf.SUBPROC_ARGS)
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
    check_call(conf.HG_PULL + [bundle_fn], cwd=conf.PROJECT_ROOT, **conf.SUBPROC_ARGS)
    #except CalledProcessError, e:
    #    print e
    #    sys.exit(1)


def build_only_msg(branch):
    log("Branch %s is configured as BUILD-ONLY. Skipping all tests" % branch)


def check_and_build():
    "Check for repository updates, get'em, build and test"
    bundle_fn = os.path.join(conf.TEMP, "in.hg")
    branches = check_new_commits(bundle_fn)
    rc = True
    if branches and not Args.hg_only:
        update_repo(branches, bundle_fn)
        for branch in branches:
            if prepare_and_build(branch):
                if branch in conf.BUILD_ONLY_BRANCHES:
                    build_only_msg(branch)
                    # don't change rc - keep it True if it still is True
                elif Args.build_only:
                    pass
                else:
                    #Build.load_vars(conf, Env) - loaded after build
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
            rc = check_and_build()
            if Args.hg_only:
                log_changesets()
            return rc

        if Args.single_ut:
            log("%s test only run..." % Args.single_ut)
        elif Args.test_only:
            log("Test only run...")

        if not Args.test_only:
            if not build_branch(conf.BRANCHES[0]):
                return False
            if conf.BRANCHES[0] in conf.BUILD_ONLY_BRANCHES:
                build_only_msg(conf.BRANCHES[0])
                return True
        if Build.arch == '':
            Build.load_vars(conf, Env)
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
            #debug("Using new testcamera from %s", src)
            shutil.copy(src, dest)
        #else:
            #debug("Using old testcamera at %s", dest)
        return True

#####################################
# Functional tests block
def updateBoxShhConfig(box):
    out = check_output(conf.VAGR_SSHCONF + [conf.BOX_NAMES[box]],
                       stderr=STDOUT, cwd=conf.VAG_DIR, **conf.SUBPROC_ARGS)
    fname = os.path.join(conf.FT_PATH, 'ssh.' + box + '.conf')
    with open(fname, "wt") as f:
        for line in out.splitlines():
            tokens = line.split()
            if tokens:
                if tokens[0] == 'HostName':
                    line = "  HostName %s" % (conf.BOX_IP[box],)
                elif tokens[0] == 'Port':
                    line = "  Port 22"
                elif tokens[0] == 'LogLevel':
                    line = "  LogLevel ERROR"
            print >>f, line


def start_boxes(boxlist=None, keep = False):
    try:
        # 1. Get the .deb file and testcamera
        check_mediaserver_deb()
        check_testcamera_bin()
        # 2. Start virtual boxes
        if not keep:
            debug("Removing old vargant boxes...")
            check_call(conf.VAGR_DESTROY, shell=False, cwd=conf.VAG_DIR)
        if not boxlist:
            log("Creating and starting vagrant boxes...")
            boxlist = conf.BOX_NAMES.keys()
            vagBoxlist = conf.BOX_NAMES.values()
        else:
            log("Creating and starting vagrant boxes: %s...", ', '.join(boxlist))
            vagBoxlist = [conf.BOX_NAMES[b] for b in boxlist]
        check_call(conf.VAGR_RUN + vagBoxlist, shell=False, cwd=conf.VAG_DIR)
        failed = [b[0] for b in get_boxes_status() if b[0] in boxlist and b[1] != 'running']
        if failed:
            ToSend.log("ERROR: failed to start up the boxes: %s", ', '.join(failed))
            return False
        for box in boxlist:
            updateBoxShhConfig(box)
        # 3. Wait for all mediaservers become ready (use /ec2/getMediaServers
        #to_check = [b for b in boxlist if b in CHECK_BOX_UP] if boxlist else CHECK_BOX_UP
        #wait_servers_ready([BOX_IP[b] for b in to_check])
        for box in (boxlist or conf.BOX_POST_START.iterkeys()):
            if box in conf.BOX_POST_START:
                boxssh(box, ['/vagrant/' + conf.BOX_POST_START[box]], cwd=conf.FT_PATH)
        time.sleep(conf.SLEEP_AFTER_BOX_START)
        return True
    except CalledProcessError as err:
        ToSend.log("Failed to call command %s. Returned code %s. Mesage: '%s'",
                   err.cmd, err.returncode, err.message)
        if err.output:
            ToSend.log("Collected output from the command:\n%s", err.output)
        return False
    except FuncTestError as err:
        ToSend.log("Virtual boxes start up failed: %s", err.message)
        return False
    except BaseException as err:
        ToSend.log("Exception during virtual boxes start up:\n%s", traceback.format_exc())
        if not isinstance(err, Exception):
            raise # it wont be catched and will allow the script to terminate


def stop_boxes(boxes, destroy=False):
    try:
        if not boxes:
            log("Removing vargant boxes...")
        else:
            log("Removing vargant boxes: %s...", boxes)
        boxlist = [conf.BOX_NAMES[b] for b in boxes] if len(boxes) else []
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


# these are only names, don't put paths there
FUNCTEST_CFG_TPL = 'functest.cfg.tpl'
FUNCTEST_CFG_NAME = 'functest-tmp.cfg'
#NATTEST_CFG_NAME = 'nattest-tmp.cfg'

BASE_FUNCTEST_CMD = [sys.executable, "-u", "functest.py", '--config', FUNCTEST_CFG_NAME]
NATCON_ARGS = ["--natcon"]


def mk_functest_cmd(to_skip):
    # http stress test single call isn't processed here
    cmd = BASE_FUNCTEST_CMD[:]
    if Args.mainft:
        cmd.append('--main')
        return cmd, 'mainft'

    for test in ('timesync', 'bstorage', 'msarch', 'stream', 'dbup'):
        if getattr(Args, test, False):
            cmd.append('--' + test)
            return cmd, test

    if Args.natcon:
        cmd.extend(NATCON_ARGS)
        return cmd, "natcon"

    if 'time' in to_skip:
        cmd.append("--skiptime")
    if 'backup' in to_skip:
        cmd.append("--skipbak")
    if 'msarch' in to_skip:
        cmd.append('--skipmsa')
    if "stream" in to_skip:
        cmd.append("--skipstrm")
    return cmd, ''


def _confServerList(*servList):
    return ','.join('%s:%s' % (conf.BOX_IP[box], conf.MEDIASERVER_PORT) for box in servList)


def prepare_functest_cfg(path=""):
    name = FUNCTEST_CFG_NAME
    if path is None or path == "":
        path = conf.FT_PATH
    if path:
        name = os.path.join(path, name)
    args = {
        'serverList' : _confServerList('Box1', 'Box2'),
        'natTestServerList': _confServerList('Box1', 'Behind'),
        'username': conf.MEDIASERVER_USER,
        'password': conf.MEDIASERVER_PASS,
    }
    tpl = FUNCTEST_CFG_TPL
    if path:
        tpl = os.path.join(path, tpl)
    file(name, "w").write(file(tpl).read() % args)


def perform_func_test(to_skip):
    if os.name != 'posix':
        raw_log("\nFunctional tests require POSIX-compatible OS. Skipped.")
        return
    need_stop = False
    reader = proc = None
    success = True
    try:
        prepare_functest_cfg()
        if not Args.nobox:
            start_boxes(['Box1'] if Args.natcon else ['Box1','Box2'])
            need_stop = True
        # 4. Call functest/main.py (ToThink: what about import it and call internally?)
        if os.path.isfile(".rollback"): # TODO: move to config or import from functest.py
            os.remove(".rollback")
        reader = pipereader.PipeReader()
        sub_args = conf.SUBPROC_ARGS.copy()
        sub_args['cwd'] = conf.FT_PATH
        debug("Running functests in %s", sub_args['cwd'])
        unreg = False

        only_test = ''
        if not Args.httpstress:
            unreg = True
            cmd, only_test = mk_functest_cmd(to_skip)
            if only_test != 'natcon':
                debug("Running functional tests: %s", cmd)
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
                    stop_boxes(['Box2'])
                    start_boxes(['Nat','Behind'], keep=True)
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
            boxssh('Box1', ('/vagrant/safestart.sh', 'networkoptix-mediaserver'), cwd=conf.FT_PATH)  #FIXME rewrite using the generic way with ctl.sh
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
    FuncTestDesc('httpstress', "HTTP stress", None, None),
    FuncTestDesc('dbup', "DB Upgrade", None, None),
    FuncTestDesc('natcon', "Connection behind NAT", None, None),
)

#FIXME: combine these two tables

FTDesc = namedtuple('FTDesc', ('args', 'name'))

SingleFuncTests = [
    FTDesc(("--mainft",), "main functests"),
    FTDesc(("--timesync", "--ts"), "time synchronization"),
    FTDesc(("--bstorage", "--bs"), "backup storage"),
    FTDesc(("--httpstress", '--hst'), "HTTP stress"),
    FTDesc(("--msarch",), "multiserver archive"),
    FTDesc(("--natcon",), "connection behind NAT"),
    FTDesc(("--stream",), "streaming"),
    FTDesc(("--dbup",), "database migration on upgrade"),
]


def getFTDesc(test):
    for ft in SingleFuncTests:
        if test == ft.args[0][2:]:
            return ft
    return None


def nameFunctest():
    if Args.functest:
        return "all functests"
    else:
        for ft in SingleFuncTests:
            if getattr(Args, ft.args[0][2:], False):
                return ft.name
        return "UNKNOWN!!!"


#TODO
def perform_func_test_new(to_skip):
    if os.name != 'posix':
        raw_log("\nFunctional tests require POSIX-compatible OS. Skipped.")
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
            for s in self.collector:
                ToSend.log(s)
            ToSend.log(line)
        elif line.startswith("Basic functional tests end"):
            ToSend.log("Basic functional tests done.")
            self.parser = self.parse_merge_start
            self.stage = 'wait for Merge server test'
        else:
            self.collector.append(line)

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
    TS_HEAD = "TimeSyncTest suites: "
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
        ToSend.log("Multiserver archive test %s! See it's log below:",
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
            debug("The last test stage was: '%s'. Last %s lines are:\n%s\n----" %
                  (p.stage, len(last_lines), "\n".join(last_lines)))
        success = False

    if proc.returncode != 0:
        if proc.returncode < 0:
            if not (proc.returncode == -signal.SIGTERM and reader.state == pipereader.PIPE_HANG): # do not report signal if it was ours kill result
                signames = SignalNames.get(-proc.returncode, [])
                signames = ' (%s)' % (','.join(signames),) if signames else ''
                ToSend.log("[ FUNCTIONAL TESTS HAVE BEEN INTERRUPTED by signal %s%s ]" % (-proc.returncode, signames))
        else:
            if proc.returncode == 1 and p.has_errors:
                ToSend.log("[ FUNCTIONAL TESTS' RETURN CODE = %s ]", proc.returncode)
            else:
                ToSend.log("[ FUNCTIONAL TESTS' RETURN CODE = %s ]\n"
                        "The last test stage was: '%s'. Last %s lines are:\n%s\n-----" %
                        (proc.returncode, p.stage, len(last_lines), "\n".join(last_lines)))
        success = False
    return success and not p.has_errors


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
        raw_log("Empty vagrant reply!")
        return
    namelen = max(len(b[0]) for b in info)
    for box in info:
        raw_log("%s  [%s]" % (box[0].ljust(namelen), box[1]))

#####################################

# which options are allowed to be used with --nobox
FUNCTEST_ARGS = ('functest', ) + tuple(ft.args[0].lstrip('-') for ft in SingleFuncTests)
# this list is incomlete, so, not all incompatible with each other args are checked now
ARGS_EXCLUSIVE = (
    ('nobox', 'boxes', 'boxoff', 'showboxes'),
    ('ft_if_ut', 'ft_always'),
    ('list', 'full'),
    ('list', 'auto'),
    ('ftconf', 'boxes', 'boxoff', 'ftprepare'),
) + tuple(('no_functest', opt) for opt in FUNCTEST_ARGS)


def any_functest_arg():
    return any(getattr(Args, opt) for opt in FUNCTEST_ARGS)


def check_debug_mode():
    if conf.DEBUG and Args.prod:
        conf.DEBUG = False
    elif not conf.DEBUG and Args.debug:
        conf.DEBUG = True
    if conf.DEBUG:
        set_debug(True)


def _fixBoxesArg(arg):
    fail = False
    if arg == '':
        return conf.BOX_NAMES.keys()
    else:
        boxes = arg.split(',')
        for i, name in enumerate(boxes):
            if name not in conf.BOX_NAMES:
                for k, v in conf.BOX_NAMES.iteritems():
                    if name == v:
                        boxes[i] = k
                        break
                else:
                    raw_log("ERROR: unknown virtual box name: %s" % name)
                    fail = True
    if fail:
        sys.exit(2)
    return boxes


def check_args_correct():
    if Args.full_build_log and not Args.stdout:
        raw_log("ERROR: --full-build-log option requires --stdout!\n")
        sys.exit(2)
    for block in ARGS_EXCLUSIVE:
        if sum(1 if getattr(Args, opt, None) else 0 for opt in block) > 1:
            raw_log("Arguments %s are mutual exclusive!" % (args2str(block),))
            sys.exit(2)
    if Args.nobox and not any_functest_arg():
        raw_log("ERROR: --nobox is allowed only with options %s\n" % (args2str(FUNCTEST_ARGS),))
        sys.exit(2)
    if Args.add and (Args.boxes is None):
        raw_log("ERROR: --add is usable only with --boxes")
        sys.exit(2)
    elif Args.boxes is not None:
        Args.boxes = _fixBoxesArg(Args.boxes)
    elif Args.boxoff is not None:
        Args.boxoff = _fixBoxesArg(Args.boxoff)


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
    #TODO: move all paths into testconf.py !
    if Build.arch == '':
        Build.load_vars(conf, Env, safe=True)

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

    if Args.ftpath is not None:
        conf.FT_PATH = Args.ftpath
    if conf.FT_PATH is None or conf.FT_PATH == '':
        conf.FT_PATH = os.getcwd()
    if conf.FT_PATH.startswith("$NX/"):
        conf.FT_PATH = os.path.join(conf.PROJECT_ROOT, conf.FT_PATH[4:])

    if not os.path.isdir(conf.PROJECT_ROOT):
        raise EnvironmentError(errno.ENOENT, "The project root directory %s isn't found", conf.PROJECT_ROOT)
    if not os.access(conf.PROJECT_ROOT, os.R_OK|os.W_OK|os.X_OK):
        raise IOError(errno.EACCES, "Full access to the project root directory required", conf.PROJECT_ROOT)
    #debug("Using project root at %s", conf.PROJECT_ROOT)

    conf.BUILD_CONF_PATH = os.path.join(conf.PROJECT_ROOT, conf.BUILD_CONF_SUBPATH)

    if not conf.UT_TEMP_DIR:
        raw_log("FATAL: UT_TEMP_DIR must be configured!")
        sys.exit(3)
    if conf.UT_TEMP_DIR.startswith('/'):
        conf.UT_TEMP_DIR_SAFE = False  # absolut paths are unsafe because directory will be cleared with root privileges
    else:
        if conf.UT_TEMP_DIR.startswith('./') or conf.UT_TEMP_DIR.startswith('.\\'):
            conf.UT_TEMP_DIR = os.path.join(os.getcwd(), conf.UT_TEMP_DIR[2:])
        else:
            conf.UT_TEMP_DIR = os.path.join(conf.PROJECT_ROOT, conf.UT_TEMP_DIR)
    if conf.UT_TEMP_DIR.endswith('$'):
        conf.UT_TEMP_DIR = conf.UT_TEMP_DIR[:-1] + str(os.getpid())
        conf.UT_TEMP_DIR_PID_USED = True
        conf.UT_TEMP_DIR_SAFE = True
    else:
        conf.UT_TEMP_DIR_PID_USED = False
    if os.path.exists(conf.UT_TEMP_DIR) and not os.path.isdir(conf.UT_TEMP_DIR):
        raw_log("FATAL: UT_TEMP_FILE %s exists but isn't a directory!" % conf.UT_TEMP_DIR)
        sys.exit(3)


def addSingleFTArgs(parser):
    for ft in SingleFuncTests:
        parser.add_argument(
            *ft.args, action="store_true", help=("Create virtual boxes and run %s test only." % ft.name)
        )


def parse_args():
    parser = argparse.ArgumentParser()
    #TODO: add parameters: usage, description

    # Run mode
    # No args -- just build and test current project (could be modified by -p, -t, -u)
    parser.add_argument("-a", "--auto", action="store_true", help="Continuos full autotest mode.")
    parser.add_argument("-t", "--test-only", action='store_true', help="Just run existing tests again (add --noft to skip functests.")
    parser.add_argument("--single-ut", help="Run specified unit test only.")
    parser.add_argument("-r", "--rebuild", action='store_true', help="(Re)build even if no new commits found.")
    parser.add_argument("--build-only", "--bo", action="store_true", help="Build only, don't test.")
    parser.add_argument("--build-ut-only", "--uo", action="store_true", help="Build and run unit tests only, don't (re-)build the project itself.")
    parser.add_argument("-g", "--hg-only", action='store_true', help="Only checks if there any new changes to get.")
    parser.add_argument("-f", "--full", action="store_true", help="Full test for all configured branches. (Not required with -b)")
    parser.add_argument("--functest", "--ft", action="store_true", help="Create virtual boxes and run functional test on them.")
    parser.add_argument("--no-functest", "--noft", action="store_true", help="Only build the project and run unittests.")
    parser.add_argument("--ft-if-ut", action="store_true", help="Run functests only if no fails in unitests.")
    parser.add_argument("--ft-always", action="store_true", help="Run functests even if there are any fails ib unitests.")

    addSingleFTArgs(parser)

    parser.add_argument("--nobox", "--nb", action="store_true", help="Do not create and destroy virtual boxes. (For the development and debugging.)")
    parser.add_argument("--conf", action='store_true', help="Show configuration and exit.")
    parser.add_argument("-l", "--list", action='store_true', help="List all unit- and functional tests for the branch. Don't run any.")
    # change settings
    parser.add_argument("-b", "--branch", action='append', help="Branches to test (as with -f) instead of configured branch list. Multiple times accepted.\n"
                                                                "Use '.' for a current branch (it WILL update to the last commit of the branch, and it will ignore all other -b). ")
    parser.add_argument("-p", "--path", help="Path to the project directory to use instead of the default one")
    parser.add_argument('--ftpath', help="Path to the directory with the functional tests scripts")
    parser.add_argument("-T", "--threads", type=int, help="The number of threads to be used by maven (for -T mvn argument). Use '-T 0' to override configured default and use maven's default.")
    # output control
    parser.add_argument("-o", "--stdout", action="store_true", help="Don't send email, print resulting text to stdout.")
    parser.add_argument("--full-build-log", "--fbl", action="store_true", help="Print full build log, immediate. Use with -o only.")
    parser.add_argument("-w", "--warnings", action='store_true', help="Treat warnings as error, report even if no errors but some strange output from tests")
    parser.add_argument("--debug", action='store_true', help="Run in debug mode (more messages)")
    parser.add_argument("--prod", action='store_true', help="Run in production mode (turn off debug messages)")
    # utillity actions
    parser.add_argument("--boxes", "--box", help="Start virtual boxes and wait the mediaserver comes up.", nargs='?', const="")
    parser.add_argument('--add', action='store_true', help='Start new boxes without closing existing boxes')
    parser.add_argument("--boxoff", "--b0", help="Stop virtual boxes and wait the mediaserver comes up.", nargs='?', const="")
    parser.add_argument("--showboxes", '--sb', action="store_true", help="Check and show vagrant boxes states")
    parser.add_argument('--utcont', action="store_true", help="Only creates unittest container and displays the sample command line.")
    parser.add_argument('--ftconf', help="Only creates configs for functest.py and updates boxes.rb", nargs='?', const="")
    parser.add_argument('--ftprepare', action="store_true", help="Combine --box (for all boxes) and --ftconf")

    global Args
    Args = parser.parse_args()
    if Args.stdout:
        ToSend.stdout = True
    check_args_correct()
    if Args.auto or Args.hg_only or Args.branch:
        Args.full = True # to simplify checks in run()
    if Args.ft_if_ut:
        conf.FT_AFTER_FAILED_UT = False
    elif Args.ft_always:
        conf.FT_AFTER_FAILED_UT = True
    if Args.threads is not None:
        conf.MVN_THREADS = Args.threads
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
    dest = os.path.join(conf.VAG_DIR, conf.BOXES_NAMES_FILE)
    rbTime = get_file_time(dest)
    confTime = max(
        get_file_time(conf.__file__),
        get_file_time(conf.testconf_local.__file__) if hasattr(conf, 'testconf_local') else 0
    )
    if rbTime < confTime:
        if os.path.exists(dest):
            os.rename(dest, dest + '.bak')
        with open(dest, "wt") as out:
            print >>out, """# -*- mode: ruby -*-
# vi: set ft=ruby :
# AUTOGENERATED FILE, DON'T MODIFY!
# Change the BOX_NAMES dict in the testconf.py or, better, testconf_local.py instead
module Boxes"""
            for name, value in conf.BOX_NAMES.iteritems():
                print >>out, '    %s = "%s"' % (name, value)
            if hasattr(conf, "UT_BOX_NAME"):
                print >>out, '    %s = "%s"' % (conf.UT_BOX_VAR, conf.UT_BOX_NAME)
            print >>out, "end"
            print >>out, "module IPs"
            for name, value in conf.BOX_IP.iteritems():
                print >>out, '    %s = "%s"' % (name, value)
            if hasattr(conf, "UT_BOX_IP"):
                print >>out, '    %s = "%s"' % (conf.UT_BOX_VAR, conf.UT_BOX_IP)
            print >>out, "end"
            print >>out, "# Created at %s" % (time.asctime())
    dest_ut = os.path.join(conf.UT_VAG_DIR, conf.BOXES_NAMES_FILE)
    if get_file_time(dest_ut) < get_file_time(dest):
        shutil.copy(dest, dest_ut)


def run_auto_loop():
    "Runs check-build-test sequence for all branches repeatedly."
    while True:
        t = time.time()
        log("Checking...")
        run()
        # restore some values
        Build.clear()
        global Env
        Env = os.environ.copy()
        #
        t = max(conf.MIN_SLEEP, conf.HG_CHECK_PERIOD - (time.time() - t))
        log("Sleeping %s secs...", t)
        wake_time = time.time() + t
        while time.time() < wake_time:
            time.sleep(1)
            check_control_flags()
    log("Finishing...")


def printTestList():
    print "Unittests:"
    for name in ut.get_list(get_tests_to_skip(conf.BRANCHES[0])):
        print '\t' + name
    print "Functional tests:"
    maxlen = max(len(ft.args[0]) for ft in SingleFuncTests)
    for ft in SingleFuncTests:
        print "\t%s   %s" % (ft.args[0].ljust(maxlen), ft.name)


def main():
    parse_args()
    set_paths()
    set_branches()

    if Args.conf:
        show_conf() # changes done by other options are shown here
        return True

    if Args.list:
        printTestList()
        return True

    updateBoxesNames()

    if Args.utcont:
        #FIXME!!! cover vagrant case too!
        debug("Only creating a docker container for unittests")
        UtContainer = ut.UtContainer
        Build.load_vars(conf, Env)
        UtContainer.init(Build)
        print "Use this command to run unittests:"
        print list2cmdline(UtContainer.makeCmd(UtContainer.getWrapper(), 'YOUR', 'TEST', 'COMMAND'))
        return True

    if Args.ftconf is not None:
        if Args.ftconf:
            debug("Only creating configs for functest.py at %s", Args.ftconf)
        else:
            debug("Only creating configs for functest.py")
        prepare_functest_cfg(path=Args.ftconf)
        return True

    if Args.showboxes:
        show_boxes()
        return True

    if Args.boxes is not None:
        return start_boxes(Args.boxes, keep=Args.add)

    if Args.boxoff is not None:
        stop_boxes(Args.boxoff, destroy=True)
        return True

    if Args.ftprepare:
        prepare_functest_cfg()
        return start_boxes()

    global RESULT
    RESULT = []
    drop_flag(conf.RESTART_FLAG)
    drop_flag(conf.STOP_FLAG)

    if Args.auto:
        log("Starting...")
    else:
        RunTime.go()

    FailTracker.load()

    if Args.auto:
        run_auto_loop()
        return True

    if Args.single_ut:
        Args.no_functest = True
        Args.test_only = True

    if (not Args.no_functest) and any_functest_arg():  # virtual boxes functest only
        ToSend.clear()
        if not perform_func_test(get_tests_to_skip(conf.BRANCHES[0])):
            print "*** Some of FUCTESTS failed! ***"
            if ToSend.count() and not Args.stdout:
                emailTestResult(conf.BRANCHES[0], ToSend.lines, testName=nameFunctest())
            return False
        return True

    else:
        return run()


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf8')
    check_conf()
    try:
        if not main():
            debug("Something isn't OK, returning code 1")
            debug("Results: %s", RESULT)
            sys.exit(1)
        elif RESULT is not None:
            debug("Results: %s", RESULT)
    finally:
        if conf.UT_TEMP_DIR_PID_USED:
            if os.name == 'posix':
                check_call([conf.SUDO, conf.RM, '-rf', conf.UT_TEMP_DIR])
            else:
                shutil.rmtree(conf.UT_TEMP_DIR, ignore_errors=True)
        else:
            ut.clear_temp_dir()
        RunTime.report()

# TODO: with -o turn off output lines accumulator, just print 'em
# Check . branch processing in full test
#
