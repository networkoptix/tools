# -*- coding: utf-8 -*-
""" Sending notification emals (or, sometimes, printing to console).
"""
__author__ = 'Danil Lavrentyuk'
import sys, time
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from subprocess import PIPE, STDOUT

from .logger import debug, log, ToSend
from .tools import Process, Build

main = sys.modules['__main__']
conf = main.conf

Changesets = {}

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


def read_changesets(branches, bundle_fn):
    Changesets.clear()
    return [ b for b in branches if get_changesets(b, bundle_fn) ]


def log_changesets():
    log("Changesets:\n %s",
        "\n".join("%s\n%s" % (br, "\n".join("\t%s" % ch for ch in chs)) for br, chs in Changesets.iteritems()))


def _chs_str(changeset):
    try:
        return "[%(branch)s] %(node)s: %(author)s, %(date)s\n\t%(desc)s" % changeset
    except KeyError, e:
        return "WARNING: no %s key in changeset dict: %s!" % (e.args[0], changeset)


def format_changesets(branch):
    chs = Changesets.get(branch, [])
    if chs and isinstance(chs[0], dict):
        return "Changesets:\n" + "\n".join(
            ("\t%s" % v['line']) if 'line' in v else _chs_str(v) for v in chs)
    else:
        return "\n".join(chs)


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


def _time4LogName(tmStruct):
    return time.strftime("%y%m%d-%H%M%S", tmStruct)


def emailTestResult(branch, lines, testName='', fail='', summary=''):
    branchStr = "Branch " + branch
    if testName:
        branchStr  += ", " + testName + " only"
    else:
        branchStr  += " autotests"
    resultStr = (fail + " failed") if fail else 'success'
    parts = [
        "%s run report. Platform %s, arch %s." % (branchStr.capitalize(), Build.platform, Build.arch),
        "Result: " + resultStr,
    ]
    attach = ''
    now = time.gmtime()
    lines.extend(('',"[Finished at: %s]" % time.strftime("%Y.%m.%d %H:%M:%S GMT", now), ''))
    if len(lines) >= conf.MAX_LOG_NO_ATTACH:
        if summary:
            parts.extend(('',summary,''))
        parts.append("See log file (%s lines) attached for details." % len(lines))
        attach = MIMEText("\n".join(lines))
        attach.add_header('Content-Disposition', 'attachment', filename=('test_fail_%s_%s.log' % (
            branch.replace(' ', '_'), _time4LogName(now))))
    else:
        parts.extend(lines)
    if branch:
        parts.append(format_changesets(branch))
    text = '\n'.join(parts)
    if attach:
        msg = MIMEMultipart()
        msg.attach(MIMEText(text))
        msg.attach(attach)
    else:
        msg = MIMEText(text)
    onlyTest = (" (%s only)" % testName) if testName else ''
    msg['Subject'] = "Autotest%s: %s (%s, %s, %s)" % (onlyTest, resultStr, branch, Build.platform, Build.arch)
    email_send(conf.MAIL_FROM, conf.MAIL_TO, conf.BRANCH_CC_TO.get(branch, []), msg)


def emailBuildError(branch, loglines, unit_tests, crash='', single_project=None, dep_error=None):
    bstr = ("%s unit tests" % branch) if unit_tests else branch
    cause = ("Error building branch " + bstr) if not crash else (("Branch %s build crashes!" % bstr) + crash)
    attach = ''
    if single_project:
        special = 'Failed build was restarted for the single failed project: %s\n\n' % single_project
    elif dep_error:
        special = ("DEPENDENCY ERROR DETECTED!\n"
                   "Multithread build has failed on '%s', but singlethreaded has succeeded." % dep_error)
    else:
        special = ''
    msglines = [format_changesets(branch), '', special, '', cause]
    log_iter = (s.rstrip() for s in loglines)  # to be shure with newlines style
    if not ToSend.stdout and len(loglines) > conf.MAX_LOG_NO_ATTACH:  # TODO remove attchament code partial duplidation with emailTestResult!
        msglines.append("See the last %d lines of the build log in the file attached." % len(loglines))
        attach = MIMEText("\n".join(log_iter))
        attach.add_header('Content-Disposition', 'attachment', filename=('build_fail_%s_%s.log' % (
            branch, _time4LogName(time.gmtime()))))
    else:
        msglines.append("The build log last %d lines are:" % len(loglines))
        msglines.extend(log_iter)
        msglines.append('')
    text = '\n'.join(msglines)
    if ToSend.stdout:
        print text
    else:
        if attach:
            msg = MIMEMultipart()
            msg.attach(MIMEText(text))
            msg.attach(attach)
        else:
            msg = MIMEText(text)
        msg['Subject'] = "Autotest: build failed (%s, %s, %s)" % (bstr, Build.platform, Build.arch)
        email_send(conf.MAIL_FROM, conf.MAIL_TO, conf.BRANCH_CC_TO.get(branch, []), msg)
