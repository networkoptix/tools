import logging
import os.path
import datetime
import yaml

from utils import setup_logging, is_list_inst, is_dict_inst, str_to_timedelta, timedelta_to_str

log = logging.getLogger(__name__)


class PlatformConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            build_node=data['build_node'],
            )

    def __init__(self, build_node):
        assert isinstance(build_node, basestring), repr(build_node)
        self.build_node = build_node

    def to_dict(self):
        return dict(
            build_node=self.build_node,
            )

    def report(self):
        log.info('\t\t\t' 'build_node: %r', self.build_node)


class JunkShopConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            db_host=data['db_host'],
            )

    def __init__(self, db_host):
        assert isinstance(db_host, basestring), repr(db_host)
        self.db_host = db_host

    def to_dict(self):
        return dict(
            db_host=self.db_host,
            )

    def report(self):
        log.info('\t' 'junk_shop:')
        log.info('\t\t' 'db_host: %r:', self.db_host)


class ServicesConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            junk_shop_url=data['junk_shop_url'].rstrip('/'),
            jira_url=data['jira_url'],
            scm_browser_url_format=data['scm_browser_url_format'],
            )

    def __init__(self, junk_shop_url, jira_url, scm_browser_url_format):
        assert isinstance(junk_shop_url, basestring), repr(junk_shop_url)
        assert isinstance(jira_url, basestring), repr(jira_url)
        assert isinstance(scm_browser_url_format, basestring), repr(scm_browser_url_format)
        self.junk_shop_url = junk_shop_url
        self.jira_url = jira_url
        self.scm_browser_url_format = scm_browser_url_format

    def to_dict(self):
        return dict(
            junk_shop_url=self.junk_shop_url,
            jira_url=self.jira_url,
            scm_browser_url_format=self.scm_browser_url_format,
            )

    def report(self):
        log.info('\t' 'services:')
        log.info('\t\t' 'junk_shop_url: %r:', self.junk_shop_url)
        log.info('\t\t' 'jira_url: %r:', self.jira_url)
        log.info('\t\t' 'scm_browser_url_format: %r:', self.scm_browser_url_format)


class EmailSmtpConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            host=data['host'],
            user=data['user'],
            )

    def __init__(self, host, user):
        assert isinstance(host, basestring), repr(host)
        assert isinstance(user, basestring), repr(user)
        self.host = host
        self.user = user

    def to_dict(self):
        return dict(
            host=self.host,
            user=self.user,
            )

    def report(self):
        log.info('\t\t' 'smtp:')
        log.info('\t\t\t' 'host: %r:', self.host)
        log.info('\t\t\t' 'user: %r:', self.user)


class EmailConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            smtp=EmailSmtpConfig.from_dict(data['smtp']),
            from_address=data['from_address'],
            ci_admins=data['ci_admins'],
            )

    def __init__(self, smtp, from_address, ci_admins):
        assert isinstance(smtp, EmailSmtpConfig), repr(smtp)
        assert isinstance(from_address, basestring), repr(from_address)
        assert is_list_inst(ci_admins, basestring), repr(ci_admins)
        self.smtp = smtp
        self.from_address = from_address
        self.ci_admins = ci_admins

    def to_dict(self):
        return dict(
            smtp=self.smtp.to_dict(),
            from_address=self.from_address,
            ci_admins=self.ci_admins,
            )

    def report(self):
        log.info('\t' 'email:')
        self.smtp.report()
        log.info('\t\t' 'from_address: %r:', self.from_address)
        log.info('\t\t' 'ci_admins (%r total):', len(self.ci_admins))
        for email in self.ci_admins:
            log.info('\t\t\t' '%r', email)


class CiConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            timeout=str_to_timedelta(data['timeout']),
            )

    def __init__(self, timeout):
        assert isinstance(timeout, datetime.timedelta), repr(timeout)
        self.timeout = timeout

    def to_dict(self):
        return dict(
            timeout=timedelta_to_str(self.timeout),
            )

    def report(self):
        log.info('\t' 'ci:')
        log.info('\t\t' 'timeout: %s', timedelta_to_str(self.timeout))


class Config(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            junk_shop=JunkShopConfig.from_dict(data['junk_shop']),
            services=ServicesConfig.from_dict(data['services']),
            email=EmailConfig.from_dict(data['email']),
            platforms={platform_name: PlatformConfig.from_dict(platform_config)
                               for platform_name, platform_config in data['platforms'].items()},
            ci=CiConfig.from_dict(data['ci']),
            )

    def __init__(self, junk_shop, services, email, platforms, ci):
        assert isinstance(junk_shop, JunkShopConfig), repr(junk_shop)
        assert isinstance(services, ServicesConfig), repr(services)
        assert isinstance(email, EmailConfig), repr(email)
        assert is_dict_inst(platforms, basestring, PlatformConfig), repr(platforms)
        assert isinstance(ci, CiConfig), repr(ci)
        self.junk_shop = junk_shop
        self.services = services
        self.email = email
        self.platforms = platforms
        self.ci = ci

    def to_dict(self):
        return dict(
            junk_shop=self.junk_shop.to_dict(),
            services=self.services.to_dict(),
            email=self.email.to_dict(),
            platforms={platform_name: platform_config.to_dict()
                               for platform_name, platform_config in self.platforms.items()},
            ci=self.ci.to_dict(),
            )

    def report(self):
        log.info('config:')
        self.junk_shop.report()
        self.services.report()
        self.email.report()
        log.info('\t' 'platforms:')
        for platform_name, platform_info in self.platforms.items():
            log.info('\t\t' '%s:', platform_name)
            platform_info.report()
        self.ci.report()


def test_me():
    setup_logging(logging.DEBUG)
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    config = Config.from_dict(yaml.load(open(config_path)))
    config = Config.from_dict(config.to_dict())
    config.report()

if __name__ == '__main__':
    test_me()
