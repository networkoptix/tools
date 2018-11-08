import logging
from collections import namedtuple
from functools import total_ordering

from pony.orm import select, desc, count, exists

from . import models
from .artifact import decode_artifact_data

log = logging.getLogger(__name__)


BUILD_STAGE = 'build'
UNIT_TEST_STAGE = 'unit'
SCALABILITY_STAGE = 'scalability'


# drop starting unit/ or functional/ part
def make_test_name(run):
    if run.test:
        return '/'.join(run.test.path.split('/')[1:])
    else:
        return run.name


# single test run, which is 'interesting' for us: failed or fixed
class TestRun(object):

    def __init__(self, run):
        self.run = run  # models.Run
        self.test_name = make_test_name(run)
        self.status = self._make_status_title(run.outcome, run.prev_outcome)
        self.succeeded = run.outcome != 'failed'
        self.output_artifacts = self._pick_output_artifacts(run)
        self.traceback_list = []  # models.Artifact list - coredump tracebacks

    def _make_status_title(self, outcome, prev_outcome):
        title_map = {
            ('passed', 'passed'): 'Still passing',
            ('passed', 'failed'): 'New pass',
            ('passed', ''): 'Passed',
            ('failed', 'failed'): 'Still failing',
            ('failed', 'passed'): 'New fail',
            ('failed', ''): 'Failed',
            }
        return title_map.get((outcome, prev_outcome), '')

    def _pick_output_artifacts(self, run):
        return {
            artifact.short_name: artifact.id for artifact in
            run.artifacts.filter(lambda artifact: artifact.type.name == 'output')}


# Stage run for a platform - root run for build, unit or functional tests
@total_ordering
class Stage(object):

    def __init__(self, root_run, error_list=None):
        self.root_run = root_run  # models.Run
        self.stage_name = root_run.name  # 'build', 'unit', 'functional' or 'scalability'
        self.error_list = error_list

    def __eq__(self, other):
        return self.root_run == other.root_run

    def __lt__(self, other):
        return self.root_run < other.root_run


# Tests batch run - for one platform, for one stage (unit or functional tests)
class TestsStage(Stage):

    def __init__(self, root_run, error_list=None):
        Stage.__init__(self, root_run, error_list)
        self.failed_count = 0
        self.passed_count = 0
        self._visited_run_set = {}  # models.Run -> TestRun, runs we have already added
        self.run_list = []  # TestRun list
        if self.stage_name == SCALABILITY_STAGE:
            self.run_parameters = {p.run_parameter.name: p.value for p in root_run.run_parameters}
        else:
            self.run_parameters = {}

    def add_run(self, run):
        tr = self._visited_run_set.get(run)
        if tr:
            return tr
        if run.outcome == 'passed' and run.prev_outcome != 'failed':
            return None
        if run.outcome == 'failed':
            self.failed_count += 1
        tr = TestRun(run)
        self.run_list.append(tr)
        self._visited_run_set[run] = tr
        return tr


class Platform(object):

    def __init__(self, name, order_num):
        self.name = name
        self.order_num = order_num
        self.build_run = None
        self.build_artifact = None
        self.build_error_list = []  # errors parsed from build output
        self.error_list = []  # errors generated by ci scripts
        self.stage_list = []

    @property
    def succeeded(self):
        return self.build_run.outcome == 'passed'


class BuildInfo(namedtuple('BuildInfo', [
    'build',
    'started_at',
    'changeset_list',
    'platform_list',
    'failed_build_platform_list',
    'failed_tests_platform_list',
    'failed_test_list',
])):

    @property
    def has_failed_builds(self):
        return bool(self.failed_build_platform_list)

    @property
    def has_succeeded_builds(self):
        return set(self.failed_build_platform_list) < set(self.platform_list)

    @property
    def has_failed_tests(self):
        bool(self.failed_tests_platform_list)

    @property
    def changeset_email_list(self):
        return set('{} <{}>'.format(changeset.user, changeset.email)
                   for changeset in self.changeset_list)


PlatformBuildInfo = namedtuple('PlatformBuildInfo', [
    'build',
    'started_at',
    'customization',
    'platform',
    ])


class BuildInfoLoader(object):

    @classmethod
    def from_project_branch_num(cls, project_name, branch_name, build_num):
        build = models.Build.get(lambda build:
                                 build.project.name == project_name and
                                 build.branch.name == branch_name and
                                 build.build_num == build_num)
        return cls(build)

    @classmethod
    def for_full_build(cls, build):
        return cls(build, is_full_build_mode=True)

    @classmethod
    def for_build_customzation_platform(cls, build, customization, platform):
        return cls(build, customization, platform, is_full_build_mode=False)

    @classmethod
    def for_stage_list(cls, build, customization, platform, stage):
        return cls(build, customization, platform, stage, is_full_build_mode=False)

    def __init__(
            self, build, customization=None,
            platform=None, stage=None, is_full_build_mode=True):
        self.build = build
        self.customization = customization
        self.platform = platform
        self.stage = stage
        self.is_full_build_mode = is_full_build_mode
        self.platform_map = {}  # models.Platform -> Platform
        self.stage_map = {}  # models.Run (root run) -> Stage
        self.started_at = None  # minimal started_at field from all Runs
        self.failed_build_platform_set = set()  # platform name set
        self.failed_tests_platform_set = set()
        self.failed_test_set = set()  # failed test list from all platforms

    def _is_run_wanted(self, root_run):
        if self.is_full_build_mode:
            return True
        return root_run.customization is self.customization and root_run.platform is self.platform

    def _produce_platform(self, platform_model):
        platform = self.platform_map.get(platform_model)
        if not platform:
            platform = Platform(platform_model.name, platform_model.order_num)
            self.platform_map[platform_model] = platform
        return platform

    def _produce_stage(self, root_run, stage_cls):
        if not root_run.platform:
            log.error('root_run#%s platform is not defined', root_run.id)
            return None
        self._update_started_at(root_run)
        platform = self._produce_platform(root_run.platform)
        stage = self.stage_map.get(root_run)
        if not stage:
            stage = stage_cls(root_run)
            if root_run.name == (self.stage or root_run.name):
                platform.stage_list.append(stage)
            self.stage_map[root_run] = stage
        return stage

    def _update_started_at(self, run):
        if not self.started_at or run.started_at < self.started_at:
            self.started_at = run.started_at  # this is first run for this build

    def _create_leaf_test_runs(self):
        # load 'passed' leaf test run counts
        for root_run, run_count in select(
                (root_run, count(run))
                for root_run in models.Run
                for run in models.Run if
                run.root_run is root_run and
                root_run.build is self.build and
                run.test.is_leaf and
                run.outcome == 'passed'):
            if not self._is_run_wanted(root_run):
                continue
            stage = self._produce_stage(root_run, TestsStage)
            if not stage:
                continue
            stage.passed_count = run_count
        # load 'interesting' leaf test runs
        for run, test, root_run in select(
                (run, run.test, root_run)
                for run in models.Run
                for root_run in models.Run if
                run.root_run is root_run and
                root_run.build is self.build and
                run.test.is_leaf and
                (run.outcome == 'failed' or run.prev_outcome == 'failed')).order_by(1):
            if not self._is_run_wanted(root_run):
                continue
            stage = self._produce_stage(root_run, TestsStage)
            if not stage:
                continue
            stage.add_run(run)
            if run.outcome == 'failed':
                self.failed_tests_platform_set.add(root_run.platform.name)
                self.failed_test_set.add(test.path)

    # ensure failed runs show up when there is no leafs for them
    def _create_non_leaf_failed_test_runs(self):
        for run, test, root_run in select(
                (run, run.test, root_run)
                for root_run in models.Run
                for run in root_run.children if
                root_run.build is self.build and
                run.outcome == 'failed' and
                run.test and
                not exists(child for child in root_run.children if
                               child.path.startswith(run.path) and
                               child is not run and
                               child.outcome == 'failed')).order_by(1):
            if not self._is_run_wanted(root_run):
                continue
            stage = self._produce_stage(root_run, TestsStage)
            stage.add_run(run)
            self.failed_tests_platform_set.add(root_run.platform.name)
            self.failed_test_set.add(test.path)

    # ensure failed root runs show up when there is no failed leafs for them
    def _create_root_failed_test_runs(self):
        for run, test in select(
                (run, run.test)
                for run in models.Run if
                run.build is self.build and
                run.outcome == 'failed' and
                run.test and not run.test.is_leaf and
                not exists(child for child in run.children if
                               child.path.startswith(run.path) and
                               child is not run and
                               child.outcome == 'failed')).order_by(1):
            if not self._is_run_wanted(run):
                continue
            stage = self._produce_stage(run, TestsStage)
            stage.add_run(run)
            self.failed_tests_platform_set.add(run.platform.name)
            self.failed_test_set.add(test.path)

    def _load_build_artifacts(self):
        for run, artifact in select(
                (run, artifact)
                for run in models.Run
                for artifact in run.artifacts
                if run.build is self.build and
                run.name == BUILD_STAGE):
            if not self._is_run_wanted(run):
                continue
            self._update_started_at(run)
            platform = self._produce_platform(run.platform)
            platform.build_run = run
            if artifact.short_name == 'output':
                platform.build_artifact = artifact
            if artifact.short_name == 'errors':
                platform.error_list = self._artifact_as_lines(artifact)
            if artifact.short_name == 'build-errors':
                platform.build_error_list = self._artifact_as_lines(artifact)
            if run.outcome == 'failed':
                self.failed_build_platform_set.add(run.platform.name)

    @staticmethod
    def _artifact_as_lines(artifact):
        data = decode_artifact_data(artifact)
        return data.decode('utf-8').splitlines()

    def _load_test_stage_errors(self):
        for root_run, artifact in select(
                (root_run, artifact)
                for root_run in models.Run
                for artifact in root_run.artifacts
                if root_run.build is self.build and
                root_run.name != BUILD_STAGE and
                artifact.short_name == 'errors'):
            if not self._is_run_wanted(root_run):
                continue
            stage = self._produce_stage(root_run, Stage)
            stage.error_list = self._artifact_as_lines(artifact)
            self.failed_tests_platform_set.add(root_run.platform.name)

    # have to load them separately as tracebacks are attached to top-level unit test runs, not to leaf ones
    def _load_tracebacks(self):
        for root_run, run, artifact in select(
                (root_run, run, artifact)
                for root_run in models.Run
                for run in models.Run
                for artifact in run.artifacts
                if root_run.build is self.build and
                run.root_run is root_run and
                root_run.test.path == UNIT_TEST_STAGE and
                artifact.type.name == 'traceback'):
            if not self._is_run_wanted(root_run):
                continue
            stage = self._produce_stage(root_run, TestsStage)
            tr = stage.add_run(run)
            if tr:
                tr.traceback_list.append(artifact)

    def _load_build_data(self):
        self._load_tracebacks()
        self._create_leaf_test_runs()
        self._create_non_leaf_failed_test_runs()
        self._create_root_failed_test_runs()
        if (self.stage or BUILD_STAGE) == BUILD_STAGE:
            self._load_build_artifacts()
        self._load_test_stage_errors()

    def load_build_platform_list(self):
        self._load_build_data()

        changeset_list = list(self.build.changesets.order_by(desc(1)))
        platform_list = [value for key, value in sorted(
            self.platform_map.items(),
            key=lambda (key, value): value.order_num)]

        return BuildInfo(
            build=self.build,
            started_at=self.started_at,
            changeset_list=changeset_list,
            platform_list=platform_list,
            failed_build_platform_list=list(self.failed_build_platform_set),
            failed_tests_platform_list=list(self.failed_tests_platform_set),
            failed_test_list=list(self.failed_test_set),
            )

    def load_build_platform(self):
        assert not self.is_full_build_mode  # this method intended only for particular customization/platform of a build
        self._load_build_data()

        if not self.platform_map:
            return None
        assert len(self.platform_map) == 1, repr(self.platform_map)
        platform = self.platform_map.popitem()[1]

        return PlatformBuildInfo(
            build=self.build,
            started_at=self.started_at,
            customization=self.customization,
            platform=platform,
            )
