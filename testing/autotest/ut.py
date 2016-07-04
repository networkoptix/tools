# -*- coding: utf-8 -*-
""" Unittests executor and analizer.
"""
__author__ = 'Danil Lavrentyuk'
import os.path, re, sys, time
import xml.etree.ElementTree as ET
from subprocess import check_call, PIPE, STDOUT
import shutil
import signal
import traceback

from .logger import debug, log, raw_log, ToSend
from .tools import Process, kill_proc, SignalNames, Build

from . import pipereader

__all__ = []  # avoid import *

main = sys.modules['__main__']
conf = main.conf

if conf.UT_USE_DOCKER:
    from .utdocker import UtContainer
else:
    UtContainer = None


FailedTests = []
SUITMARK =  '[' # all messages from a testsuit starts with it, other are tests' internal messages
STARTMARK = '[ RUN      ]'
FAILMARK =  '[  FAILED  ]'
BARMARK =   '[==========]'
OKMARK =    '[       OK ]'

NameRx = re.compile(r'\[[^\]]+\]\s(\S+)')

def get_name(line):
    m = NameRx.match(line)
    return m.group(1) if m else ''


def _load_names():
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
    return list(conf.TESTS)


def get_list(to_skip):
    existed_ut_names = _load_names()
    if main.Args.single_ut:
        return (main.Args.single_ut,) if main.Args.single_ut in existed_ut_names else ()
    if to_skip:
        return [] if 'all_ut' in to_skip else [test for test in existed_ut_names if test not in to_skip]
    else:
        return existed_ut_names


def check_temp_dir():
    if not os.path.exists(conf.UT_TEMP_DIR):
        os.mkdir(conf.UT_TEMP_DIR, 0750)
        # if it did not exist before, it's really safe
        conf.UT_TEMP_DIR_SAFE = True
        return False
    if not os.path.isdir(conf.UT_TEMP_DIR):
        raise EnvironmentError("ERROR: UT_TEMP_FILE %s isn't a directory!" % conf.UT_TEMP_DIR)
        # will be catched in call_unittest()
    return True


def clear_temp_dir():
    if conf.UT_TEMP_DIR_SAFE:
        if os.name == 'posix':
            check_call([conf.SUDO, conf.RM, '-rf', os.path.join(conf.UT_TEMP_DIR,'*')])
        else:
            for entry in os.listdir(conf.UT_TEMP_DIR):
                epath = os.path.join(conf.UT_TEMP_DIR, entry)
                if os.path.isdir(epath):
                    shutil.rmtree(epath, ignore_errors=True)
                else:
                    os.remove(epath)


def validate_testpath(testpath):
    if not os.access(testpath, os.F_OK):
        ToSend.flush()
        ToSend.append("Testsuite '%s' not found!" % testpath)
        return False
    if not os.access(testpath, os.R_OK|os.X_OK):
        ToSend.flush()
        ToSend.append("Testsuite '%s' isn't accessible!" % testpath)
        return False
    return True


def ut_fail_state_msg(state, suitename, testname):
    if state == pipereader.PIPE_HANG:
        return "[ %s has TIMED OUT (more than %.1f seconds) on test %s ]" % (suitename, conf.UT_PIPE_TIMEOUT/1000, testname)
    elif state == pipereader.PIPE_TOOLONG:
        return "[ %s execution takes more than %s minutes, the testsuite will be terminated ]" % (suitename, conf.UT_TIME_LIMIT/60)
    else:
        return "[ PIPE ERROR reading test suite output on test %s ]" % testname


def read_unittest_output(proc, reader, suitename):
    #last_suit_line = ''
    ToSend.clear_repeats() # now many times the same test's output line has been repeaded
    running_test_name = ''
    complete = False
    start_position = 0
    ut_start_time = time.time()
    control_time = ut_start_time + conf.UT_TIME_LIMIT
    # if a unittest doesn't finish before the control_time, it will be terminated
    ut_time = None
    try:
        while reader.state == pipereader.PIPE_READY:
            if time.time() > control_time:
                reader.state = pipereader.PIPE_TOOLONG
                break
            line = reader.readline(conf.UT_PIPE_TIMEOUT)
            if not complete and len(line) > 0:
                #debug("Line: %s", line.lstrip())
                if line.startswith(SUITMARK):
                    ToSend.check_repeats()
                    #last_suit_line = line
                    if line.startswith(STARTMARK):
                        running_test_name = get_name(line) # remember to print OK test result and for abnormal termination case
                        start_position = ToSend.count()
                        ToSend.flushed = False
                        ToSend.append(line)
                    elif line.startswith(FAILMARK) and not complete:
                        #debug("Appending: %s", line.rstrip())
                        FailedTests.append(get_name(line))
                        ToSend.flush(start_position)
                        ToSend.append(line)
                        running_test_name = ''
                    elif line.startswith(OKMARK):
                        if running_test_name == get_name(line): # print it out only if there were any 'strange' lines
                            ToSend.cutTail(start_position)  # cut off all output if no error
                        else:
                            ToSend.append(line)
                            ToSend.log("WARNING!!! running_test_name != get_name(line): %s; %s", running_test_name, line.rstrip())
                        running_test_name = ''
                    elif line.startswith(BARMARK) and not line[len(BARMARK):].startswith(" Running"):
                        ToSend.append(line)
                        complete = True
                    else:
                        ToSend.append(line)
                else: # gather test's messages
                    #if last_suit_line != '':
                    #    ToSend.append(last_suit_line)
                    #    last_suit_line = ''
                    ToSend.check_last_line(line)
        else: # end reading
            ToSend.check_repeats()

        ut_time = time.time() - ut_start_time

        state_error = reader.state in pipereader.ERROR_STATES
        if state_error:
            ToSend.flush()
            ToSend.append(ut_fail_state_msg(reader.state, suitename, running_test_name))
            FailedTests.append(running_test_name)

        before = time.time()
        proc.limited_wait(conf.TEST_TERMINATION_WAIT)

        if proc.poll() is None:
            if not state_error:
                debug("The unittest %s hasn't finished for %.1f seconds", suitename, conf.TEST_TERMINATION_WAIT)
            kill_proc(proc, sudo=True)
            proc.limited_wait(1)
        else:
            delta = time.time() - before
            if delta >= 0.01:
                debug("The unittest %s finnishing takes %.2f seconds", suitename, delta)

        if proc.returncode != 0:
            ToSend.flush()
            if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
                ToSend.append("[ Test %s of %s suit interrupted abnormally ]", running_test_name, suitename)
                FailedTests.append(running_test_name)
            if proc.returncode < 0:
                if not (proc.returncode == -signal.SIGTERM and reader.state == pipereader.PIPE_HANG): # do not report signal if it was ours kill result
                    signames = SignalNames.get(-proc.returncode, [])
                    signames = ' (%s)' % (','.join(signames),) if signames else ''
                    ToSend.append("[ TEST SUITE %s WAS INTERRUPTED by signal %s%s during test %s]",
                                  suitename, -proc.returncode, signames, running_test_name)
            else:
                ToSend.append("[ %s TEST SUITE'S RETURN CODE = %s ]", suitename, proc.returncode)
            if FailedTests:
                ToSend.append("Failed tests: %s", FailedTests)
            else:
                FailedTests.append('(unknown)')

    finally:
        if ut_time is None:
            ut_time = time.time() - ut_start_time
        if running_test_name and (len(FailedTests) == 0 or FailedTests[-1] != running_test_name):
            debug("Test %s final result not found!", running_test_name)
            FailedTests.append(running_test_name)
        if not FailedTests:
            ToSend.append("[ %s tests passed OK. ]" % suitename)
        debug("%s tests run for %.2f seconds.", suitename, ut_time)


def exec_unittest(testpath, branch, use_shuffle):
    """
    Creates a child process executing the unittest.
    :param testpath: str
    :param branch: str
    :param use_shuffle: bool
    :return: Process
    """
    cmd = [testpath]
    if branch not in conf.UT_BRANCHES_NO_TEMP:
        if not conf.UT_TEMP_DIR:
            ToSend.log("WARNING! UT_TEMP_FILE is not set!")
        else:
            cmd.append('--tmp=' + conf.UT_TEMP_DIR)
            if check_temp_dir():
                clear_temp_dir()
    elif UtContainer:  # in container we pass 'notmp' to runut.sh to not use --tmp
        cmd.append('notmp')
    if use_shuffle:
        cmd.append('--gtest_shuffle')
    if UtContainer:
        cmd = UtContainer.makeCmd(conf.DOCKER_UT_WRAPPER, *cmd)
    elif os.name == 'posix' and (os.path.basename(testpath) in conf.SUDO_REQUIRED):
        # sudo is required since some unittest start server
        # also we're to pass LD_LIBRARY_PATH through command line because LD_* env varsn't passed to suid processes
        cmd = [conf.SUDO, '-E', 'LD_LIBRARY_PATH=%s' % main.Env['LD_LIBRARY_PATH']] + cmd
    if not UtContainer:
        debug("Calling %s with LD_LIBRARY_PATH=%s", os.path.basename(testpath), main.Env['LD_LIBRARY_PATH'])
    debug("Command line: %s", cmd)
    return Process(cmd, bufsize=0, stdout=PIPE, stderr=STDOUT, env=main.Env, **conf.SUBPROC_ARGS)


def call_unittest(suitname, reader, branch):
    ToSend.clear()
    ToSend.log("[ Calling %s test suite ]", suitname)
    old_coount = ToSend.count()
    proc = None
    try:
        if UtContainer:
            testpath = suitname
        else:
            testpath = os.path.join(Build.bin_path, suitname)
            if not validate_testpath(testpath):
                FailedTests.append('(all -- not executed)')
                return
        #debug("Calling %s", testpath)
        proc = exec_unittest(testpath, branch, (branch, suitname) not in conf.NOSHUFFLE)
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


def iterate_unittests(branch, to_skip, result_list, all_fails):
    reader = pipereader.PipeReader()
    output = []
    ut_names = get_list(to_skip)

    if ut_names:
        try:
            if UtContainer:
                UtContainer.init(Build)
            for name in ut_names:
                del FailedTests[:]
                call_unittest(name, reader, branch)  # it clears ToSend on start
                if FailedTests:
                    result_list.append(('ut:'+name, False))
                    failedStr = "\n".join(("Tests, failed in the %s test suite:" % name,
                                           "\n".join("\t" + name for name in FailedTests),
                                          ''))
                    all_fails.append((name, FailedTests[:]))
                    if main.Args.stdout:
                        ToSend.flush()
                        raw_log('')
                        log(failedStr)
                    else:
                        if output:
                            output.append('')
                        output.append(failedStr)
                        output.extend(ToSend.lines)
                else:
                    result_list.append(('ut:'+name, True))
                    debug("OK for the '%s' test suite", name)
        #TODO add some `except`s?
        finally:
            pass
            if UtContainer:
                UtContainer.done()
    else:
        output.append("Warning: No unittests to run! Are the skipped all?")
        ToSend.log(output[-1])
    return output


#def _cp2cont(srcFn, dstFn):
#    cmd = [ conf.DOCKER, 'cp', srcFn, "%s/%s" % (UtContainer.containerId(),
