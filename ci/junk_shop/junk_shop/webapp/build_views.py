from flask import render_template
from pony.orm import db_session, select, desc, count
from .. import models
from junk_shop.webapp import app


class InterestingTestRun(object):

    def __init__(self, run):
        self.run = run
        self.test_name = '/'.join(run.test.path.split('/')[1:])
        self.status = self._make_status_title(run.outcome, run.prev_outcome)
        self.succeeded = run.outcome != 'failed'
        self.output_artifact_id = self._pick_output_artifact_id(run)

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


@app.route('/project/<project_name>/<branch_name>/<int:build_num>')
@db_session
def build(project_name, branch_name, build_num):
    build = models.Build.get(lambda build:
        build.project.name == project_name and
        build.branch.name == branch_name and
        build.build_num == build_num)
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
    platform_to_build_output = {
        platform: artifact_id for platform, artifact_id in select(
            (run.platform, artifact.id)
            for run in models.Run
            for artifact in run.artifacts
            if run.build is build and
            run.name == 'build'
            and artifact.type.name=='output')}
    print platform_to_build_output
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
        platform_to_build_output=platform_to_build_output,
        tests_run_map=tests_run_map,
        )
