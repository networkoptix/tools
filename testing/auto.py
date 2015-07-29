#!/usr/bin/env python
#TODO: ADD THE DESCRIPTION!!!
import sys, os, os.path, time, re
from subprocess import Popen, PIPE, STDOUT
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


def log(text):
    print "[%s] %s" % (time.strftime("%Y:%m:%d %X %Z"), text)

def email_notify(lines):
    msg = MIMEText.MIMEText(
        "\n".join(lines) +
        ("\n\n[Finished at: %s]" % time.strftime("%Y.%m.%d %H:%M:%S (%Z)"))
    )
    msg['Subject'] = "Autotest run results"
    msg['From'] = MAIL_FROM
    msg['To'] = MAIL_TO
    smtp = SMTP('localhost')
    #smtp.set_debuglevel(1)
    smtp.sendmail(MAIL_FROM, MAIL_TO, msg.as_string())
    smtp.quit()


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
    ToSend.append("[ Calling %s tests ]" % testname)
    old_len = len(ToSend)
    proc = None
    try:
        proc = Popen([os.path.join(BIN_PATH, testname)], bufsize=0, stdout=PIPE, stderr=STDOUT, cwd=PROJECT_ROOT,
                     env=Env, universal_newlines=True)
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
            del ToSend[-1]
        else:
            ToSend.append('')


def run_tests():
    ToSend = []
    poller = select.poll()

    for name in TESTS:
        call_test(name, poller)

    if ToSend:
        email_notify(ToSend)


def check_new_commits():
    "Check the repository for new commits in the controlled branches"
    log("Check for new commits")
    

def perform_check():
    "Check for repository updates, get'em, build and test"
    run_tests()



def run():
    log("Starting...")
    old_cwd = os.getcwd()
    if old_cwd != PROJECT_ROOT:
        os.chdir(PROJECT_ROOT)
        log("Switched to the project directory %s" % PROJECT_ROOT)
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