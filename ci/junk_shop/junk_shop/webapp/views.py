import bz2
from flask import request, render_template, make_response, url_for, redirect, abort
from pony.orm import db_session, desc, select
from ..utils import SimpleNamespace
from .. import models
from .utils import DEFAULT_RUN_LIST_PAGE_SIZE, paginator
from junk_shop.webapp import app
from .run import artifact_disposition, load_root_run_node_list, load_run_node_tree


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
    run_node_list = list(load_root_run_node_list(page, page_size))
    return render_template(
        'run_list.html',
        paginator=paginator(page, rec_count, page_size),
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


# versions must be compared as ints
# unused
def parse_version(version_str):
    try:
        return map(int, version_str.split('.'))
    except ValueError:
        return (99999,)  # show invalid versions first


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
    run_list = list(load_root_run_node_list(page, page_size, branch, platform, version))
    return render_template(
        'branch_platform_version_run_list.html',
        paginator=paginator(page, rec_count, page_size),
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
    headers = {
        'Content-Type': artifact.type.content_type,
        'Content-Disposition': '%s; filename="%s%s"' % (
            artifact_disposition(artifact.type.content_type), artifact.full_name, artifact.type.ext),
        }
    return str(data), headers
