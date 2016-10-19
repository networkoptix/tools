# $Id$
# Artem V. Nikitin
# Email notifications for developers

from smtplib import SMTP
from email.mime.text import MIMEText
import os

SMTP_ADDR = 'email-smtp.us-east-1.amazonaws.com:587'
SMTP_LOGIN = 'AKIAJ6MLW7ZT7WXXXOIA' # service@networkoptix.com
SMTP_PASS = 'AlYDnddPk8mWorQFVogh8sqkQX6Nv01JwxxfMoYJAFeC'
MAIL_FROM = '"Taskbot System" <autotest@networkoptix.com>'

DEBUG_WATCHERS = {
  'Artem Nikitin': 'anikitin@networkoptix.com'}

class EmailNotify:

  def __init__(self):
    self.__smtp__ = SMTP(SMTP_ADDR)
    self.__smtp__.ehlo()
    self.__smtp__.starttls()
    self.__smtp__.login(SMTP_LOGIN, SMTP_PASS)

  def __enter__(self):
    return self
    
  def send( self, to, subject, text):
    msg = MIMEText(text)
    
    msg['Subject'] = subject
    msg['From'] = MAIL_FROM
    msg['To'] = ",".join(map(lambda t: "%s <%s>" % (t[0], t[1]), to.items()))
    # Debug
    # print "TO:  %s\nMSG:  %s" % ("\n  ".join(to), text)
    self.__smtp__.sendmail(MAIL_FROM, to.values(), msg.as_string())
    
  def __exit__(self, exc_type, exc_value, traceback):
    self.__smtp__.quit()


def email_body(report, text):
  return """Dear all!

%s

Use the link for details:
%s

(task #%s)

--
  taskbot""" % (text, report.get_taskbot_link(), report.link_task_id)

def email_commits(cs, reason):
  return """After these changes:

  %s

%s""" % (",\n  ".join(cs), reason)
  

def notify(report, prev_run, subject, reason):
  import HGUtils
  debug = os.environ.get('TASKBOT_DEBUG_MODE', '0') == '1'
  commits = HGUtils.changes(report, prev_run).values()
  commits = reduce(lambda x, y: x + y, commits, [])
  to = report.watchers
  if debug or not to:
    to = DEBUG_WATCHERS
  cs = []
  for c in commits:
    if not debug:
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
