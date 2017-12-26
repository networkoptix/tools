from collections import namedtuple
from flask import render_template, abort
from pony.orm import db_session, select, count, desc
from junk_shop.webapp import app
from .. import models
from ..build_info import BuildInfoLoader
from .matrix_cell import MatrixCell


class CustomizationRow(object):

    def __init__(self, customization):
        self.customization = customization
        self.platform2cell = {}  # models.Platform -> MatrixCell


# any build with many customization must be shown as matrix
# and build for 'release' project must be shown as matrix even if ordered for a single customization
def is_release_build(build):
    return (build.project.name == 'release' or
            select(count(run.customization) for run in models.Run if run.build is build)[:][0] > 1)

def render_release_build(build):
    customization2row = {}
    for customization, platform, run in select(
            (run.customization, run.platform, run) for run in  models.Run
            if run.build is build and
            run.test.path in ['build', 'unit', 'functional']):
        row = customization2row.setdefault(customization, CustomizationRow(customization))
        cell = row.platform2cell.setdefault(platform, MatrixCell())
        cell.add_run(run)
    customization_list = sorted(customization2row.values(), key=lambda row: row.customization.order_num)
    platform_list = list(select(run.platform for run in models.Run if run.build is build).order_by(models.Platform.order_num))
    changeset_list = list(build.changesets.order_by(desc(1)))
    return render_template(
        'release_build.html',
        build=build,
        changeset_list=changeset_list,
        platform_list=platform_list,
        customization_list=customization_list,
        )

def render_ci_build(build):
    loader = BuildInfoLoader(build)
    build_info = loader.load_build_platform_list()
    return render_template('build.html', **build_info._asdict())

def render_platform_build(build, customization, platform):
    loader = BuildInfoLoader(build, customization, platform)
    build_platform_info = loader.load_build_platform()
    return render_template('platform_build.html', **build_platform_info._asdict())


@app.route('/project/<project_name>/<branch_name>/<int:build_num>')
@db_session
def build(project_name, branch_name, build_num):
    build = models.Build.get(lambda build:
        build.project.name == project_name and
        build.branch.name == branch_name and
        build.build_num == build_num)
    if not build:
        abort(404)
    if is_release_build(build):
        return render_release_build(build)
    else:
        return render_ci_build(build)


@app.route('/project/<project_name>/<branch_name>/<int:build_num>/<customization_name>/<platform_name>')
@db_session
def platform_build(project_name, branch_name, build_num, customization_name, platform_name):
    build = models.Build.get(lambda build:
        build.project.name == project_name and
        build.branch.name == branch_name and
        build.build_num == build_num)
    customization = models.Customization.get(name=customization_name)
    platform = models.Platform.get(name=platform_name)
    if not build or not customization or not platform:
        abort(404)
    return render_platform_build(build, customization, platform)
