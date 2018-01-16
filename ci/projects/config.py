import sys
import logging
import os.path
import datetime
import yaml

from utils import setup_logging, is_list_inst, is_dict_inst, str_to_timedelta, timedelta_to_str

log = logging.getLogger(__name__)


# configuration common for all branches, stored in devtools/ci/projects/config.yaml

class PlatformConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            build_node=data['build_node'],
            should_run_unit_tests=data['should_run_unit_tests'],
            artifact_mask_list=data['artifact_mask_list'],
            generator=data.get('generator'),
            )

    def __init__(self, build_node, should_run_unit_tests, artifact_mask_list, generator):
        assert isinstance(build_node, basestring), repr(build_node)
        assert isinstance(should_run_unit_tests, bool), repr(should_run_unit_tests)
        assert is_list_inst(artifact_mask_list,  basestring), repr(artifact_mask_list)
        assert generator is None or isinstance(generator, basestring), repr(generator)
        self.build_node = build_node
        self.should_run_unit_tests = should_run_unit_tests
        self.artifact_mask_list = artifact_mask_list
        self.generator = generator

    def to_dict(self):
        return dict(
            build_node=self.build_node,
            should_run_unit_tests=self.should_run_unit_tests,
            artifact_mask_list=self.artifact_mask_list,
            generator=self.generator,
            )

    def report(self):
        log.info('\t\t\t' 'build_node: %r', self.build_node)
        log.info('\t\t\t' 'should_run_unit_tests: %r', self.should_run_unit_tests)
        log.info('\t\t\t' 'artifact_mask_list: %r', self.artifact_mask_list)
        log.info('\t\t\t' 'generator: %r', self.generator)


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
            platforms=data['platforms'],
            )

    def __init__(self, timeout, platforms):
        assert isinstance(timeout, datetime.timedelta), repr(timeout)
        assert is_list_inst(platforms, basestring), repr(platforms)
        self.timeout = timeout
        self.platforms = platforms

    def to_dict(self):
        return dict(
            timeout=timedelta_to_str(self.timeout),
            platforms=self.platforms,
            )

    def report(self):
        log.info('\t' 'ci:')
        log.info('\t\t' 'timeout: %s', timedelta_to_str(self.timeout))
        log.info('\t\t' 'platforms: %s', ', '.join(self.platforms))


class TestsWatchersConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            watcher_email=data['watcher_email'],
            test_list=data['test_list'],
            )

    def __init__(self, watcher_email, test_list):
        assert isinstance(watcher_email, basestring), repr(watcher_email)
        assert is_list_inst(test_list, basestring), repr(test_list)
        assert test_list  # Must not be empty
        self.watcher_email = watcher_email
        self.test_list = test_list

    def to_dict(self):
        return dict(
            watcher_email=self.watcher_email,
            test_list=self.test_list,
            )

    def report(self):
        log.info('\t\t\t' 'watcher_email: %r', self.watcher_email)
        log.info('\t\t\t' 'test_list:')
        for test in self.test_list:
            log.info('\t\t\t\t' '%r', test)


class Config(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            junk_shop=JunkShopConfig.from_dict(data['junk_shop']),
            services=ServicesConfig.from_dict(data['services']),
            email=EmailConfig.from_dict(data['email']),
            customization_list=data['customization_list'],
            platforms={platform_name: PlatformConfig.from_dict(platform_config)
                               for platform_name, platform_config in data['platforms'].items()},
            ci=CiConfig.from_dict(data['ci']),
            tests_watchers={name: TestsWatchersConfig.from_dict(twc)
                                for name, twc in data['tests_watchers'].items()},
            )

    def __init__(self, junk_shop, services, email, customization_list, platforms, ci, tests_watchers):
        assert isinstance(junk_shop, JunkShopConfig), repr(junk_shop)
        assert isinstance(services, ServicesConfig), repr(services)
        assert isinstance(email, EmailConfig), repr(email)
        assert is_list_inst(customization_list, basestring), repr(customization_list)
        assert is_dict_inst(platforms, basestring, PlatformConfig), repr(platforms)
        assert isinstance(ci, CiConfig), repr(ci)
        assert is_dict_inst(tests_watchers, basestring, TestsWatchersConfig), repr(tests_watchers)
        self.junk_shop = junk_shop
        self.services = services
        self.email = email
        self.customization_list = customization_list
        self.platforms = platforms
        self.ci = ci
        self.tests_watchers = tests_watchers

    def to_dict(self):
        return dict(
            junk_shop=self.junk_shop.to_dict(),
            services=self.services.to_dict(),
            email=self.email.to_dict(),
            customization_list=self.customization_list,
            platforms={platform_name: platform_config.to_dict()
                               for platform_name, platform_config in self.platforms.items()},
            ci=self.ci.to_dict(),
            tests_watchers={name: twc.to_dict() for name, twc in self.tests_watchers.items()},
            )

    def report(self):
        log.info('config:')
        self.junk_shop.report()
        self.services.report()
        self.email.report()
        log.info('\t' 'customization_list:')
        for customization in self.customization_list:
            log.info('\t\t' '%r', customization)
        log.info('\t' 'platforms:')
        for platform_name, platform_info in self.platforms.items():
            log.info('\t\t' '%s:', platform_name)
            platform_info.report()
        self.ci.report()
        log.info('\t' 'tests_watchers:')
        for name, twc in self.tests_watchers.items():
            log.info('\t\t' '%s:', name)
            twc.report()


# configuration specific for a branch, stored in nx_vms/ci/config.yaml (may be missing, defaults are used then)

class PlatformBranchConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            c_compiler=data.get('c_compiler'),
            cxx_compiler=data.get('cxx_compiler'),
            )

    def __init__(self, c_compiler, cxx_compiler):
        assert c_compiler is None or isinstance(c_compiler, basestring), repr(c_compiler)
        assert cxx_compiler is None or isinstance(cxx_compiler, basestring), repr(cxx_compiler)
        self.c_compiler = c_compiler
        self.cxx_compiler = cxx_compiler

    def to_dict(self):
        return dict(
            c_compiler=self.c_compiler,
            cxx_compiler=self.cxx_compiler,
            )

    def report(self):
        log.info('\t\t\t' 'c_compiler: %r', self.c_compiler)
        log.info('\t\t\t' 'cxx_compiler: %r', self.cxx_compiler)


class BranchConfig(object):

    @classmethod
    def make_default(cls):
        return cls(
            platforms={},
            )

    @classmethod
    def from_dict(cls, data):
        return cls(
            platforms={platform_name: PlatformBranchConfig.from_dict(platform_config)
                               for platform_name, platform_config in data['platforms'].items()},
            )

    def __init__(self, platforms):
        assert is_dict_inst(platforms, basestring, PlatformBranchConfig), repr(platforms)
        self.platforms = platforms

    def to_dict(self):
        return dict(
            platforms={platform_name: platform_config.to_dict()
                               for platform_name, platform_config in self.platforms.items()},
            )

    def report(self):
        log.info('branch config:')
        log.info('\t' 'platforms: %s', '' if self.platforms else 'none' )
        for platform_name, platform_info in self.platforms.items():
            log.info('\t\t' '%s:', platform_name)
            platform_info.report()


def test_me():
    setup_logging(logging.DEBUG)
    if len(sys.argv) == 1:
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        config = Config.from_dict(yaml.load(open(config_path)))
        config = Config.from_dict(config.to_dict())
        config.report()
        return
    if sys.argv[1] == 'default':
        branch_config = BranchConfig.make_default()
    else:
        branch_config_path = sys.argv[1]
        branch_config = BranchConfig.from_dict(yaml.load(open(branch_config_path)))
    branch_config = BranchConfig.from_dict(branch_config.to_dict())
    branch_config.report()

if __name__ == '__main__':
    test_me()
