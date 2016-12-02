# $Id$
# Artem V. Nikitin
# Email notifications for developers

from smtplib import SMTP, SMTPException
from email.mime.text import MIMEText
import os, time

SMTP_ADDR = 'email-smtp.us-east-1.amazonaws.com:587'
SMTP_LOGIN = 'AKIAJ6MLW7ZT7WXXXOIA' # service@networkoptix.com
SMTP_PASS = 'AlYDnddPk8mWorQFVogh8sqkQX6Nv01JwxxfMoYJAFeC'
MAIL_FROM = '"Taskbot System" <autotest@networkoptix.com>'

DEBUG_WATCHERS = {
  'Artem Nikitin': 'anikitin@networkoptix.com'}

class EmailNotify:

  RETRY_COUNT = 3
  RESEND_TIMEOUT = 5 # seconds

  def __init__(self):
    self.__smtp = SMTP(SMTP_ADDR)
    self.__smtp.ehlo()
    self.__smtp.starttls()
    self.__smtp.login(SMTP_LOGIN, SMTP_PASS)

  def __enter__(self):
    return self
    
  def send(self, to, subject, text):
    msg = MIMEText(text)
    
    msg['Subject'] = subject
    msg['From'] = MAIL_FROM
    msg['To'] = ",".join(map(lambda t: '"%s" <%s>' % (t[0], t[1]), to.items()))
    # Debug
    print "TO:  %s\nMSG:  %s" % ("\n  ".join(to), text)
    for i in range(EmailNotify.RETRY_COUNT):
      try:
        self.__smtp.sendmail(MAIL_FROM, to.values(), msg.as_string())
        break
      except SMTPException, x:
        if i == EmailNotify.RETRY_COUNT - 1:
          raise
        print "Can't send email notify: '%s'" % str(x)
        time.sleep(EmailNotify.RESEND_TIMEOUT)
    
  def __exit__(self, exc_type, exc_value, traceback):
    self.__smtp.quit()


def email_body(report, text):
  return """Dear all!

%s


Use the links for details:
  Report page: %s
  Taskbot page: %s

(task #%s)

--
  taskbot""" % (text, report.href(True), report.get_taskbot_link(), report.link_task_id)

def email_commits(cs, reason):
  return """After these changes:

  %s

%s""" % (",\n  ".join(cs), reason)
  

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

  with EmailNotify() as email_notify:
    email_notify.send(
      to, subject, 
      email_body(report, email_commits(cs, reason)))

def emergency_body(report, name, text):
  return """Chief!

  There is an error in the taskbot report '%s'

%s

Use the links for details:
  Taskbot page: %s

(task #%s)

--
  taskbot""" % (name, text, report.get_taskbot_link(), report.link_task_id)

def emergency(report, name, error):
  subject = "[Taskbot] [%s] [%s] internal report error" % \
      (os.environ.get('TASKBOT_BRANCHNAME', ''),
       report.platform.description)
  to = DEBUG_WATCHERS
  with EmailNotify() as email_notify:
    email_notify.send(
      to, subject, emergency_body(report, name, error))
  
  
