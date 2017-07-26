import sys
import bz2
from flask import request, render_template, make_response, url_for, redirect, abort
from pony.orm import db_session, desc, select, count
from ..utils import SimpleNamespace
from .. import models
from junk_shop.webapp import app
from .run import load_root_run_node_list, load_run_node_tree


DEFAULT_RUN_LIST_PAGE_SIZE = 20

VERSION_LIST_SQL='''Select version FROM run
WHERE branch = $branch and platform = $platform
GROUP BY version
ORDER BY string_to_array(version, '.')::int[] DESC
LIMIT $limit OFFSET $offset'''



@app.route('/')
@db_session
def index():
    return redirect(url_for('run_list'))


@app.route('/run/')
@db_session
def run_list():
    page = int(request.args.get('page', 1))
    page_size = DEFAULT_RUN_LIST_PAGE_SIZE
    rec_count = select(run for run in models.Run if run.root_run is None).count()
    page_count = (rec_count - 1) / page_size + 1
    run_node_list = list(load_root_run_node_list(page, page_size))
    return render_template(
        'run_list.html',
        current_page=page,
        page_count=page_count,
        run_node_list=run_node_list)

@app.route('/run/<int:run_id>/children')
@db_session
def run_children(run_id):
    run = models.Run[run_id]
    return render_template(
        'run_children.html',
        run_node_list=load_run_node_tree(run).children,
        )


@app.route('/run/<int:run_id>')
@db_session
def run(run_id):
    run = models.Run[run_id]
    return render_template(
        'run.html',
        run_name=run.name,
        run_node=load_run_node_tree(run),
        )


def load_platform_branch_cell(branch, platform):
    if not branch or not platform: abort(404)
    def load_last_run(test_path):
        last_run = select(run for run in models.Run
                          if run.test.path == test_path and
                          run.platform == platform and
                          run.branch == branch).order_by(
                              desc(models.Run.id)).first()

        if last_run:
            test_count = dict(select((run.outcome, count(run)) for run in models.Run
                                     if run.path.startswith(last_run.path) and
                                     run.test.is_leaf))
        else:
            test_count = None
        return SimpleNamespace(run=last_run, test_count=test_count)

    last_build = load_last_run('build')
    return SimpleNamespace(
            platform_name=platform.name,
            branch_name=branch.name,
            started_at=last_build.run.started_at if last_build.run else None,
            build=last_build,
            unit=load_last_run('unit'),
            functional=load_last_run('functional'),
            )


def load_branch_row(branch):
    for platform in models.Platform.select():
        yield load_platform_branch_cell(branch, platform)


def load_platform_row(platform):
    for branch in models.Branch.select():
        yield load_platform_branch_cell(branch, platform)


def load_branch_table():
    for branch in models.Branch.select():
        yield SimpleNamespace(
            branch_name=branch.name,
            platform_list=list(load_branch_row(branch)),
            )


@app.route('/branch/')
@db_session
def matrix():
    branch_table = list(load_branch_table())
    platform_list = models.Platform.select()
    return render_template(
        'matrix.html',
        branch_table=branch_table,
        platform_list=platform_list)


# versions must be compared as ints
def parse_version(version_str):
    try:
        return map(int, version_str.split('.'))
    except ValueError:
        return (99999,)  # show invalid versions first


@app.route('/branch/<branch_name>')
@db_session
def branch_platform_list(branch_name):
    branch = models.Branch.get(name=branch_name)
    return render_template(
        'branch_platform_list.html',
        branch_name=branch_name,
        platform_list=list(load_branch_row(branch)))


@app.route('/platform/<platform_name>')
@db_session
def platform_branch_list(platform_name):
    platform = models.Platform.get(name=platform_name)
    return render_template(
        'platform_branch_list.html',
        platform_name=platform_name,
        branch_list=list(load_platform_row(platform)))


def load_version_list(page, page_size, branch, platform):
    versions = models.db.select(
        VERSION_LIST_SQL,
        {'platform': platform.id, 'branch': branch.id,
         'limit': page_size, 'offset': (page - 1) * page_size})
    for version in versions:

        def load_run_rec(test_path):
            root_run = select(run for run in models.Run
                              if run.test.path == test_path and
                              run.branch == branch and
                              run.platform == platform and
                              run.version == version
                              ).order_by(desc(models.Run.id)).first()
            if root_run:
                test_count = dict(select((run.outcome, count(run)) for run in models.Run
                                         if run.path.startswith(root_run.path) and
                                         run.test.is_leaf))
            else:
                test_count = None
            return SimpleNamespace(run=root_run, test_count=test_count)

        last_build = load_run_rec('build')
        yield SimpleNamespace(
            version=version,
            started_at=last_build.run.started_at if last_build.run else None,
            build=last_build,
            unit=load_run_rec('unit'),
            functional=load_run_rec('functional'),
            )


@app.route('/branch/<branch_name>/<platform_name>/')
@db_session
def branch_platform_version_list(branch_name, platform_name):
    branch = models.Branch.get(name=branch_name)
    platform = models.Platform.get(name=platform_name)
    page = int(request.args.get('page', 1))
    page_size = DEFAULT_RUN_LIST_PAGE_SIZE
    version_list=load_version_list(page, page_size, branch, platform)
    rec_count = select(run.version for run in models.Run
                       if run.branch == branch and
                       run.platform == platform).count()
    page_count = (rec_count - 1) / page_size + 1
    if branch and platform:
        version_list = load_version_list(page, page_size, branch, platform)
    else:
        version_list = []
    return render_template(
        'branch_platform_version_list.html',
        current_page=page,
        page_count=page_count,
        branch_name=branch_name,
        platform_name=platform_name,
        version_list=version_list)


@app.route('/version/<branch_name>/<platform_name>/<version>')
@db_session
def branch_platform_version_run_list(branch_name, platform_name, version):
    branch = models.Branch.get(name=branch_name)
    platform = models.Platform.get(name=platform_name)
    page = int(request.args.get('page', 1))
    page_size = DEFAULT_RUN_LIST_PAGE_SIZE
    rec_count = select(run for run in models.Run
                       if run.root_run is None and
                       run.branch == branch and
                       run.platform == platform and
                       run.version == version).count()
    page_count = (rec_count - 1) / page_size + 1
    run_list = list(load_root_run_node_list(page, page_size, branch, platform, version))
    return render_template(
        'branch_platform_version_run_list.html',
        current_page=page,
        page_count=page_count,
        branch_name=branch_name,
        platform_name=platform_name,
        version=version,
        run_node_list=run_list)


@app.route('/artifact/<int:artifact_id>')
@db_session
def get_artifact(artifact_id):
    artifact = models.Artifact.get(id=artifact_id)
    if artifact.encoding == 'bz2':
        data = bz2.decompress(artifact.data)
    elif not artifact.encoding:
        data = artifact.data
    else:
        assert False, 'Unknown artifact encoding: %r' % artifact.encoding
    return str(data), {
        'Content-Type': artifact.type.content_type,
        'Content-Disposition': 'attachment; filename="%s%s"' % (artifact.name, artifact.type.ext),
        }
