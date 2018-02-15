import logging
import os.path
import sys
import smtplib
from email.mime.text import MIMEText

import yaml
from pony.orm import db_session

from junk_shop import models, DbConfig, BuildInfoLoader
from utils import is_list_inst, setup_logging
from config import Config
from template_renderer import TemplateRenderer
from test_watcher_selector import make_email_recipient_list

log = logging.getLogger(__name__)


class EmailSender(object):

    def __init__(self, config):
        self._config = config
        self._renderer = TemplateRenderer(config.services)

    def render_email(self, build_info, recipient_list, test_mode):
        return self._renderer.render(
            'build_email.html',
            test_mode=test_mode,
            recipient_list=recipient_list,
            **build_info._asdict())

    def send_email(self, smtp_password, subject_and_html, recipient_list):
        if not recipient_list:
            log.warning('Empty email recipient list, email will not be sent')
            return
        lines = subject_and_html.splitlines()
        assert lines[1] == '', lines[:2]  # email template must consist of subject and body delimited by empty line
        assert lines[0]  # Subject must not be empty
        subject = lines[0]
        html = '\n'.join(lines[2:])
        message = MIMEText(html, 'html', _charset='utf-8')
        message['Subject'] = subject
        message['From'] = self._config.email.from_address
        message['To'] = ', '.join(recipient_list)
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

    with db_session:
        loader = BuildInfoLoader.from_project_branch_num(project, branch, build_num)
        build_info = loader.load_build_platform_list()

        print 'changeset recipients:'
        print build_info.changeset_email_list
        print 'recipients for tests:'
        print make_email_recipient_list(config.tests_watchers, build_info)

        sender = EmailSender(config)
        print 'subject and html:'
        subject_and_html = sender.render_email(build_info, [recipient], test_mode=True)
        if smtp_password and recipient:
            sender.send_email(smtp_password, subject_and_html, [recipient])

if __name__ == '__main__':
    test_me()
