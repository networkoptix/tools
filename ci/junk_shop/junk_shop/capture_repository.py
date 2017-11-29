import os
from argparse import ArgumentTypeError
import re
import bz2
import threading
from pony.orm import db_session, commit, flush, select, desc, raw_sql, sql_debug
from .utils import SimpleNamespace, datetime_utc_now, param_to_bool
from . import models


VERSION_REGEX = r'^\d+(\.\d+)+$'


class BuildParameters(object):

    example = ','.join([
        'project=ci',
        'branch=dev_3.1_dev',
        'version=3.1.0.1000',
        'build_num=1000',
        'release=beta',
        'configuration=debug',
        'cloud_group=demo',
        'customization=default'
        'is_incremental=true',
        'jenkins_url=http://la.hdw.mx/jenkins/job/test/16299/'
        'repository_url=ssh://hg@hdw.mx/nx_vms',
        'revision=81510b15f3bc',
        'duration_ms=1234',
        'platform=linux-x64',
        ])
    known_parameters = [
        'project',
        'branch',
        'version',
        'build_num',
        'release',
        'configuration',
        'cloud_group',
        'customization',
        'is_incremental',
        'jenkins_url',
        'repository_url',
        'revision',
        'duration_ms',
        'platform',
        ]

    @classmethod
    def from_string(cls, parameters_str):
        error_msg = 'Expected build parameters in form "%s", but got: %r' % (cls.example, parameters_str)
        parameters = cls()
        for pair in parameters_str.split(','):
            l = pair.split('=')
            if len(l) != 2:
                raise ArgumentTypeError(error_msg)
            name, value = l
            if name not in cls.known_parameters:
                raise ArgumentTypeError('Unknown build parameter: %r. Known are: %s' % (name, ', '.join(cls.known_parameters)))
            if value == 'null':
                raise ArgumentTypeError('Got null value for %r parameter' % name)
            if name == 'is_incremental':
                value = param_to_bool(value)
            if name in ['duration_ms', 'build_num']:
                if not re.match(r'^\d+$', value):
                    raise ArgumentTypeError('Invalid int for duration_ms: %r' % value)
            if name == 'build_num':
                value = int(value)
            if name == 'release' and value not in ['release', 'beta']:
                raise ArgumentTypeError('Invalid value for "release": %r; allowed are: "release" and "beta"' % value)
            if name == 'duration_ms':
                value = timedelta(milliseconds=int(duration_ms))
                name = 'duration'
            setattr(parameters, name, value)
        if parameters.version:
            if not re.match(VERSION_REGEX, parameters.version):
                raise ArgumentTypeError('Invalid version: %r. Expected string in format: 1.2.3.4' % parameters.version)
            parameters.build_num = int(parameters.version.split('.')[-1])
        return parameters

    def __init__(self,
                 project=None,
                 branch=None,
                 version=None,
                 build_num=None,
                 release=None,
                 configuration=None,
                 cloud_group=None,
                 customization=None,
                 is_incremental=None,
                 jenkins_url=None,
                 repository_url=None,
                 revision=None,
                 duration=None,
                 platform=None,
                 ):
        assert release in [None, 'release', 'beta'], repr(release)
        self.project = project
        self.branch = branch
        self.version = version
        self.build_num = build_num
        self.release = release
        self.configuration = configuration
        self.cloud_group = cloud_group
        self.customization = customization
        self.is_incremental = is_incremental
        self.jenkins_url = jenkins_url
        self.repository_url = repository_url
        self.revision = revision
        self.duration = duration
        self.platform = platform

    @property
    def is_beta(self):
       return self.release == 'beta'


class RunParameters(object):

    example = 'some_param_1=some_value_1,some_param2=some_value_2'

    @classmethod
    def from_string(cls, parameters_str):
        error_msg = 'Expected run parameters in form "%s", but got: %r' % (cls.example, parameters_str)
        parameters = {}
        for pair in parameters_str.split(','):
            l = pair.split('=')
            if len(l) != 2:
                raise ArgumentTypeError(error_msg)
            name, value = l
            parameters[name] = value
        return cls(parameters)

    def __init__(self, parameters):
        self.parameters = parameters  # name -> value, str -> str

    def items(self):
        return self.parameters.items()


class ArtifactType(object):

    def __init__(self, name, content_type, ext=''):
        self.name = name
        self.content_type = content_type
        self.ext = ext
        self.id = None


class ArtifactTypeFactory(object):

    def __init__(self, builtin_types):
        self._name2at = {at.name: at for at in builtin_types}  # type_name -> ArtifactType
        for at in builtin_types:
            setattr(self, at.name, at)

    def __call__(self, name, content_type=None, ext=None):
        at = self._name2at.get(name)
        if at:
            assert ((content_type is None or content_type == at.content_type) and
                    (ext is None or ext == at.ext)) # conflicting content type or ext for same name
            return at
        assert content_type  # required to create new ArtifactType
        at = ArtifactType(name, content_type, ext or '')
        self._name2at[name] = at
        setattr(self, name, at)
        return at


class DbCaptureRepository(object):

    prev_select_mutex = threading.Lock()

    def __init__(self, db_config, build_parameters, run_parameters=None):
        self.db_config = db_config
        self.build_parameters = build_parameters
        self.run_parameters = run_parameters
        self.artifact_type = ArtifactTypeFactory([
            ArtifactType('traceback', 'text/plain', '.txt'),
            ArtifactType('output', 'text/plain', '.txt'),
            ArtifactType('log', 'text/plain', '.log'),
            ArtifactType('core', 'application/octet-stream'),
            ArtifactType('core-traceback', 'text/plain', '.txt'),
            ])
        if 'SQL_DEBUG' in os.environ:
            sql_debug(True)
        models.db.bind('postgres', host=db_config.host, user=db_config.user,
                       password=db_config.password, port=db_config.port)
        models.db.generate_mapping(create_tables=True)
        self.test_run = {}  # test path -> models.Run

    def _select_run_children(self, parent):
        return select(run for run in models.Run if raw_sql("run.path similar to $parent.path || '[^/]+/'"))

    def add_run(self, name=None, parent=None, test=None):
        root_run = None
        if parent:
            parent = models.Run[parent.id]
            root_run = parent.root_run or parent
        run = models.Run(
            root_run=root_run if parent else None,
            name=name or '',
            test=test,
            started_at=datetime_utc_now(),
            outcome='incomplete' if test else '',
            )
        if not parent:
            self._set_paramerers(run)
        flush()
        run.path = '%s%d/' % (parent.path if parent else '', run.id)
        return run

    def _set_paramerers(self, run):
        if self.build_parameters:
            run.build = self.produce_build()
            run.platform = self._produce_build_parameter('platform')
        if self.run_parameters:
            for name, value in self.run_parameters.items():
                param = models.RunParameter.get(name=name)
                if not param:
                    param = models.RunParameter(name=name)
                param_value = models.RunParameterValue(
                    run_parameter=param,
                    run=run,
                    value=value,
                    )

    def _produce_artifact_type(self, artifact_type_rec):
        if artifact_type_rec.id:
            return models.ArtifactType[artifact_type_rec.id]
        at = models.ArtifactType.get(name=artifact_type_rec.name)
        if not at:
            at = models.ArtifactType(
                name=artifact_type_rec.name,
                content_type=artifact_type_rec.content_type,
                ext=artifact_type_rec.ext,
                )
            flush()
        artifact_type_rec.id = at.id
        return at

    def produce_build(self):
        project = self._produce_build_parameter('project')
        branch = self._produce_build_parameter('branch')
        build_num = self._produce_build_parameter('build_num')
        build = models.Build.get(
            project=project,
            branch=branch,
            build_num=build_num)
        if not build:
            build = models.Build(
                project=project,
                branch=branch,
                build_num=build_num,
                version=self._produce_build_parameter('version'))
        for name in BuildParameters.known_parameters:
            if name in ['project', 'branch', 'build_num']: continue
            if name == 'duration_ms':
                name = 'duration'
            value = self._produce_build_parameter(name)
            if value:
                setattr(build, name, value)
        return build

    def _produce_build_parameter(self, name):
        value = getattr(self.build_parameters, name)
        param2model = dict(
            project=models.Project,
            branch=models.Branch,
            cloud_group=models.CloudGroup,
            customization=models.Customization,
            platform=models.Platform,
            )
        model = param2model.get(name)
        if not model:
            if name in ['build_num', 'duration', 'is_incremental']:
                return value
            else:
                return value or ''  # str fields do not accept None
        if not value:
            return None
        rec = model.get(name=value)
        if not rec:
            rec = model(name=value)
        return rec

    def produce_run(self, parent, name):
        run = self._select_run_children(parent).filter(name=name).get()
        if not run:
            run = self.add_run(name, parent)
        return run

    def produce_test(self, test_path, is_leaf):
        test = models.Test.get(path=test_path)
        if test:
            assert test.is_leaf == is_leaf, repr((is_leaf, test_path))
        else:
            test = models.Test(path=test_path, is_leaf=is_leaf)
        return test

    def produce_test_run(self, root_run, test_path_list, is_test=False):
        run = root_run
        # create all parent nodes too
        for path, name, is_leaf in self._iter_path_parents(test_path_list):
            test = self.produce_test(path, is_leaf=is_leaf and is_test)
            parent_run = run
            run = self.test_run.get(path)
            if not run:
                run = self.add_run(name, parent_run, test)
                with self.prev_select_mutex:  # try to avoid supposed ponyorm error
                    run.prev_outcome = self._pick_prev_outcome(run) or ''
                self.test_run[path] = run
        return run

    def _iter_path_parents(self, path_list):
        for i in range(len(path_list)):
            path = '/'.join(path_list[:i+1])
            name = path_list[i]
            is_leaf = i == len(path_list) - 1
            yield (path, name, is_leaf)

    def _pick_prev_outcome(self, this_run):
        if not this_run.root_run or not this_run.root_run.build:
            return None
        prev_run = select(prev_run
                          for prev_run in models.Run
                          for this_build in models.Build
                          for prev_build in models.Build if
                          this_run.root_run.build is this_build and
                          prev_run.root_run.build is prev_build and
                          prev_build.project is this_build.project and
                          prev_build.branch is this_build.branch and
                          prev_build.build_num < this_build.build_num and
                          prev_run.root_run.platform is this_run.root_run.platform and
                          prev_run.test is this_run.test).order_by(desc(1)).first()
        if not prev_run:
            return None
        return prev_run.outcome

    def add_artifact(self, run, short_name, full_name, artifact_type_rec, data, is_error=False):
        assert run
        if not data: return
        at = self._produce_artifact_type(artifact_type_rec)
        if type(data) is unicode:
            data = data.encode('utf-8')
        compressed_data = bz2.compress(data)
        artifact = models.Artifact(
            type=at,
            short_name=short_name,
            full_name=full_name,
            is_error=is_error,
            run=run,
            encoding='bz2',
            data=compressed_data)
        #print '----- added artifact %s for run %s' % (artifact.type, run.path)

    @db_session
    def add_artifact_with_session(self, run, short_name, full_name, artifact_type_rec, data, is_error=False):
        run_reloaded = models.Run[run.id]  # it may belong to different transaction
        self.add_artifact(run_reloaded, short_name, full_name, artifact_type_rec, data, is_error)

    @db_session
    def add_metric_with_session(self, run, metric_name, metric_value):
        assert isinstance(metric_value, (float, int)), repr(metric_value)
        run_reloaded = models.Run[run.id]  # it may belong to different transaction
        metric = models.Metric.get(name=metric_name)
        if not metric:
            metric = models.Metric(name=metric_name)
        metric_value = models.MetricValue(
            metric=metric,
            run=run_reloaded,
            value=metric_value)

    def set_test_outcome(self, parent_run):
        outcome = None
        for run in self._select_run_children(parent_run):
            if run.outcome in [None, 'incomplete']:
                self.set_test_outcome(run)
            if run.outcome == 'failed':
                outcome = run.outcome
            elif not outcome and run.outcome == 'passed':
                outcome = run.outcome
            elif not outcome and run.outcome != 'skipped':
                outcome = run.outcome
        parent_run.outcome = outcome or 'skipped'
