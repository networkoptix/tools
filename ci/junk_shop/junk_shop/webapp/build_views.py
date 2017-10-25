from collections import namedtuple
from flask import render_template, abort
from pony.orm import db_session, select, desc, count
from .. import models
from junk_shop.webapp import app
from .artifact import decode_artifact_data
from .build_output_parser import match_output_line


# drop starting unit/ or functional/ part
def make_test_name(test):
    return '/'.join(test.path.split('/')[1:])

class InterestingTestRun(object):

    def __init__(self, run):
        self.run = run  # models.Run
        self.test_name = make_test_name(run.test)
        self.status = self._make_status_title(run.outcome, run.prev_outcome)
        self.succeeded = run.outcome != 'failed'
        self.output_artifact_id = self._pick_output_artifact_id(run)
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

    def _pick_output_artifact_id(self, run):
        artifact = run.artifacts.filter(lambda artifact: artifact.type.name == 'output').first()
        return artifact.id if artifact else None


class TestsRun(object):

    def __init__(self, stage):
        self.stage = stage  # 'unit', 'functional'
        self.failed_count = 0
        self.passed_count = 0
        self.run_list = []

    def add_run(self, run):
        if run.outcome == 'passed' and run.prev_outcome != 'failed':
            return
        if run.outcome == 'failed':
            self.failed_count += 1
        self.run_list.append(InterestingTestRun(run))


def pick_build_errors(artifact):
    data = decode_artifact_data(artifact)
    errors = []
    for line in data.splitlines():
        severity = match_output_line(line)
        if severity == 'error':
            errors.append(line.decode('utf-8'))
    return errors

def artifact_as_lines(artifact):
    data = decode_artifact_data(artifact)
    return data.splitlines()

# have to load them separately as tracebacks are attached to top-level unit test runs, not to leaf ones
def load_tracebacks(build):
    traceback_map = {}
    for platform, root_run, run, test, artifact in select(
            (root_run.platform, root_run, run, run.test, artifact)
            for root_run in models.Run
            for run in models.Run
            for artifact in run.artifacts
            if root_run.build is build and
            run.root_run is root_run and
            root_run.test.path == 'unit' and
            artifact.type.name == 'traceback'):
        test_name = make_test_name(test)
        itr_map = traceback_map.setdefault((platform, root_run), {})  # test_name -> InterestingTestRun
        itr = itr_map.setdefault(test_name, InterestingTestRun(run))
        itr.traceback_list.append(artifact)
    return traceback_map


@app.route('/project/<project_name>/<branch_name>/<int:build_num>')
@db_session
def build(project_name, branch_name, build_num):
    build = models.Build.get(lambda build:
        build.project.name == project_name and
        build.branch.name == branch_name and
        build.build_num == build_num)
    if not build:
        abort(404)
    repository = build.repository_url.split('/')[-1]
    jenkins_build_num = build.jenkins_url.rstrip('/').split('/')[-1]
    changeset_list = list(build.changesets.order_by(desc(1)))
    platform_list = list(select(run.platform for run in models.Run if run.build is build))
    started_at = None
    tests_run_map = {}  # platform -> root_run -> TestsRun

    def produce_tests_run(root_run):
        run_map = tests_run_map.setdefault(root_run.platform, {})
        return run_map.setdefault(root_run, TestsRun(root_run.test.path))

    for root_run, run_count in select(
            (root_run, count(run))
            for root_run in models.Run
            for run in models.Run if
            run.root_run is root_run and
            root_run.build is build and
            run.test.is_leaf and
            run.outcome == 'passed'):
        tests_run = produce_tests_run(root_run)
        tests_run.passed_count = run_count
    for run, root_run in select(
            (run, root_run)
            for run in models.Run
            for root_run in models.Run if
            run.root_run is root_run and
            root_run.build is build and
            run.test.is_leaf and
            (run.outcome == 'failed' or run.prev_outcome == 'failed')).order_by(1):
        tests_run = produce_tests_run(root_run)
        tests_run.add_run(run)
        if not started_at or root_run.started_at < started_at:
            started_at = root_run.started_at  # first run for this build

    platform_to_build_artifact = {
        platform: artifact for platform, artifact in select(
            (run.platform, artifact)
            for run in models.Run
            for artifact in run.artifacts
            if run.build is build and
            run.name == 'build' and
            artifact.short_name == 'output')}
    failed_builds = {
        platform: pick_build_errors(artifact)
        for platform, artifact in select(
            (run.platform, artifact)
            for run in models.Run
            for artifact in run.artifacts
            if run.build is build and
            run.name == 'build' and
            run.outcome == 'failed' and
            artifact.short_name == 'output')}
    error_map = {
        (platform, run): artifact_as_lines(artifact)
        for platform, run, artifact in select(
            (run.platform, run, artifact)
            for run in models.Run
            for artifact in run.artifacts
            if run.build is build and
            artifact.short_name == 'errors')}
    traceback_map = load_tracebacks(build)
    return render_template(
        'build.html',
        build=build,
        project_name=project_name,
        branch_name=branch_name,
        started_at=started_at,
        repository=repository,
        jenkins_build_num=jenkins_build_num,
        changeset_list=changeset_list,
        platform_list=platform_list,
        platform_to_build_artifact=platform_to_build_artifact,
        failed_builds=failed_builds,
        tests_run_map=tests_run_map,
        error_map=error_map,
        traceback_map=traceback_map,
        )
