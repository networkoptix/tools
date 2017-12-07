from collections import namedtuple
from functools import total_ordering
from pony.orm import select, desc, count, exists
from . import models
from .artifact import decode_artifact_data
from .build_output_parser import match_output_line


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
            artifact.short_name : artifact.id for artifact in
            run.artifacts.filter(lambda artifact: artifact.type.name == 'output')}


# Stage run for a platform - root run for build, unit or functional tests
@total_ordering
class Stage(object):

    def __init__(self, root_run, error_list=None):
        self.root_run = root_run  # models.Run
        self.stage_name = root_run.test.path  # 'build', 'unit' or 'functional'
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
        self._visited_run_set = set()  # Run set, runs we have already added
        self.run_list = []  # TestRun list

    def add_run(self, run):
        if run in self._visited_run_set:
            return
        if run.outcome == 'passed' and run.prev_outcome != 'failed':
            return
        if run.outcome == 'failed':
            self.failed_count += 1
        tr = TestRun(run)
        self.run_list.append(tr)
        self._visited_run_set.add(run)
        return tr


class Platform(object):

    def __init__(self, name, build_artifact=None):
        self.name = name
        self.build_artifact = build_artifact
        self.build_error_list = []
        self.stage_list = []


BuildInfo = namedtuple('BuildInfo', [
    'build',
    'project_name',
    'branch_name',
    'started_at',
    'repository',
    'jenkins_build_num',
    'changeset_list',
    'platform_list',
    'failed_build_platform_list',
    'failed_tests_platform_list',
    ])


class BuildInfoLoader(object):

    def __init__(self, project_name, branch_name, build_num):
        self.project_name = project_name
        self.branch_name = branch_name
        self.build_num = build_num
        self.build = models.Build.get(lambda build:
            build.project.name == self.project_name and
            build.branch.name == self.branch_name and
            build.build_num == self.build_num)
        self.platform_map = {}  # models.Platform -> Platform
        self.stage_map = {}  # models.Run (root run) -> Stage
        self.started_at = None  # minimal started_at field from all Runs
        self.failed_build_platform_set = set()  # platform name set
        self.failed_tests_platform_set = set()

    def produce_platform(self, platform_model, build_artifact=None):
        platform = self.platform_map.get(platform_model)
        if platform:
            if build_artifact:
                platform.build_artifact = build_artifact
        else:
            platform = Platform(platform_model.name, build_artifact)
            self.platform_map[platform_model] = platform
        return platform

    def produce_stage(self, root_run, stage_cls):
        self.update_started_at(root_run)
        platform = self.produce_platform(root_run.platform)
        stage = self.stage_map.get(root_run)
        if not stage:
            stage = stage_cls(root_run)
            platform.stage_list.append(stage)
            self.stage_map[root_run] = stage
        return stage

    def update_started_at(self, run):
        if not self.started_at or run.started_at < self.started_at:
            self.started_at = run.started_at  # this is first run for this build

    def create_leaf_test_runs(self):
        # load 'passed' leaf test run counts
        for root_run, run_count in select(
                (root_run, count(run))
                for root_run in models.Run
                for run in models.Run if
                run.root_run is root_run and
                root_run.build is self.build and
                run.test.is_leaf and
                run.outcome == 'passed'):
            stage = self.produce_stage(root_run, TestsStage)
            stage.passed_count = run_count
        # load 'interesting' leaf test runs
        for run, root_run in select(
                (run, root_run)
                for run in models.Run
                for root_run in models.Run if
                run.root_run is root_run and
                root_run.build is self.build and
                run.test.is_leaf and
                (run.outcome == 'failed' or run.prev_outcome == 'failed')).order_by(1):
            stage = self.produce_stage(root_run, TestsStage)
            stage.add_run(run)
            if run.outcome == 'failed':
                self.failed_tests_platform_set.add(root_run.platform.name)

    # ensure failed runs show up when there is no leafs for them
    def create_non_leaf_failed_test_runs(self):
        for run, root_run in select(
                (run, root_run)
                for root_run in models.Run
                for run in root_run.children if
                root_run.build is self.build and
                run.outcome == 'failed' and
                run.test and
                not exists(child for child in root_run.children if
                               child.path.startswith(run.path) and
                               child is not run)).order_by(1):
            stage = self.produce_stage(root_run, TestsStage)
            stage.add_run(run)
            self.failed_tests_platform_set.add(root_run.platform.name)

    def load_build_artifacts(self):
        platform2artifact = {}
        for run, artifact in select(
                (run, artifact)
                for run in models.Run
                for artifact in run.artifacts
                if run.build is self.build and
                run.name == 'build' and
                artifact.short_name == 'output'):
            self.update_started_at(run)
            platform = self.produce_platform(run.platform, artifact)
            if run.outcome == 'failed':
                platform.build_error_list = list(self.pick_build_errors(artifact))
                self.failed_build_platform_set.add(run.platform.name)

    @classmethod
    def pick_build_errors(cls, artifact):
        for line in cls.artifact_as_lines(artifact):
            severity = match_output_line(line)
            if severity == 'error':
                yield line.decode('utf-8')

    @staticmethod
    def artifact_as_lines(artifact):
        data = decode_artifact_data(artifact)
        return data.splitlines()

    def load_stage_errors(self):
        for root_run, artifact in select(
                (root_run, artifact)
                for root_run in models.Run
                for artifact in root_run.artifacts
                if root_run.build is self.build and
                artifact.short_name == 'errors'):
            stage = self.produce_stage(root_run, Stage)
            stage.error_list = self.artifact_as_lines(artifact)
            self.failed_tests_platform_set.add(root_run.platform.name)

    # have to load them separately as tracebacks are attached to top-level unit test runs, not to leaf ones
    def load_tracebacks(self):
        for root_run, run, artifact in select(
                (root_run, run, artifact)
                for root_run in models.Run
                for run in models.Run
                for artifact in run.artifacts
                if root_run.build is self.build and
                run.root_run is root_run and
                root_run.test.path == 'unit' and
                artifact.type.name == 'traceback'):
            stage = self.produce_stage(root_run, TestsStage)
            tr = stage.add_run(run)
            tr.traceback_list.append(artifact)

    def load_build_info(self):
        repository = self.build.repository_url.split('/')[-1]
        jenkins_build_num = self.build.jenkins_url.rstrip('/').split('/')[-1]
        changeset_list = list(self.build.changesets.order_by(desc(1)))

        self.load_tracebacks()
        self.create_leaf_test_runs()
        self.create_non_leaf_failed_test_runs()
        self.load_build_artifacts()
        self.load_stage_errors()

        platform_list = [value for key, value in sorted(self.platform_map.items())]

        return BuildInfo(
            build=self.build,
            project_name=self.project_name,
            branch_name=self.branch_name,
            started_at=self.started_at,
            repository=repository,
            jenkins_build_num=jenkins_build_num,
            changeset_list=changeset_list,
            platform_list=platform_list,
            failed_build_platform_list=list(self.failed_build_platform_set),
            failed_tests_platform_list=list(self.failed_tests_platform_set),
            )
