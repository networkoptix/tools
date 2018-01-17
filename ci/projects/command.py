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


class ArchiveArtifactsCommand(Command):

    command_id = 'archive_artifacts'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            artifact_mask_list=d['artifact_mask_list'],
            )

    def __init__(self, artifact_mask_list):
        assert is_list_inst(artifact_mask_list, basestring), repr(artifact_mask_list)
        self.artifact_mask_list = artifact_mask_list

    def args_to_dict(self):
        return dict(artifact_mask_list=self.artifact_mask_list)


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


class ProjectParameter(object):

    @staticmethod
    def from_dict(d):
        param_types = dict(
            boolean=BooleanProjectParameter,
            string=StringProjectParameter,
            choice=ChoiceProjectParameter,
            )
        t = dict['type']
        param_cls = param_types.get(t)
        assert param_cls, 'Unknown parameter type: %r' % t
        return param_cls.from_dict(d)

    def __init__(self, name, description):
        assert isinstance(name, basestring), repr(name)
        assert isinstance(description, basestring), repr(description)
        self.name = name
        self.description = description

    def to_dict(self):
        return dict(
            type=self.type,
            name=self.name,
            description=self.description,
            )


class BooleanProjectParameter(ProjectParameter):

    type = 'boolean'

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d['name'],
            description=d['description'],
            default_value=d['default_value'],
            )

    def __init__(self, name, description, default_value):
        assert isinstance(default_value, bool), repr(default_value)
        ProjectParameter.__init__(self, name, description)
        self.default_value = default_value

    def to_dict(self):
        return dict(
            ProjectParameter.to_dict(self),
            default_value=self.default_value,
            )


class StringProjectParameter(ProjectParameter):

    type = 'string'

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d['name'],
            description=d['description'],
            default_value=d['default_value'],
            )

    def __init__(self, name, description, default_value=''):
        assert isinstance(default_value, basestring), repr(default_value)
        ProjectParameter.__init__(self, name, description)
        self.default_value = default_value

    def to_dict(self):
        return dict(
            ProjectParameter.to_dict(self),
            default_value=self.default_value,
            )


class ChoiceProjectParameter(ProjectParameter):

    type = 'choice'

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d['name'],
            description=d['description'],
            choices=d['choices'],
            )

    def __init__(self, name, description, choices):
        assert is_list_inst(choices, basestring), repr(choices)
        ProjectParameter.__init__(self, name, description)
        self.choices = choices

    def to_dict(self):
        return dict(
            ProjectParameter.to_dict(self),
            choices=self.choices,
            )


class MultiChoiceProjectParameter(ProjectParameter):

    type = 'multi_choice'

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d['name'],
            description=d['description'],
            choices=d['choices'],
            selected_choices=d['selected_choices'],
            )

    def __init__(self, name, description, choices, selected_choices=None):
        assert is_list_inst(choices, basestring), repr(choices)
        assert selected_choices is None or is_list_inst(selected_choices, basestring), repr(selected_choices)
        ProjectParameter.__init__(self, name, description)
        self.choices = choices
        self.selected_choices = selected_choices or []

    def to_dict(self):
        return dict(
            ProjectParameter.to_dict(self),
            choices=self.choices,
            selected_choices=self.selected_choices,
            )


class SetProjectPropertiesCommand(Command):

    command_id = 'set_project_properties'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            parameters=[ProjectParameter.from_dict(p) for p in d['parameters']],
            enable_concurrent_builds=d['enable_concurrent_builds'],
            days_to_keep_old_builds=d['days_to_keep_old_builds'],
            poll_scm=d['poll_scm'],
            cron=d['cron'],
            )

    def __init__(self, parameters, enable_concurrent_builds, days_to_keep_old_builds=None, poll_scm=None, cron=None):
        assert is_list_inst(parameters, ProjectParameter), repr(parameters)
        assert isinstance(enable_concurrent_builds, bool), repr(enable_concurrent_builds)
        assert days_to_keep_old_builds is None or isinstance(days_to_keep_old_builds, int), repr(days_to_keep_old_builds)
        assert poll_scm is None or isinstance(poll_scm, basestring), repr(poll_scm)
        assert cron is None or isinstance(cron, basestring), repr(cron)
        self.parameters = parameters
        self.enable_concurrent_builds = enable_concurrent_builds
        self.days_to_keep_old_builds = days_to_keep_old_builds
        self.poll_scm = poll_scm  # cron tab format if not None
        self.cron = cron  # cron tab format if not None

    def args_to_dict(self):
        return dict(
            parameters=[p.to_dict() for p in self.parameters],
            enable_concurrent_builds=self.enable_concurrent_builds,
            days_to_keep_old_builds=self.days_to_keep_old_builds,
            poll_scm=self.poll_scm,
            cron=self.cron,
            )


class ParameterValue(object):

    @staticmethod
    def from_dict(d):
        param_types = dict(
            boolean=BooleanParameterValue,
            string=StringParameterValue,
            choice=MultiChoiceParameterValue,
            )
        t = dict['type']
        param_cls = param_types.get(t)
        assert param_cls, 'Unknown parameter type: %r' % t
        return param_cls.from_dict(d)

    def __init__(self, name, value):
        assert isinstance(name, basestring), repr(name)
        self.name = name
        self.value = value

    def to_dict(self):
        return dict(
            type=self.type,
            name=self.name,
            value=self.value_to_dict(self.value),
            )

    def value_to_dict(self, value):
        return value


class BooleanParameterValue(ParameterValue):

    type = 'boolean'

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d['name'],
            value=d['value'],
            )

    def __init__(self, name, value):
        assert isinstance(value, bool), repr(value)
        ParameterValue.__init__(self, name, value)


class StringParameterValue(ParameterValue):

    type = 'string'

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d['name'],
            value=d['value'],
            )

    def __init__(self, name, value):
        assert isinstance(value, basestring), repr(value)
        ParameterValue.__init__(self, name, value)


class MultiChoiceParameterValue(ParameterValue):

    type = 'multi_choice'

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d['name'],
            value=d['value'].split(','),
            )

    def __init__(self, name, value):
        assert is_list_inst(value, basestring), repr(value)
        ParameterValue.__init__(self, name, value)

    def value_to_dict(self, value):
        return ','.join(value)


class BuildJobCommand(Command):

    command_id = 'build_job'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            job=d['job'],
            parameters=[ParameterValue.from_dict(p) for p in d['parameters']],
            wait_for_completion=d['wait'],
            propagate_errors=d['propagate'],
            )

    def __init__(self, job, parameters, wait_for_completion=True, propagate_errors=True):
        assert isinstance(job, basestring), repr(job)  # 'ci/vms_3.2'
        assert is_list_inst(parameters, ParameterValue), repr(parameters)
        assert isinstance(wait_for_completion, bool), repr(wait_for_completion)
        assert isinstance(propagate_errors, bool), repr(propagate_errors)
        self.job = job
        self.parameters = parameters
        self.wait_for_completion = wait_for_completion
        self.propagate_errors = propagate_errors

    def args_to_dict(self):
        return dict(
            job=self.job,
            parameters=[p.to_dict() for p in self.parameters],
            wait_for_completion=self.wait_for_completion,
            propagate_errors=self.propagate_errors,
            )


class SetBuildResultCommand(Command):

    command_id = 'set_build_result'

    brSUCCESS = 'SUCCESS'
    brFAILURE = 'FAILURE'
    brUNSTABLE = 'UNSTABLE'
    brABORTED = 'ABORTED'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            build_result=d['build_result'],
            )

    def __init__(self, build_result):
        assert build_result in [self.brSUCCESS, self.brFAILURE, self.brUNSTABLE, self.brABORTED], repr(build_result)
        self.build_result = build_result

    def args_to_dict(self):
        return dict(
            build_result=self.build_result,
            )


class PythonStageCommand(Command):

    command_id = 'python_stage'

    @classmethod
    def from_dict(cls, d, command_registry):
        return cls(
            project_id=d['project_id'],
            stage_id=d['stage_id'],
            in_assist_mode=d['in_assist_mode'],
            python_path_list=d.get('python_path_list'),
            **{key: value for key, value in d.items()
                   if key not in ['command_id', 'project_id', 'stage_id', 'in_assist_mode', 'python_path_list']}
            )

    def __init__(self, project_id, stage_id, in_assist_mode, python_path_list=None, **kw):
        assert isinstance(project_id, basestring), repr(project_id)
        assert isinstance(stage_id, basestring), repr(stage_id)
        assert isinstance(in_assist_mode, bool), repr(in_assist_mode)
        assert python_path_list is None or is_list_inst(python_path_list, basestring), repr(python_path_list)
        self.project_id = project_id
        self.stage_id = stage_id
        self.in_assist_mode = in_assist_mode
        self.python_path_list = python_path_list or []  # used by Commander
        self.custom_info = kw
        for key, value in self.custom_info.items():
            setattr(self, key, value)

    def args_to_dict(self):
        return dict(
            self.custom_info,
            project_id=self.project_id,
            stage_id=self.stage_id,
            in_assist_mode=self.in_assist_mode,
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
            SetBuildResultCommand,
            PythonStageCommand,
            ]:
        command_registry.register(command_cls)
