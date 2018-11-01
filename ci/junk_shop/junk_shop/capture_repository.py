from argparse import ArgumentTypeError
import re
import bz2
import logging
import threading
from collections import namedtuple

from cached_property import cached_property
from pony.orm import db_session, commit, flush, select, desc, raw_sql

from .utils import SimpleNamespace, datetime_utc_now
from . import models

log = logging.getLogger(__name__)


ARTIFACT_SIZE_LIMIT = 128 * 1024*1024


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

    def __init__(
            self, db_config, build_parameters,
            run_parameters=None, run_properties=None):
        self.db_config = db_config
        self.build_parameters = build_parameters
        self.run_parameters = run_parameters
        self.run_properties = run_properties or dict()
        self.artifact_type = ArtifactTypeFactory([
            ArtifactType('traceback', 'text/plain', '.txt'),
            ArtifactType('output', 'text/plain', '.txt'),
            ArtifactType('log', 'text/plain', '.log'),
            ArtifactType('core', 'application/octet-stream'),
            ArtifactType('core-traceback', 'text/plain', '.txt'),
            ArtifactType('cap', 'application/vnd.tcpdump.pcap', '.cap'),
            ArtifactType('json', 'application/json', '.json')
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
            run.description = self._produce_run_property('description')
            run.jenkins_url = self._produce_run_property('jenkins_url')
            run.revision = self._produce_run_property('revision')
            run.kind = self._produce_run_property('kind')
        if self.run_parameters:
            for name, value in self.run_parameters.iteritems():
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
        for name in self.build_parameters:
            if name in ['project', 'branch', 'build_num']:
                continue
            value = self._produce_build_parameter(name)
            if value is not None:
                setattr(build, name, value)
        return build

    def _produce_run_property(self, name):
        value = self.run_properties.get(name, '')
        if name == 'kind':
            model = models.RunKind
            return model.get(name=value) or model(name=value)
        else:
            return value

    def _produce_build_parameter(self, name):
        value = self.build_parameters.get(name)
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
        rec = model.get(name=value)
        if not rec:
            rec = model(name=value)
        return rec

    def produce_run(self, parent, name):
        run = self._select_run_children(parent).filter(name=name).get()
        if not run:
            run = self.add_run(name, parent)
        return run

    def produce_test(self, test_path, is_leaf, description=None):
        test = models.Test.get(path=test_path)
        if test:
            assert test.is_leaf == is_leaf, repr((is_leaf, test_path))
        else:
            test = models.Test(
                path=test_path,
                is_leaf=is_leaf,
                description=description or '')
        return test

    def produce_test_run(self, root_run, test_path_list, is_test=False):
        run = root_run
        # create all parent nodes too
        for path, name, is_leaf in self._iter_path_parents(test_path_list):
            test = self.produce_test(
                path,
                is_leaf=is_leaf and is_test,
                description=None if root_run else self._produce_run_property('test_description'))
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
        project = models.Project.get(name=self.build_parameters['project'])
        branch = models.Branch.get(name=self.build_parameters['branch'])
        build_set = set(select(
            build for build in models.Build
            if build.build_num < self.build_parameters['build_num'] and
            build.project == project and
            build.branch == branch)
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

        def log_skipping(size_description, size):
            log.warning(
                'Skip artifact for run=%r: short_name=%r full_name=%r type=%r: %s %d exceeded limit %d',
                run.path, short_name, full_name, artifact_type_rec.name, size_description, size, ARTIFACT_SIZE_LIMIT)

        if not data:
            return
        if len(data) > ARTIFACT_SIZE_LIMIT:
            log_skipping('raw size', len(data))
            return
        if type(data) is unicode:
            data = data.encode('utf-8')
            if len(data) > ARTIFACT_SIZE_LIMIT:
                log_skipping('utf-8 encoded size', len(data))
                return
        at = self._produce_artifact_type(artifact_type_rec)
        compressed_data = bz2.compress(data)
        if len(compressed_data) > ARTIFACT_SIZE_LIMIT:
            log_skipping('compressed size', len(compressed_data))
            return
        models.Artifact(
            type=at,
            short_name=short_name,
            full_name=full_name,
            is_error=is_error,
            run=run,
            encoding='bz2',
            data=compressed_data)

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
