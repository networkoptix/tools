from flask import request, render_template
from pony.orm import db_session, select
from .. import models
from .utils import DEFAULT_RUN_LIST_PAGE_SIZE, paginator, get_or_abort
from junk_shop.webapp import app
from .run import load_root_run_node_list, load_run_node_tree


@app.route('/run/')
@db_session
def run_list():
    page = int(request.args.get('page', 1))
    page_size = DEFAULT_RUN_LIST_PAGE_SIZE
    rec_count, run_node_list = load_root_run_node_list(page, page_size)
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
    run = get_or_abort(models.Run, run_id)
    return render_template(
        'run.html',
        run_name=run.name,
        project_name=run.build.project.name,
        branch_name=run.build.branch.name,
        platform_name=run.platform.name,
        run_version=run.build.version,
        run_id=run.id,
        run_node=load_run_node_tree(run),
        )


# versions must be compared as ints
# unused
def parse_version(version_str):
    try:
        return map(int, version_str.split('.'))
    except ValueError:
        return (99999,)  # show invalid versions first


@app.route('/project/<project_name>/<branch_name>/<platform_name>/<version>/<test_name>/runs')
@db_session
def branch_platform_version_test_run_list(project_name, branch_name, platform_name, version, test_name):
    page = int(request.args.get('page', 1))
    page_size = DEFAULT_RUN_LIST_PAGE_SIZE
    rec_count, run_node_list = load_root_run_node_list(page, page_size, project_name, branch_name, platform_name, version)
    return render_template(
        'branch_platform_version_run_list.html',
        paginator=paginator(page, rec_count, page_size),
        project_name=project_name,
        branch_name=branch_name,
        platform_name=platform_name,
        version=version,
        test_name=test_name,
        run_node_list=run_node_list)
