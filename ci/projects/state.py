import logging
from utils import SimpleNamespace, is_list_inst, is_dict_inst
from config import Config
from command import Command, SetBuildResultCommand, PythonStageCommand

log = logging.getLogger(__name__)


class Namespace(object):

    def __init__(self, d):
        self._items = d
        for key, value in d.items():
            setattr(self, key, value)

    def get(self, key, default_value=None):
        return self._items.get(key, default_value)

    def items(self):
        return self._items.items()

    def to_dict(self):
        return self._items

    def __contains__(self, key):
        return key in self._items


class SloppyNamespace(Namespace):

    def __getattr__(self, name):
        if name in self._items:
            return self._items[name]
        else:
            return None


class SshKeyCredential(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            key_path=data['key_path'],
            user=data['user'],
            )

    def __init__(self, key_path, user):
        self.key_path = key_path
        self.user = user

    def __repr__(self):
        return '<key_path=%r, user=%r>' % (self.key_path, self.user)

    def to_dict(self):
        return dict(
            key_path=self.key_path,
            user=self.user,
            )


class Credentials(Namespace):

    @classmethod
    def from_dict(cls, data, config):
        return cls({
            t.id: cls.credential_from_dict(data, t) for t in config.credentials
            })

    @staticmethod
    def credential_from_dict(data, t):
        value = data[t.id]
        if t.type == 'ssh_key':
            return SshKeyCredential.from_dict(value)
        else:
            return value

    def to_dict(self):
        return {key: self.credential_to_dict(value) for (key, value) in self._items.items()}

    @staticmethod
    def credential_to_dict(value):
        if isinstance(value, SshKeyCredential):
            return value.to_dict()
        else:
            return value


class ScmInfo(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            branch=data['branch'],
            repository_url=data['MERCURIAL_REPOSITORY_URL'],
            revision=data['MERCURIAL_REVISION_SHORT'],
            prev_revision=data.get('prev_revision'),
            )

    def __init__(self, branch, repository_url, revision, prev_revision=None):
        assert branch is None or isinstance(branch, basestring), repr(branch)
        assert isinstance(repository_url, basestring), repr(repository_url)
        assert isinstance(revision, basestring), repr(revision)
        assert prev_revision is None or isinstance(prev_revision, basestring), repr(prev_revision)
        self.branch = branch
        self.repository_url = repository_url
        self.revision = revision
        self.prev_revision = prev_revision

    def __repr__(self):
        return '<branch=%r repository_url=%r revision=%r prev_revision=%r>' % (
            self.branch, self.repository_url, self.revision, self.prev_revision)

    def to_dict(self):
        return dict(
            branch=self.branch,
            MERCURIAL_REPOSITORY_URL=self.repository_url,
            MERCURIAL_REVISION_SHORT=self.revision,
            prev_revision=self.prev_revision,
            )

    def set_prev_revision(self, prev_revision):
        assert prev_revision is None or isinstance(prev_revision, basestring), repr(prev_revision)
        self.prev_revision = str(prev_revision) if prev_revision else None


# user triggered this job, None for jobs triggered by timer or upstream job
class BuildUser(object):

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        return cls(
            id=data['id'],
            email=data['email'],
            full_name=data['full_name'],
            )

    def __init__(self, id, email, full_name):
        assert isinstance(id, basestring), repr(id)
        assert isinstance(email, basestring), repr(email)
        assert isinstance(full_name, basestring), repr(full_name)
        self.id = id
        self.email = email
        self.full_name = full_name

    def to_dict(self):
        return dict(
            id=self.id,
            email=self.email,
            full_name=self.full_name,
            )

    def report(self):
        log.info('\t' 'build user:')
        log.info('\t\t' 'id: %r' % self.id)
        log.info('\t\t' 'email: %r' % self.email)
        log.info('\t\t' 'full_name: %r' % self.full_name)


class JenkinsEnv(object):

    @classmethod
    def from_dict(cls, data):
        return cls(
            job_path=data['job_path'],
            build_number=data['build_number'],
            node_name=data['node_name'],
            build_url=data['build_url'],
            executor_number=data['executor_number'],
            branch_name=data['branch_name'],
            build_user=BuildUser.from_dict(data['build_user']),
            )

    def __init__(self, job_path, build_number, node_name, build_url, executor_number, branch_name, build_user):
        assert isinstance(job_path, basestring), repr(job_path)
        assert isinstance(build_number, int), repr(build_number)
        assert isinstance(node_name, basestring), repr(node_name)
        assert isinstance(build_url, basestring), repr(build_url)
        assert isinstance(executor_number, int), repr(executor_number)
        assert branch_name is None or isinstance(branch_name, basestring), repr(branch_name)
        assert build_user is None or isinstance(build_user, BuildUser), repr(build_user)
        self.job_path = job_path
        self.build_number = build_number
        self.node_name= node_name
        self.build_url = build_url
        self.executor_number = executor_number
        self.branch_name = branch_name
        self.build_user = build_user

    def to_dict(self):
        return dict(
            job_path=self.job_path,
            build_number=self.build_number,
            node_name=self.node_name,
            build_url=self.build_url,
            executor_number=self.executor_number,
            branch_name=self.branch_name,
            build_user=self.build_user.to_dict() if self.build_user else None,
            )

    def report(self):
        log.info('jenkins_env:')
        log.info('\t' 'job_path: %r' % self.job_path)
        log.info('\t' 'build_number: %r' % self.build_number)
        log.info('\t' 'node_name: %r' % self.node_name)
        log.info('\t' 'build_url: %r' % self.build_url)
        log.info('\t' 'executor_number: %r' % self.executor_number)
        log.info('\t' 'branch_name: %r' % self.branch_name)
        if self.build_user:
            self.build_user.report()
        else:
            log.info('\t' 'build_user: None')

    @property
    def job_name(self):
        return self.job_path.split('/')[-1]  # drop folder name


class State(object):

    @classmethod
    def from_dict(cls, data, command_registry):
        config = Config.from_dict(data['config'])
        return cls(
            jenkins_env=JenkinsEnv.from_dict(data['jenkins_env']),
            params=SloppyNamespace(data['params']),
            config=config,
            command_list=[command_registry.resolve(command) for command in data['command_list']],
            credentials=Credentials.from_dict(data['credentials'], config),
            scm_info={repository: ScmInfo.from_dict(info) for repository, info in data.get('scm', {}).items()},
            current_node=data['current_node'],
            workspace_dir=data['workspace_dir'],
            is_unix=data['is_unix'],
            current_command=PythonStageCommand.from_dict(data['current_command'], command_registry),
            clean_stamp=data.get('clean_stamp'),
            clean_build_stamp=data.get('clean_build_stamp'),
            job_result=data.get('job_result', {}),
            )

    def __init__(
            self,
            jenkins_env,
            params,
            config,
            command_list,
            credentials,
            scm_info,
            current_node,
            workspace_dir,
            is_unix,
            current_command,
            clean_stamp,
            clean_build_stamp,
            job_result,
            ):
        assert isinstance(current_command, PythonStageCommand), repr(current_command)
        assert isinstance(jenkins_env, JenkinsEnv), repr(jenkins_env)
        assert isinstance(params, SloppyNamespace), repr(params)
        assert isinstance(config, Config), repr(config)
        assert is_list_inst(command_list, Command), repr(command_list)
        assert isinstance(credentials, Namespace), repr(credentials)
        assert is_dict_inst(scm_info, basestring, ScmInfo), repr(scm_info)
        assert isinstance(current_node, basestring), repr(current_node)
        assert isinstance(workspace_dir, basestring), repr(workspace_dir)
        assert isinstance(is_unix, bool), repr(is_unix)
        assert clean_stamp is None or isinstance(clean_stamp, int), repr(clean_stamp)
        assert clean_build_stamp is None or isinstance(clean_build_stamp, int), repr(clean_build_stamp)
        assert is_dict_inst(job_result, basestring, basestring), repr(job_result)
        assert all(result in SetBuildResultCommand.known_results for result in job_result.values()), repr(job_result)
        self.jenkins_env = jenkins_env
        self.params = params
        self.config = config
        self.command_list = command_list
        self.credentials = credentials
        self.scm_info = scm_info  # repository name -> ScmInfo
        self.current_node = current_node
        self.workspace_dir = workspace_dir
        self.is_unix = is_unix
        self.current_command = current_command
        self.clean_stamp = clean_stamp  # last time when 'clean' flag was used
        self.clean_build_stamp = clean_build_stamp  # same for clean_build flag
        self.job_result = job_result  # result of BuildJobCommand, job -> build_result

    def report(self):
        self.jenkins_env.report()
        log.info('params:')
        for name, value in self.params.items():
            log.info('\t' '%s: %r', name, value)
        self.config.report()
        log.info('credentials:')
        for id, value in self.credentials.items():
            log.info('\t' '%s: %r', id, value)
        log.info('scm_info:')
        for repository, info in self.scm_info.items():
            log.info('\t' '%s: %r', repository, info)
        log.info('current_node: %r', self.current_node)
        log.info('clean_stamp: %r', self.clean_stamp)
        log.info('clean_build_stamp: %r', self.clean_build_stamp)
        log.info('job_result:')
        for job, result in self.job_result.items():
            log.info('\t' '%s: %r', job, result)

    def to_dict(self):
        return dict(
            jenkins_env=self.jenkins_env.to_dict(),
            params=self.params.to_dict(),
            config=self.config.to_dict(),
            command_list=[command.to_dict() for command in self.command_list],
            credentials=self.credentials.to_dict(),
            scm={repository_name: scm_info.to_dict() for repository_name, scm_info in self.scm_info.items()},
            current_node=self.current_node,
            workspace_dir=self.workspace_dir,
            is_unix=self.is_unix,
            clean_stamp=self.clean_stamp,
            clean_build_stamp=self.clean_build_stamp,
            job_result=self.job_result,
            )

    def make_output_state(self, command_list=None):
        return State(
            self.jenkins_env,
            self.params,
            self.config,
            command_list or self.command_list,
            self.credentials,
            self.scm_info,
            self.current_node,
            self.workspace_dir,
            self.is_unix,
            self.current_command,
            self.clean_stamp,
            self.clean_build_stamp,
            self.job_result,
            )
