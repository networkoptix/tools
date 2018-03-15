import sys
import logging
import os.path
import datetime
import yaml

from utils import setup_logging, is_list_inst, is_dict_inst, str_to_timedelta, timedelta_to_str

log = logging.getLogger(__name__)


DEFAULT_CI_CUSTOMIZATION = 'hanwha'


# configuration common for all branches, stored in devtools/ci/projects/config.yaml


class Credential(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data['id'],
            type=data['type'],
            )

    def __init__(self, id, type):
        assert isinstance(id, basestring), repr(id)
        assert type in ['name_and_password', 'password', 'ssh_key'], repr(type)
        self.id = id
        self.type = type

    def to_dict(self):
        return dict(
            id=self.id,
            type=self.type,
            )

    def report(self):
        log.info('\t\t\t' 'id: %r', self.id)
        log.info('\t\t\t' 'type: %r', self.type)


class PlatformConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            build_node=data['build_node'],
            should_run_unit_tests=data['should_run_unit_tests'],
            distributive_mask_list=data['distributive_mask_list'],
            update_mask_list=data['update_mask_list'],
            publish_dir=data['publish_dir'],
            generator=data.get('generator'),
            toolset=data.get('toolset'),
            )

    def __init__(self, build_node, should_run_unit_tests, distributive_mask_list, update_mask_list, publish_dir, generator, toolset):
        assert isinstance(build_node, basestring), repr(build_node)
        assert isinstance(should_run_unit_tests, bool), repr(should_run_unit_tests)
        assert is_list_inst(distributive_mask_list,  basestring), repr(distributive_mask_list)
        assert is_list_inst(update_mask_list,  basestring), repr(update_mask_list)
        assert isinstance(publish_dir, basestring), repr(publish_dir)
        assert generator is None or isinstance(generator, basestring), repr(generator)
        assert toolset is None or isinstance(toolset, basestring), repr(toolset)
        self.build_node = build_node
        self.should_run_unit_tests = should_run_unit_tests
        self.distributive_mask_list = distributive_mask_list
        self.update_mask_list = update_mask_list
        self.publish_dir = publish_dir
        self.generator = generator
        self.toolset = toolset

    def to_dict(self):
        return dict(
            build_node=self.build_node,
            should_run_unit_tests=self.should_run_unit_tests,
            distributive_mask_list=self.distributive_mask_list,
            update_mask_list=self.update_mask_list,
            publish_dir=self.publish_dir,
            generator=self.generator,
            toolset=self.toolset,
            )

    def report(self):
        log.info('\t\t\t' 'build_node: %r', self.build_node)
        log.info('\t\t\t' 'should_run_unit_tests: %r', self.should_run_unit_tests)
        log.info('\t\t\t' 'distributive_mask_list: %r', self.distributive_mask_list)
        log.info('\t\t\t' 'update_mask_list: %r', self.update_mask_list)
        log.info('\t\t\t' 'publish_dir: %r', self.publish_dir)
        log.info('\t\t\t' 'generator: %r', self.generator)
        log.info('\t\t\t' 'toolset: %r', self.toolset)


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
            mercurial_repository_url=data['mercurial_repository_url'],
            junk_shop_url=data['junk_shop_url'].rstrip('/'),
            jira_url=data['jira_url'],
            scm_browser_url_format=data['scm_browser_url_format'],
            deployment_path=data['deployment_path'],
            )

    def __init__(self, mercurial_repository_url, junk_shop_url, jira_url, scm_browser_url_format, deployment_path):
        assert isinstance(mercurial_repository_url, basestring), repr(mercurial_repository_url)
        assert isinstance(junk_shop_url, basestring), repr(junk_shop_url)
        assert isinstance(jira_url, basestring), repr(jira_url)
        assert isinstance(scm_browser_url_format, basestring), repr(scm_browser_url_format)
        assert isinstance(deployment_path, basestring), repr(deployment_path)
        self.mercurial_repository_url = mercurial_repository_url
        self.junk_shop_url = junk_shop_url
        self.jira_url = jira_url
        self.scm_browser_url_format = scm_browser_url_format
        self.deployment_path = deployment_path

    def to_dict(self):
        return dict(
            mercurial_repository_url=self.mercurial_repository_url,
            junk_shop_url=self.junk_shop_url,
            jira_url=self.jira_url,
            scm_browser_url_format=self.scm_browser_url_format,
            deployment_path=self.deployment_path,
            )

    def report(self):
        log.info('\t' 'services:')
        log.info('\t\t' 'mercurial_repository_url: %r:', self.mercurial_repository_url)
        log.info('\t\t' 'junk_shop_url: %r:', self.junk_shop_url)
        log.info('\t\t' 'jira_url: %r:', self.jira_url)
        log.info('\t\t' 'scm_browser_url_format: %r:', self.scm_browser_url_format)
        log.info('\t\t' 'deployment_path: %r:', self.deployment_path)


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


class BuildConfig(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            cmake_version=data['cmake_version'],
            rebuild_cause_file_patterns=data['rebuild_cause_file_patterns'],
            )

    def __init__(self, cmake_version, rebuild_cause_file_patterns):
        assert isinstance(cmake_version, basestring), repr(cmake_version)
        assert is_list_inst(rebuild_cause_file_patterns, basestring), repr(rebuild_cause_file_patterns)
        self.cmake_version = cmake_version
        self.rebuild_cause_file_patterns = rebuild_cause_file_patterns

    def to_dict(self):
        return dict(
            cmake_version=self.cmake_version,
            rebuild_cause_file_patterns=self.rebuild_cause_file_patterns,
            )

    def report(self):
        log.info('\t' 'build:')
        log.info('\t\t' 'cmake_version: %r', self.cmake_version)
        log.info('\t\t' 'rebuild_cause_file_patterns:')
        for patterns in self.rebuild_cause_file_patterns:
            log.info('\t\t\t' '%r', patterns)


class UnitTestsConfig(object):

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
        log.info('\t' 'unit_tests:')
        log.info('\t\t' 'timeout: %s', timedelta_to_str(self.timeout))


class ProjectConfig(object):

    def __init__(self, enable_concurrent_builds, days_to_keep_old_builds):
        assert isinstance(enable_concurrent_builds, bool), repr(enable_concurrent_builds)
        assert isinstance(days_to_keep_old_builds, int), repr(days_to_keep_old_builds)
        self.enable_concurrent_builds = enable_concurrent_builds
        self.days_to_keep_old_builds = days_to_keep_old_builds

    def to_dict(self):
        return dict(
            enable_concurrent_builds=self.enable_concurrent_builds,
            days_to_keep_old_builds=self.days_to_keep_old_builds,
            )

    def report(self):
        log.info('\t\t' 'enable_concurrent_builds: %r', self.enable_concurrent_builds)
        log.info('\t\t' 'days_to_keep_old_builds: %r', self.days_to_keep_old_builds)


class FunTestsConfig(ProjectConfig):

    @classmethod
    def from_dict(cls, data):
        return cls(
            platforms=data['platforms'],
            node=data['node'],
            timeout=str_to_timedelta(data['timeout']),
            port_base=data['port_base'],
            port_range=data['port_range'],
            binaries_url=data['binaries_url'],
            enable_concurrent_builds=data['enable_concurrent_builds'],
            days_to_keep_old_builds=data['days_to_keep_old_builds'],
            )

    def __init__(self, platforms, node, timeout, port_base, port_range, binaries_url, enable_concurrent_builds, days_to_keep_old_builds):
        assert is_list_inst(platforms, basestring), repr(platforms)
        assert isinstance(node, basestring), repr(node)
        assert isinstance(timeout, datetime.timedelta), repr(timeout)
        assert isinstance(port_base, int), repr(port_base)
        assert isinstance(port_range, int), repr(port_range)
        assert isinstance(binaries_url, basestring), repr(binaries_url)
        ProjectConfig.__init__(self, enable_concurrent_builds, days_to_keep_old_builds)
        self.platforms = platforms
        self.node = node
        self.timeout = timeout
        self.port_base = port_base
        self.port_range = port_range
        self.binaries_url = binaries_url

    def to_dict(self):
        return dict(
            ProjectConfig.to_dict(self),
            platforms=self.platforms,
            node=self.node,
            timeout=timedelta_to_str(self.timeout),
            port_base=self.port_base,
            port_range=self.port_range,
            binaries_url=self.binaries_url,
            )

    def report(self):
        log.info('\t' 'fun_tests:')
        log.info('\t\t' 'platforms: %r', self.platforms)
        log.info('\t\t' 'node: %r', self.node)
        log.info('\t\t' 'timeout: %s', timedelta_to_str(self.timeout))
        log.info('\t\t' 'port_base: %r', self.port_base)
        log.info('\t\t' 'port_range: %r', self.port_range)
        log.info('\t\t' 'binaries_url: %r', self.binaries_url)
        ProjectConfig.report(self)


class CiConfig(ProjectConfig):

    @classmethod
    def from_dict(cls, data):
        return cls(
            platforms=data['platforms'],
            nightly_schedule=data['nightly_schedule'],
            enable_concurrent_builds=data['enable_concurrent_builds'],
            days_to_keep_old_builds=data['days_to_keep_old_builds'],
            )

    def __init__(self, platforms, nightly_schedule, enable_concurrent_builds, days_to_keep_old_builds):
        assert is_list_inst(platforms, basestring), repr(platforms)
        assert isinstance(nightly_schedule, basestring), repr(nightly_schedule)
        assert isinstance(enable_concurrent_builds, bool), repr(enable_concurrent_builds)
        assert isinstance(days_to_keep_old_builds, int), repr(days_to_keep_old_builds)
        ProjectConfig.__init__(self, enable_concurrent_builds, days_to_keep_old_builds)
        self.platforms = platforms
        self.nightly_schedule = nightly_schedule

    def to_dict(self):
        return dict(
            ProjectConfig.to_dict(self),
            platforms=self.platforms,
            nightly_schedule=self.nightly_schedule,
            )

    def report(self):
        log.info('\t' 'ci:')
        log.info('\t\t' 'platforms: %s', ', '.join(self.platforms))
        log.info('\t\t' 'nightly_schedule: %r', self.nightly_schedule)
        ProjectConfig.report(self)


class ReleaseConfig(ProjectConfig):

    @classmethod
    def from_dict(cls, data):
        return cls(
            enable_concurrent_builds=data['enable_concurrent_builds'],
            days_to_keep_old_builds=data['days_to_keep_old_builds'],
            )

    def __init__(self, enable_concurrent_builds, days_to_keep_old_builds):
        ProjectConfig.__init__(self, enable_concurrent_builds, days_to_keep_old_builds)

    def to_dict(self):
        return dict(
            ProjectConfig.to_dict(self),
            )

    def report(self):
        log.info('\t' 'release:')
        ProjectConfig.report(self)


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
            credentials=[Credential.from_dict(d) for d in data['credentials']],
            junk_shop=JunkShopConfig.from_dict(data['junk_shop']),
            services=ServicesConfig.from_dict(data['services']),
            email=EmailConfig.from_dict(data['email']),
            build=BuildConfig.from_dict(data['build']),
            unit_tests=UnitTestsConfig.from_dict(data['unit_tests']),
            ci=CiConfig.from_dict(data['ci']),
            release=ReleaseConfig.from_dict(data['release']),
            fun_tests=FunTestsConfig.from_dict(data['fun_tests']),
            customization_list=data['customization_list'],
            platforms={platform_name: PlatformConfig.from_dict(platform_config)
                               for platform_name, platform_config in data['platforms'].items()},
            tests_watchers={name: TestsWatchersConfig.from_dict(twc)
                                for name, twc in data['tests_watchers'].items()},
            )

    def __init__(self, credentials, junk_shop, services, email, build, unit_tests, ci, release, fun_tests, customization_list, platforms, tests_watchers):
        assert is_list_inst(credentials, Credential), repr(credentials)
        assert isinstance(junk_shop, JunkShopConfig), repr(junk_shop)
        assert isinstance(services, ServicesConfig), repr(services)
        assert isinstance(email, EmailConfig), repr(email)
        assert isinstance(build, BuildConfig), repr(build)
        assert isinstance(unit_tests, UnitTestsConfig), repr(unit_tests)
        assert isinstance(ci, CiConfig), repr(ci)
        assert isinstance(release, ReleaseConfig), repr(release)
        assert isinstance(fun_tests, FunTestsConfig), repr(fun_tests)
        assert is_list_inst(customization_list, basestring), repr(customization_list)
        assert is_dict_inst(platforms, basestring, PlatformConfig), repr(platforms)
        assert is_dict_inst(tests_watchers, basestring, TestsWatchersConfig), repr(tests_watchers)
        self.credentials = credentials
        self.junk_shop = junk_shop
        self.services = services
        self.email = email
        self.build = build
        self.unit_tests = unit_tests
        self.ci = ci
        self.release = release
        self.fun_tests = fun_tests
        self.customization_list = customization_list
        self.platforms = platforms
        self.tests_watchers = tests_watchers

    def to_dict(self):
        return dict(
            credentials=[c.to_dict() for c in self.credentials],
            junk_shop=self.junk_shop.to_dict(),
            services=self.services.to_dict(),
            email=self.email.to_dict(),
            build=self.build.to_dict(),
            unit_tests=self.unit_tests.to_dict(),
            ci=self.ci.to_dict(),
            release=self.release.to_dict(),
            fun_tests=self.fun_tests.to_dict(),
            customization_list=self.customization_list,
            platforms={platform_name: platform_config.to_dict()
                               for platform_name, platform_config in self.platforms.items()},
            tests_watchers={name: twc.to_dict() for name, twc in self.tests_watchers.items()},
            )

    def report(self):
        log.info('config:')
        log.info('\t' 'credentials:')
        for c in self.credentials:
            c.report()
        self.junk_shop.report()
        self.services.report()
        self.email.report()
        self.build.report()
        self.unit_tests.report()
        self.ci.report()
        self.release.report()
        self.fun_tests.report()
        log.info('\t' 'customization_list:')
        for customization in self.customization_list:
            log.info('\t\t' '%r', customization)
        log.info('\t' 'platforms:')
        for platform_name, platform_info in self.platforms.items():
            log.info('\t\t' '%s:', platform_name)
            platform_info.report()
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


class CiBranchConfig(object):

    @classmethod
    def make_default(cls):
        return cls(
            platform_list=None,
            customization=DEFAULT_CI_CUSTOMIZATION,
            )

    @classmethod
    def from_dict(cls, data):
        if data is None:
            return cls.make_default()
        return cls(
            platform_list=data.get('platform_list'),
            customization=data.get('customization', DEFAULT_CI_CUSTOMIZATION),
            )

    def __init__(self, platform_list, customization):
        assert platform_list is None or is_list_inst(platform_list, basestring), repr(platform_list)
        assert customization is None or isinstance(customization, basestring), repr(customization)
        self.platform_list = platform_list
        self.customization = customization

    def to_dict(self):
        return dict(
            platform_list=self.platform_list,
            customization=self.customization,
            )

    def report(self):
        log.info('\t' 'ci:')
        log.info('\t\t' 'platform_list: %r', self.platform_list)
        log.info('\t\t' 'customization: %r', self.customization)


class BranchConfig(object):

    @classmethod
    def make_default(cls):
        return cls(
            platforms={},
            ci=CiBranchConfig.make_default(),
            )

    @classmethod
    def from_dict(cls, data):
        return cls(
            platforms={platform_name: PlatformBranchConfig.from_dict(platform_config)
                               for platform_name, platform_config in data['platforms'].items()},
            ci=CiBranchConfig.from_dict(data.get('ci')),
            )

    def __init__(self, platforms, ci):
        assert is_dict_inst(platforms, basestring, PlatformBranchConfig), repr(platforms)
        assert isinstance(ci, CiBranchConfig), repr(ci)
        self.platforms = platforms
        self.ci = ci

    def to_dict(self):
        return dict(
            platforms={platform_name: platform_config.to_dict()
                               for platform_name, platform_config in self.platforms.items()},
            ci=self.ci.to_dict(),
            )

    def report(self):
        log.info('branch config:')
        log.info('\t' 'platforms: %s', '' if self.platforms else 'none' )
        for platform_name, platform_info in self.platforms.items():
            log.info('\t\t' '%s:', platform_name)
            platform_info.report()
        self.ci.report()


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
