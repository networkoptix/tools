import logging
from utils import SimpleNamespace, is_list_inst, is_dict_inst
from command import Command, PythonStageCommand

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
            db_host=self.db_host
            )

    def report(self):
        log.info('\t' 'junk_shop:')
        log.info('\t\t' '' 'db_host: %r:', self.db_host)


class Config(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            junk_shop=JunkShopConfig.from_dict(data['junk_shop']),
            platforms={platform_name: PlatformConfig.from_dict(platform_config)
                               for platform_name, platform_config in data['platforms'].items()},
            )

    def __init__(self, junk_shop, platforms):
        assert isinstance(junk_shop, JunkShopConfig), repr(junk_shop)
        assert is_dict_inst(platforms, basestring, PlatformConfig), repr(platforms)
        self.junk_shop = junk_shop
        self.platforms = platforms

    def to_dict(self):
        return dict(
            junk_shop=self.junk_shop.to_dict(),
            platforms={platform_name: platform_config.to_dict()
                               for platform_name, platform_config in self.platforms.items()},
            )

    def report(self):
        log.info('config:')
        self.junk_shop.report()
        log.info('\t' 'platforms:')
        for platform_name, platform_info in self.platforms.items():
            log.info('\t\t' '%s:', platform_name)
            platform_info.report()


class ScmInfo(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            branch=data['branch'],
            repository_url=data['MERCURIAL_REPOSITORY_URL'],
            revision=data['MERCURIAL_REVISION_SHORT'],
            )

    def __init__(self, branch, repository_url, revision):
        assert branch is None or isinstance(branch, basestring), repr(branch)
        assert isinstance(repository_url, basestring), repr(repository_url)
        assert isinstance(revision, basestring), repr(revision)
        self.branch = branch
        self.repository_url = repository_url
        self.revision = revision

    def __repr__(self):
        return '<branch=%r repository_url=%r revision=%r>' % (self.branch, self.repository_url, self.revision)

    def to_dict(self):
        return dict(
            branch=self.branch,
            MERCURIAL_REPOSITORY_URL=self.repository_url,
            MERCURIAL_REVISION_SHORT=self.revision,
            )


class JenkinsEnv(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            build_number=data['build_number'],
            build_url=data['build_url'],
            executor_number=data['executor_number'],
            )

    def __init__(self, build_number, build_url, executor_number):
        assert isinstance(build_number, int), repr(build_number)
        assert isinstance(build_url, basestring), repr(build_url)
        assert isinstance(executor_number, int), repr(executor_number)
        self.build_number = build_number
        self.build_url = build_url
        self.executor_number = executor_number

    def to_dict(self):
        return dict(
            build_number=self.build_number,
            build_url=self.build_url,
            executor_number=self.executor_number,
            )
    def report(self):
        log.info('jenkins_env:')
        log.info('\t' 'build_number: %r' % self.build_number)
        log.info('\t' 'build_url: %r' % self.build_url)
        log.info('\t' 'executor_number: %r' % self.executor_number)


class State(object):

    def __init__(self, jenkins_env, config, command_list, credentials, scm_info, current_node, workspace_dir, is_unix):
        assert isinstance(jenkins_env, JenkinsEnv), repr(jenkins_env)
        assert isinstance(config, Config), repr(config)
        assert is_list_inst(command_list, Command), repr(command_list)
        assert is_dict_inst(credentials, basestring, basestring), repr(credentials)
        assert is_dict_inst(scm_info, basestring, ScmInfo), repr(scm_info)
        assert isinstance(current_node, basestring), repr(current_node)
        assert isinstance(workspace_dir, basestring), repr(workspace_dir)
        assert isinstance(is_unix, bool), repr(is_unix)
        self.jenkins_env = jenkins_env
        self.config = config
        self.command_list = command_list
        self.credentials = SimpleNamespace(**credentials)
        self.scm_info = scm_info  # repository name -> ScmInfo
        self.current_node = current_node
        self.workspace_dir = workspace_dir
        self.is_unix = is_unix

    def report(self):
        self.jenkins_env.report()
        self.config.report()
        log.info('credentials:')
        for id, value in self.credentials.__dict__.items():
            log.info('\t' '%s: %r', id, value)
        log.info('scm_info:')
        for repository, info in self.scm_info.items():
            log.info('\t' '%s: %r', repository, info)
        log.info('current_node: %r', self.current_node)


class InputState(State):

    @classmethod
    def from_dict(cls, data, command_registry):
        return cls(
            jenkins_env=JenkinsEnv.from_dict(data['jenkins_env']),
            config=Config.from_dict(data['config']),
            command_list=[command_registry.resolve(command) for command in data['command_list']],
            credentials=data['credentials'],
            scm_info={repository: ScmInfo.from_dict(info) for repository, info in data.get('scm', {}).items()},
            current_node=data['current_node'],
            workspace_dir=data['workspace_dir'],
            is_unix=data['is_unix'],
            current_command=PythonStageCommand.from_dict(data['current_command'], command_registry),
            )

    def __init__(self, jenkins_env, config, command_list, credentials, scm_info, current_node, workspace_dir, is_unix, current_command):
        assert isinstance(current_command, PythonStageCommand), repr(current_command)
        State.__init__(self, jenkins_env, config, command_list, credentials, scm_info, current_node, workspace_dir, is_unix)
        self.current_command = current_command

    def make_output_state(self, command_list=None):
        return OutputState(
            self.jenkins_env,
            self.config,
            command_list or self.command_list,
            self.credentials.__dict__,
            self.scm_info,
            self.current_node,
            self.workspace_dir,
            self.is_unix,
            )


class OutputState(State):

    def to_dict(self):
        return dict(
            jenkins_env=self.jenkins_env.to_dict(),
            config=self.config.to_dict(),
            command_list=[command.to_dict() for command in self.command_list],
            credentials=self.credentials.__dict__,
            scm={repository_name: scm_info.to_dict() for repository_name, scm_info in self.scm_info.items()},
            current_node=self.current_node,
            workspace_dir=self.workspace_dir,
            is_unix=self.is_unix,
            )
