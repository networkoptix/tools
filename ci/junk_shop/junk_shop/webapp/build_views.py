from collections import namedtuple
from flask import render_template, abort
from pony.orm import db_session, select, desc, count, exists
from .. import models
from junk_shop.webapp import app
from .artifact import decode_artifact_data
from .build_output_parser import match_output_line


# drop starting unit/ or functional/ part
def make_test_name(run):
    if run.test:
        return '/'.join(run.test.path.split('/')[1:])
    else:
        return run.name


class InterestingTestRun(object):

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


class TestsRun(object):

    def __init__(self, stage):
        self.stage = stage  # 'unit', 'functional'
        self.failed_count = 0
        self.passed_count = 0
        self.run_set = set()  # Run set
        self.run_list = []  # InterestingTestRun list

    def add_run(self, run):
        if run in self.run_set:
            return
        if run.outcome == 'passed' and run.prev_outcome != 'failed':
            return
        if run.outcome == 'failed':
            self.failed_count += 1
        itr = InterestingTestRun(run)
        self.run_list.append(itr)
        self.run_set.add(run)
        return itr


class BuildPageView(object):

    def __init__(self, project_name, branch_name, build_num):
        self.project_name = project_name
        self.branch_name = branch_name
        self.build_num = build_num
        self.build = models.Build.get(lambda build:
            build.project.name == self.project_name and
            build.branch.name == self.branch_name and
            build.build_num == self.build_num)
        if not self.build:
            abort(404)
        self.tests_run_map = {}  # platform -> root_run -> TestsRun
        self.started_at = None

    @staticmethod
    def pick_build_errors(artifact):
        data = decode_artifact_data(artifact)
        errors = []
        for line in data.splitlines():
            severity = match_output_line(line)
            if severity == 'error':
                errors.append(line.decode('utf-8'))
        return errors

    @staticmethod
    def artifact_as_lines(artifact):
        data = decode_artifact_data(artifact)
        return data.splitlines()

    def produce_tests_run(self, root_run):
        self.update_started_at(root_run)
        run_map = self.tests_run_map.setdefault(root_run.platform, {})
        return run_map.setdefault(root_run, TestsRun(root_run.test.path))

    def update_started_at(self, run):
        print self.started_at, run, run.started_at
        if not self.started_at or run.started_at < self.started_at:
            self.started_at = run.started_at  # first run for this build

    def create_leaf_test_runs(self):
        for root_run, run_count in select(
                (root_run, count(run))
                for root_run in models.Run
                for run in models.Run if
                run.root_run is root_run and
                root_run.build is self.build and
                run.test.is_leaf and
                run.outcome == 'passed'):
            tests_run = self.produce_tests_run(root_run)
            tests_run.passed_count = run_count
        for run, root_run in select(
                (run, root_run)
                for run in models.Run
                for root_run in models.Run if
                run.root_run is root_run and
                root_run.build is self.build and
                run.test.is_leaf and
                (run.outcome == 'failed' or run.prev_outcome == 'failed')).order_by(1):
            tests_run = self.produce_tests_run(root_run)
            tests_run.add_run(run)

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
            tests_run = self.produce_tests_run(root_run)
            tests_run.add_run(run)

    def load_build_artifacts(self):
        platform2artifact = {}
        for run, platform, artifact in select(
                (run, run.platform, artifact)
                for run in models.Run
                for artifact in run.artifacts
                if run.build is self.build and
                run.name == 'build' and
                artifact.short_name == 'output'):
            platform2artifact[platform] = artifact
            self.update_started_at(run)
        return platform2artifact

    def load_build_errors(self):
        return {
            platform: self.pick_build_errors(artifact)
            for platform, artifact in select(
                (run.platform, artifact)
                for run in models.Run
                for artifact in run.artifacts
                if run.build is self.build and
                run.name == 'build' and
                run.outcome == 'failed' and
                artifact.short_name == 'output')}

    def load_root_run_errors(self):
        return {
            (platform, run): self.artifact_as_lines(artifact)
            for platform, run, artifact in select(
                (run.platform, run, artifact)
                for run in models.Run
                for artifact in run.artifacts
                if run.build is self.build and
                artifact.short_name == 'errors')}

    # have to load them separately as tracebacks are attached to top-level unit test runs, not to leaf ones
    def load_tracebacks(self):
        traceback_map = {}
        for platform, root_run, run, test, artifact in select(
                (root_run.platform, root_run, run, run.test, artifact)
                for root_run in models.Run
                for run in models.Run
                for artifact in run.artifacts
                if root_run.build is self.build and
                run.root_run is root_run and
                root_run.test.path == 'unit' and
                artifact.type.name == 'traceback'):
            tests_run = self.produce_tests_run(root_run)
            itr = tests_run.add_run(run)
            itr.traceback_list.append(artifact)
        return traceback_map

    def render_template(self):
        repository = self.build.repository_url.split('/')[-1]
        jenkins_build_num = self.build.jenkins_url.rstrip('/').split('/')[-1]
        changeset_list = list(self.build.changesets.order_by(desc(1)))
        platform_list = list(select(run.platform for run in models.Run if run.build is self.build))

        traceback_map = self.load_tracebacks()
        self.create_leaf_test_runs()
        self.create_non_leaf_failed_test_runs()
        platform_to_build_artifact = self.load_build_artifacts()
        build_errors_map = self.load_build_errors()
        root_run_error_map = self.load_root_run_errors()

        return render_template(
            'build.html',
            build=self.build,
            project_name=self.project_name,
            branch_name=self.branch_name,
            started_at=self.started_at,
            repository=repository,
            jenkins_build_num=jenkins_build_num,
            changeset_list=changeset_list,
            platform_list=platform_list,
            platform_to_build_artifact=platform_to_build_artifact,
            build_errors_map=build_errors_map,
            tests_run_map=self.tests_run_map,
            root_run_error_map=root_run_error_map,
            traceback_map=traceback_map,
            )


@app.route('/project/<project_name>/<branch_name>/<int:build_num>')
@db_session
def build(project_name, branch_name, build_num):
    view = BuildPageView(project_name, branch_name, build_num)
    return view.render_template()
