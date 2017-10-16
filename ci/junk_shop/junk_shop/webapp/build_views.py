from flask import render_template
from pony.orm import db_session, select, desc
from .. import models
from junk_shop.webapp import app


class InterestingTestRun(object):

    def __init__(self, run):
        self.run = run
        self.test_name = '/'.join(run.test.path.split('/')[1:])
        self.status = run.outcome.capitalize()
        self.succeeded = run.outcome != 'failed'


class TestsRun(object):

    def __init__(self, stage):
        self.stage = stage  # 'unit', 'functional'
        self.failed_count = 0
        self.passed_count = 0
        self.run_list = []

    def add_run(self, run):
        if run.outcome == 'passed':
            self.passed_count += 1
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
    tests_run_map = {}  # platform -> root_run -> TestsRun
    for run, root_run in select(
            (run, run.root_run) for run in models.Run if
            run.root_run.build is build and
            run.test.is_leaf).order_by(1):
        run_map = tests_run_map.setdefault(root_run.platform, {})
        tests_run = run_map.setdefault(root_run, TestsRun(root_run.test.path))
        tests_run.add_run(run)
    return render_template(
        'build.html',
        build=build,
        project_name=project_name,
        branch_name=branch_name,
        repository=repository,
        jenkins_build_num=jenkins_build_num,
        changeset_list=changeset_list,
        platform_list=platform_list,
        tests_run_map=tests_run_map,
        )
