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

log = logging.getLogger(__name__)


class BuildInfo(object):

    def __init__(self, has_failed_builds, has_failed_tests, failed_test_list, offender_email_list, subject_and_html):
        assert isinstance(has_failed_builds, bool), repr(has_failed_builds)
        assert isinstance(has_failed_tests, bool), repr(has_failed_tests)
        assert is_list_inst(failed_test_list, basestring), repr(failed_test_list)
        assert is_list_inst(offender_email_list, basestring), repr(offender_email_list)
        assert isinstance(subject_and_html, basestring), repr(subject_and_html)
        self.has_failed_builds = has_failed_builds
        self.has_failed_tests = has_failed_tests
        self.failed_test_list = failed_test_list
        self.offender_email_list = offender_email_list
        self.subject_and_html = subject_and_html


class EmailSender(object):

    def __init__(self, config):
        self._config = config
        self._renderer = TemplateRenderer(config.services)

    def render_and_send_email(self, smtp_password, project, branch, build_num, test_mode=True):
        build_info = self.render_email(project, branch, build_num, test_mode)
        if test_mode:
            recipient_list = []
        else:
            recipient_list = self.make_recipient_list(build_info)
        recipient_list += self._config.email.ci_admins
        if recipient_list:
            self.send_email(smtp_password, build_info.subject_and_html, recipient_list)
        else:
            log.warning('No recipients in changesets for build %s / %s #%d', project, branch, build_num)
        return build_info

    @db_session
    def render_email(self, project, branch, build_num, test_mode=True):
        loader = BuildInfoLoader(project, branch, build_num)
        build_info = loader.load_build_info()
        offender_email_list = set('{} <{}>'.format(changeset.user, changeset.email) for changeset in build_info.changeset_list)
        subject_and_html = self._renderer.render(
            'build_email.html',
            test_mode=test_mode,
            recipient_list=offender_email_list,
            **build_info._asdict())
        return BuildInfo(
            has_failed_builds=bool(build_info.failed_build_platform_list),
            has_failed_tests=bool(build_info.failed_tests_platform_list),
            failed_test_list=build_info.failed_test_list,
            offender_email_list=list(offender_email_list),
            subject_and_html=subject_and_html,
            )

    def make_recipient_list(self, build_info):

        def test_in_mask_list(test, mask_list):
            return any(self.test_match_mask(test, mask) for mask in mask_list)

        for name, twc in self._config.tests_watchers.items():
            if (build_info.failed_test_list and
                all(test_in_mask_list(test, twc.test_list) for test in build_info.failed_test_list)):
                log.info('All failed tests are in %r watcher list belonging to %r', name, twc.watcher_email)
                return [twc.watcher_email]
        email_list = build_info.offender_email_list
        for name, twc in self._config.tests_watchers.items():
            if any(test_in_mask_list(test, twc.test_list) for test in build_info.failed_test_list):
                log.info('Some failed tests are in %r watcher list belonging to %r', name, twc.watcher_email)
                email_list.append(twc.watcher_email)
        return email_list

    @staticmethod
    def test_match_mask(test_path, test_mask):
        mask = test_mask.split('/')
        path = test_path.split('/')
        if mask[-1] == '*':
            return path[:len(mask) - 1] == mask[:-1]
        else:
            return path == mask

    def send_email(self, smtp_password, subject_and_html, recipient_list):
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
    sender = EmailSender(config)
    build_info = sender.render_email(project, branch, build_num, test_mode=True)
    print 'recipients:'
    print sender.make_recipient_list(build_info)
    print 'subject and html:'
    print build_info.subject_and_html
    if smtp_password and recipient:
        sender.send_email(smtp_password, build_info.subject_and_html, [recipient])

if __name__ == '__main__':
    test_me()
