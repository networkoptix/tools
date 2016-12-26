# $Id$
# Artem V. Nikitin
# Email notifications for developers

from smtplib import SMTP, SMTPException
from email.mime.text import MIMEText
import os, time, re

SMTP_ADDR = 'email-smtp.us-east-1.amazonaws.com:587'
SMTP_LOGIN = 'AKIAJ6MLW7ZT7WXXXOIA' # service@networkoptix.com
SMTP_PASS = 'AlYDnddPk8mWorQFVogh8sqkQX6Nv01JwxxfMoYJAFeC'
MAIL_FROM = '"Taskbot System" <autotest@networkoptix.com>'

DEBUG_WATCHERS = {
  'Artem Nikitin': 'anikitin@networkoptix.com'}


RETRY_COUNT = 3
RESEND_TIMEOUT = 5 # seconds
# NOTE. This is not full RFC 5322 regexp.
EMAIL_CHECKER=r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

def check_email(email):
  result = bool(re.search(EMAIL_CHECKER, email))
  if not result:
    print "'%s' is not a valie email address" % email
  return result

def send(to, subject, text):
  msg = MIMEText(text, 'plain', 'utf-8')
  msg['Subject'] = subject
  msg['From'] = MAIL_FROM
  to = {k:v for k,v in to.iteritems() if check_email(v)}
  if not to:
    print "'To' list is empty"
    return
  msg['To'] = ",".join(map(lambda t: '"{0}" <{1}>'.format(t[0], t[1]), to.items()))
  # Debug
  print "TO:  {0}\nMSG:  {1}".format(msg['To'], text)
  for i in range(RETRY_COUNT):
    try:
      smtp = SMTP(SMTP_ADDR)
      try:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_LOGIN, SMTP_PASS)
        smtp.sendmail(MAIL_FROM, to.values(), msg.as_string())
        break
      finally:
        smtp.quit()
    except SMTPException, x:
      if i == RETRY_COUNT - 1:
        raise
      print "Can't send email notify: '%s'" % str(x)
      time.sleep(RESEND_TIMEOUT)


def email_body(report, text):
  return """Dear all!

{0}


Use the links for details:
  Report page: {1}
  Taskbot page: {2}

(task #{3})

--
  taskbot""".format(text, report.href(True), report.get_taskbot_link(), report.link_task_id)

def email_commits(cs, reason):
  return """After these changes:

  {0}

{1}""".format(",\n  ".join(cs), reason)
  

def notify(report, prev_run, subject, reason, notify_owner = True):
  import HGUtils
  debug_mode = os.environ.get('TASKBOT_DEBUG_MODE', '0')
  if debug_mode == '2':
    notify_owner = False
  debug = debug_mode == '1'
  commits = HGUtils.changes(report, prev_run).values()
  commits = reduce(lambda x, y: x + y, commits, [])
  to = report.watchers
  if debug or not to:
    to = DEBUG_WATCHERS
  cs = []
  for c in commits:
    if not debug and notify_owner:
      to[c.author] = c.author_email
    cs.append("%-20s %-20s %s" % \
      (c.author, c.repo.name, c.description))

  subject = "[Taskbot] [%s] [%s] %s" % \
      (os.environ.get('TASKBOT_BRANCHNAME', ''),
       report.platform.description, subject)

  send(
    to, subject, 
    email_body(report, email_commits(cs, reason)))

def emergency_body(report, name, text):
  return """Chief!

  There is an error in the taskbot report '{0}'

{1}

Use the links for details:
  Taskbot page: {2}

(task #{3})

--
  taskbot""".format(name, text, report.get_taskbot_link(), report.link_task_id)

def emergency(report, name, error):
  subject = "[Taskbot] [%s] [%s] internal report error" % \
      (os.environ.get('TASKBOT_BRANCHNAME', ''),
       report.platform.description)
  to = DEBUG_WATCHERS
  send(to, subject, emergency_body(report, name, error))
  
  
