import logging
import os.path
import sys
import smtplib
from email.mime.text import MIMEText

import yaml
from pony.orm import db_session

from junk_shop import models, DbConfig, BuildInfoLoader
from utils import setup_logging
from config import Config
from template_renderer import TemplateRenderer

log = logging.getLogger(__name__)


class EmailSender(object):

    def __init__(self, config):
        self._config = config
        self._renderer = TemplateRenderer(config.services)

    def render_and_send_email(self, smtp_password, project, branch, build_num, test_mode=True):
        offender_list, subject_and_html = self.render_email(project, branch, build_num, test_mode)
        if test_mode:
            recipient_list = self._config.email.ci_admins
        else:
            recipient_list = offender_list + self._config.email.ci_admins
        if recipient_list:
            self.send_email(smtp_password, subject_and_html, recipient_list)
        else:
            log.warning('No recipients in changesets for build %s / %s #%d', project, branch, build_num)

    @db_session
    def render_email(self, project, branch, build_num, test_mode=True):
        loader = BuildInfoLoader(project, branch, build_num)
        build_info = loader.load_build_info()
        offender_list = set('{} <{}>'.format(changeset.user, changeset.email) for changeset in build_info.changeset_list)
        subject_and_html = self._renderer.render(
            'build_email.html',
            test_mode=test_mode,
            recipient_list=offender_list,
            **build_info._asdict())
        return (list(offender_list), subject_and_html)

    def send_email(self, smtp_password, subject_and_html, recipient_list):
        lines = subject_and_html.splitlines()
        assert lines[1] == '', lines[:2]  # email template must consist of subject and body delimited by empty line
        assert lines[0]  # Subject must not be empty
        subject = lines[0]
        html = '\n'.join(lines[2:])
        message = MIMEText(html, 'html', _charset='utf-8')
        message['Subject'] = subject
        message['From'] = self._config.email.from_address
        message['To'] = ' '.join(recipient_list)
        log.info('Sending email to %r; Subject: %s', recipient_list, subject)
        server = smtplib.SMTP(self._config.email.smtp.host)
        try:
            server.ehlo()
            server.starttls()
            server.login(self._config.email.smtp.user, smtp_password)
            server.sendmail(self._config.email.from_address, recipient_list, message.as_string())
        finally:
            server.quit()


def test_me():
    setup_logging(logging.DEBUG)
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    config = Config.from_dict(yaml.load(open(config_path)))
    db_config = DbConfig.from_string(sys.argv[1])
    db_config.bind(models.db)
    smtp_password = sys.argv[2]
    recipient = sys.argv[3]
    project = sys.argv[4]
    branch = sys.argv[5]
    build_num = int(sys.argv[6])
    sender = EmailSender(config)
    offender_list, subject_and_html = sender.render_email(project, branch, build_num, test_mode=True)
    print subject_and_html
    if smtp_password and recipient:
        sender.send_email(smtp_password, subject_and_html, [recipient])

if __name__ == '__main__':
    test_me()
