import abc
from utils import is_list_inst


class CommandRegistry(object):

    def __init__(self):
        self._registry = {}

    def register(self, command_cls):
        self._registry[command_cls.command_id] = command_cls

    def resolve(self, command_dict):
        command_id = command_dict['command_id']
        command_cls = self._registry.get(command_id)
        assert command_cls, 'Unknown command id: %r' % command_id
        return command_cls.from_dict(command_dict, self)


class Command(object):

    __metaclass__ = abc.ABCMeta

    def to_dict(self):
        return dict(self.args_to_dict(), command_id=self.command_id)

    @abc.abstractmethod
    def args_to_dict(self):
        pass


class ScriptCommand(Command):

    command_id = 'script'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            script=d['script'],
            )

    def __init__(self, script):
        assert isinstance(script, basestring), repr(script)
        self.script = script

    def args_to_dict(self):
        return dict(script=self.script)


class CheckoutCommand(Command):

    command_id = 'checkout'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            repository=d['repository'],
            branch=d['branch'],
            )

    def __init__(self, repository, branch='default'):
        assert isinstance(repository, basestring), repr(repository)
        assert isinstance(branch, basestring), repr(branch)
        self.repository = repository  # 'devtools', 'nx_vms' etc
        self.branch = branch

    def args_to_dict(self):
        return dict(repository=self.repository, branch=self.branch)


class CheckoutScmCommand(Command):

    command_id = 'checkout_scm'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            repository=d['repository'],
            )

    def __init__(self, repository):
        assert isinstance(repository, basestring), repr(repository)
        # repository name and also target dir to checkout to, 'devtools', 'nx_vms' etc
        self.repository = repository

    def args_to_dict(self):
        return dict(repository=self.repository)


class StashCommand(Command):

    command_id = 'stash'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            name=d['name'],
            pattern_list=d['pattern_list'],
            )

    def __init__(self, name, pattern_list):
        assert isinstance(name, basestring), repr(name)
        assert is_list_inst(pattern_list, basestring), repr(pattern_list)
        self.name = name
        self.pattern_list = pattern_list

    def args_to_dict(self):
        return dict(name=self.name, pattern_list=self.pattern_list)

        
class UnstashCommand(Command):

    command_id = 'unstash'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            name=d['name'],
            )

    def __init__(self, name):
        assert isinstance(name, basestring), repr(name)
        self.name = name

    def args_to_dict(self):
        return dict(name=self.name)


class CleanDirCommand(Command):

    command_id = 'clean_dir'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls()

    def __init__(self):
        pass

    def args_to_dict(self):
        return dict()


class ParallelJob(object):

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            job_name=d['job_name'],
            command_list=[command_registry.resolve(command) for command in d['command_list']],
            )

    def __init__(self, job_name, command_list):
        assert isinstance(job_name, basestring), repr(job_name)
        assert is_list_inst(command_list, Command), repr(command_list)
        self.job_name = job_name
        self.command_list = command_list

    def to_dict(self):
        return dict(job_name=self.job_name, command_list=[command.to_dict() for command in self.command_list])

        
class ParallelCommand(Command):

    command_id = 'parallel'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            job_list=[ParallelJob.from_dict(job, command_registry) for job in d['job_list']],
            )

    def __init__(self, job_list):
        assert is_list_inst(job_list, ParallelJob), repr(job_list)
        self.job_list = job_list

    def args_to_dict(self):
        return dict(job_list=[job.to_dict() for job in self.job_list])


class NodeCommand(Command):

    command_id = 'node'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            node_name=d['node_name'],
            workspace_dir=d['workspace_dir'],
            command_list=[command_registry.resolve(command) for command in self.command_list],
            )

    def __init__(self, node_name, workspace_dir=None, command_list=None):
        assert isinstance(node_name, basestring), repr(node_name)
        assert workspace_dir is None or isinstance(workspace_dir, basestring), repr(workspace_dir)
        assert command_list is None or is_list_inst(command_list, Command), repr(command_list)
        self.node_name = node_name
        self.workspace_dir = workspace_dir
        self.command_list = command_list

    def args_to_dict(self):
        return dict(
            node=self.node_name,
            workspace_dir=self.workspace_dir,
            command_list=[command.to_dict() for command in self.command_list],
            )


class PrepareVirtualEnvCommand(Command):

    command_id = 'prepare_virtualenv'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            requirements_file_list=d['requirements_file_list'],
            )

    def __init__(self, requirements_file_list=None):
        assert requirements_file_list is None or is_list_inst(requirements_file_list, basestring), repr(requirements_file_list)
        self.requirements_file_list = requirements_file_list or []

    def args_to_dict(self):
        return dict(requirements_file_list=self.requirements_file_list)


class PythonStageCommand(Command):

    command_id = 'python_stage'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            project_id=d['project_id'],
            stage_id=d['stage_id'],
            python_path_list=d.get('python_path_list'),
            **{key: value for key, value in d.items()
                   if key not in ['project_id', 'stage_id', 'python_path_list']}
            )

    def __init__(self, project_id, stage_id, python_path_list=None, **kw):
        assert isinstance(project_id, basestring), repr(project_id)
        assert isinstance(stage_id, basestring), repr(stage_id)
        assert python_path_list is None or is_list_inst(python_path_list, basestring), repr(python_path_list)
        self.project_id = project_id
        self.stage_id = stage_id
        self.python_path_list = python_path_list or []
        self.custom_info = kw
        for key, value in self.custom_info.items():
            setattr(self, key, value)

    def args_to_dict(self):
        return dict(
            self.custom_info,
            project_id=self.project_id,
            stage_id=self.stage_id,
            python_path_list=self.python_path_list,
            )


def register_all_commands(command_registry):
    for command_cls in [
            ScriptCommand,
            CheckoutCommand,
            CheckoutScmCommand,
            StashCommand,
            UnstashCommand,
            CleanDirCommand,
            ParallelCommand,
            NodeCommand,
            PrepareVirtualEnvCommand,
            PythonStageCommand,
            ]:
        command_registry.register(command_cls)
