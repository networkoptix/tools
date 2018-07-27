from argparse import ArgumentTypeError
import re
import bz2
import logging
import threading
from collections import namedtuple

from cached_property import cached_property
from pony.orm import db_session, commit, flush, select, desc, raw_sql

from .utils import SimpleNamespace, datetime_utc_now, param_to_bool
from . import models

log = logging.getLogger(__name__)


VERSION_REGEX = r'^\d+(\.\d+)+$'
ARTIFACT_SIZE_LIMIT = 512 * 1024*1024


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
        'add_qt_pdb=false',
        'is_incremental=true',
        'jenkins_url=http://la.hdw.mx/jenkins/job/test/16299/'
        'repository_url=ssh://hg@hdw.mx/nx_vms',
        'revision=81510b15f3bc',
        'duration_ms=1234',
        'platform=linux-x64',
        ])
    known_parameters = {
        'project': str,
        'branch': str,
        'version': str,
        'build_num': int,
        'release': str,
        'configuration': str,
        'cloud_group': str,
        'customization': str,
        'add_qt_pdb': bool,
        'is_incremental': bool,
        'jenkins_url': str,
        'repository_url': str,
        'revision': str,
        'duration_ms': int,
        'platform': str,
        }

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
                raise ArgumentTypeError('Unknown build parameter: %r. Known are: %s' % (name, ', '.join(cls.known_parameters.keys())))
            if value == 'null':
                raise ArgumentTypeError('Got null value for %r parameter' % name)
            if name in ['add_qt_pdb', 'is_incremental']:
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
                 release='beta',
                 configuration=None,
                 cloud_group=None,
                 customization=None,
                 add_qt_pdb=None,
                 is_incremental=None,
                 jenkins_url=None,
                 repository_url=None,
                 revision=None,
                 duration=None,
                 platform=None,
                 ):
        assert release in ['release', 'beta'], repr(release)
        assert add_qt_pdb is None or isinstance(add_qt_pdb, bool), repr(add_qt_pdb)
        assert is_incremental is None or isinstance(is_incremental, bool), repr(is_incremental)
        self.project = project
        self.branch = branch
        self.version = version
        self.build_num = build_num
        self.release = release
        self.configuration = configuration
        self.cloud_group = cloud_group
        self.customization = customization
        self.add_qt_pdb = add_qt_pdb
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
            if content_type is not None:
                assert content_type == at.content_type, (
                    'Conflicting content type for %r: was: %r, requested: %r' % (at.name, at.content_type, content_type))
            if ext is not None:
                assert ext == at.ext, (
                    'Conflicting extension for %r: was: %r, requested: %r' % (at.name, at.ext, ext))
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
        db_config.bind(models.db)
        self.test_run = {}  # test path -> models.Run

    def _select_run_children(self, parent):
        return select(
            run
            for run in models.Run
            if raw_sql(
                "run.path similar to $parent.path || '[^/]+/'"  # Original condition, which makes seq scan.
                " and run.root_run = split_part($parent.path, '/', 1)::int"  # Either btree on root_run...
                " and run.path between $parent.path || '0' and $parent.path || 'a'"  # ...or btree on path.
                # TODO: Make field a varchar and add varchar_pattern_ops or add text_pattern_ops.
                ))

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
            run.customization = self._produce_build_parameter('customization')
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
                version=self._produce_build_parameter('version') or '')
        for name, t in BuildParameters.known_parameters.items():
            if name in ['project', 'branch', 'build_num']: continue
            if name == 'duration_ms':
                name = 'duration'
            value = self._produce_build_parameter(name)
            if value is not None:
                t = self._get_parameter_type(name)
                if t is str and value is None:
                    value = ''  # pony str fields do not accept None
                setattr(build, name, value)
        return build

    def _produce_build_parameter(self, name):
        t = self._get_parameter_type(name)
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
            return value
        if not value:
            return None
        log.info('Retrieving %r record for parameter name=%r value=%r...', model, name, value)
        rec = model.get(name=value)
        log.info('Retrieving %r record for parameter name=%r value=%r: done: %r', model, name, value, rec)
        if not rec:
            rec = model(name=value)
        return rec

    def _get_parameter_type(self, name):
        if name == 'duration':
            name = 'duration_ms'
        return BuildParameters.known_parameters[name]

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

    @cached_property
    @db_session
    def _prev_tests_outcomes(self):
        build_count_limit = 10
        project = models.Project.get(name=self.build_parameters.project)
        branch = models.Branch.get(name=self.build_parameters.branch)
        build_set = set(select(
            build for build in models.Build
            if build.build_num < self.build_parameters.build_num
            and build.project==project
            and build.branch==branch)
                            .order_by(desc(models.Build.build_num))[:build_count_limit])
        outcome_dict = {}  # (platform_name, test_path) -> (build_num, outcome)
        for build_num, platform_name, test_path, outcome in select(
                (build.build_num, run.root_run.platform.name, run.test.path, run.outcome) for
                build in models.Build
                for run in models.Run
                if
                build in build_set and
                run.root_run.build is build):
            key = (platform_name, test_path)
            value = outcome_dict.get(key)
            if value:
                num, _ = value
                if num > build_num:
                    continue  # keep most recent build
            outcome_dict[key] = (build_num, outcome)
        return outcome_dict

    def _pick_prev_outcome(self, this_run):
        if not this_run.root_run or not this_run.root_run.build:
            return None
        value = self._prev_tests_outcomes.get((this_run.root_run.platform.name, this_run.test.path))
        if not value:
            return None
        build_num, outcome = value
        return outcome

    def add_artifact(self, run, short_name, full_name, artifact_type_rec, data, is_error=False):
        if not data: return
        if type(data) is unicode:
            data = data.encode('utf-8')
        if len(data) > ARTIFACT_SIZE_LIMIT:
            log.warning('Skip artifact for run=%r: short_name=%r full_name=%r type=%r: size %d exceeded limit %d',
                            run.path, short_name, full_name, artifact_type_rec.name, len(data), ARTIFACT_SIZE_LIMIT)
            return
        at = self._produce_artifact_type(artifact_type_rec)
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
