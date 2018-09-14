from collections import namedtuple
from flask import render_template, abort, request
from pony.orm import db_session, select, count, desc, exists
from junk_shop.webapp import app
from .. import models
from ..build_info import BuildInfoLoader
from .matrix_cell import MatrixCell
from .utils import paginator_from_list


class CustomizationRow(object):

    def __init__(self, customization):
        self.customization = customization
        self.platform2cell = {}  # models.Platform -> MatrixCell


class WebadminPhonyCustomization(object):

    def __init__(self):
        self.name = ''
        self.order_num = 0  # must appear first


# any build with many customization must be shown as matrix
# and build for 'release' project must be shown as matrix even if ordered for a single customization
def is_release_build(build):
    return (build.project.name == 'release' or
            select(count(run.customization) for run in models.Run if run.build is build)[:][0] > 1)


def render_release_build(build):
    customization2row = {}
    for customization, platform, run in select(
            (run.customization, run.platform, run) for run in models.Run
            if run.build is build and
            run.test.path in ['build', 'unit', 'functional']):
        if not customization:
            customization = WebadminPhonyCustomization()
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


def load_scalability_platform_set(build):
    return set(select(
        run.root_run.platform.name for run in models.Run
        if run.root_run.build is build and (
                run.test.path.startswith('functional/tests/scalability_test.py') or
                run.test.path.startswith('functional/scalability_test.py')) and
        run.test.is_leaf and exists(run.metrics)))


def render_ci_build(build):
    loader = BuildInfoLoader.for_full_build(build)
    build_info = loader.load_build_platform_list()
    scalability_platform_set = load_scalability_platform_set(build)
    return render_template('build.html',
                           scalability_platform_set=scalability_platform_set,
                           **build_info._asdict())


def render_platform_build(build, customization, platform, paginator):
    loader = BuildInfoLoader.for_build_customzation_platform(build, customization, platform)
    build_platform_info = loader.load_build_platform()
    if not build_platform_info:
        abort(404)
    scalability_platform_set = load_scalability_platform_set(build)
    return render_template(
        'platform_build.html',
        paginator=paginator,
        scalability_platform_set=scalability_platform_set,
        **build_platform_info._asdict())


@app.route('/project/<project_name>/<branch_name>/<int:build_num>')
@db_session
def build(project_name, branch_name, build_num):
    build = models.Build.get(
        lambda build:
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
    build = models.Build.get(
        lambda build:
            build.project.name == project_name and
            build.branch.name == branch_name and
            build.build_num == build_num)
    platform = models.Platform.get(name=platform_name)
    if not build or not platform:
        abort(404)
    if customization_name == 'none':
        customization = None
    else:
        customization = models.Customization.get(name=customization_name)
        if not customization:
            abort(404)

    query = select(
        build for build in models.Build
        if build.project.name == project_name and
        build.branch.name == branch_name and
        exists(run for run in build.runs
               if run.platform.name == platform_name and
               run.customization.name == customization_name))

    build_list = [b.build_num for b in query.order_by(desc(models.Build.build_num))]

    return render_platform_build(
        build, customization, platform,
        paginator=paginator_from_list(build_num, build_list))
