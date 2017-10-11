from flask import request, render_template
from pony.orm import db_session, desc, select, count, exists
from ..utils import SimpleNamespace
from .. import models
from junk_shop.webapp import app


class TestsRec(object):

    def __init__(self, run, test_count):
        self.run = run  # models.Run
        self.test_count = test_count  # outcome:str -> count:int


class BranchPlatformRec(object):

    def __init__(self, branch_name, platform_name, started_at, build, unit, functional):
        self.branch_name = branch_name
        self.platform_name = platform_name
        self.started_at = started_at
        self.build = build
        self.unit = unit
        self.functional = functional
        self.has_scalability = False


def load_platform_branch_rec(branch_name, platform_name, load_counts=True):
    def load_last_run(test_path):
        last_run = select(run for run in models.Run
                          if run.test.path == test_path and
                          run.platform.name == platform_name and
                          run.branch.name == branch_name).order_by(
                              desc(models.Run.id)).first()

        if load_counts and last_run:
            test_count = dict(select((run.outcome, count(run)) for run in models.Run
                                     if run.path.startswith(last_run.path) and
                                     run.test.is_leaf))
        else:
            test_count = None
        return TestsRec(run=last_run, test_count=test_count)

    last_build = load_last_run('build')
    return BranchPlatformRec(
            branch_name=branch_name,
            platform_name=platform_name,
            started_at=last_build.run.started_at if last_build.run else None,
            build=last_build,
            unit=load_last_run('unit'),
            functional=load_last_run('functional'),
            )


def load_branch_row(branch_name, load_counts=True):
    for platform in models.Platform.select():
        yield load_platform_branch_rec(branch_name, platform.name, load_counts)


def load_has_scalability_flag(branch_name, platform_list):
    platform2rec = {rec.platform_name: rec for rec in platform_list}
    for platform_name in select(
            run.root_run.platform.name for run in models.Run
            if run.root_run.branch.name == branch_name and
               run.test.path.startswith('functional/scalability_test.py') and
               run.test.is_leaf and
               exists(run.metrics)):
        platform2rec[platform_name].has_scalability = True


def _branch_list(project_name, branch_name):
    platform_list = list(load_branch_row(branch_name))
    load_has_scalability_flag(branch_name, platform_list)
    return render_template(
        'branch_platform_list.html',
        branch_name=branch_name,
        platform_list=platform_list)


def load_platform_row(platform_name):
    for branch in models.Branch.select():
        yield load_platform_branch_rec(branch.name, platform_name)

@app.route('/platform/<platform_name>')
@db_session
def platform_branch_list(platform_name):
    return render_template(
        'platform_branch_list.html',
        platform_name=platform_name,
        branch_list=list(load_platform_row(platform_name)))
