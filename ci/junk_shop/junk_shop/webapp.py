import os
from datetime import datetime, timedelta
import bz2
from flask import Flask, request, render_template, make_response, url_for, redirect
from jinja2 import Markup
from pony.orm import db_session, desc, select, raw_sql, count, sql_debug
from .utils import SimpleNamespace, datetime_utc_now, DbConfig
from . import models

app = Flask(__name__)


DEFAULT_RUN_LIST_PAGE_SIZE = 20


@app.template_filter('format_datetime')
def format_datetime(dt, precise=True):
    if not dt: return dt
    assert isinstance(dt, datetime), repr(dt)
    s = dt.strftime('%Y %b %d')
    if not precise and dt.day < datetime_utc_now().day:
        return Markup(s)
    s += ' <b>' + dt.strftime('%H:%M') + '</b>'
    if precise:
        s += ':' + dt.strftime('%S') + '.%03d' % (dt.microsecond/1000)
    return Markup(s)

@app.template_filter('format_timedelta')
def format_timedelta(d):
    hours, rem = divmod(d.total_seconds(), 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return '%d:%02d:02d' % (hours, minutes, seconds)
    if minutes:
        return '%d:%02d' % (minutes, seconds)
    return '%d.%03d' % (seconds, d.microseconds/1000)


class ArtifactRec(object):

    def __init__(self, artifact):
        self.id = artifact.id
        self.name = artifact.name
        self.is_error = artifact.is_error
        self.is_binary = not artifact.type.content_type.startswith('text/')
        if artifact.type.name not in ['output', 'traceback', 'core']:
            self.name += ' ' + artifact.type.name

class RunNode(object):

    def __init__(self, path_tuple, run):
        self.path_tuple = path_tuple
        self.run = run
        self.artifacts = [ArtifactRec(artifact) for artifact in run.artifacts.order_by(models.Artifact.id)]
        self.children = []  # RunNode list


def load_root_run_node_list(page, page_size, branch=None, platform=None):
    query = select(run for run in models.Run if run.root_run is None)
    if branch:
        query = query.filter(branch=branch)
    if platform:
        query = query.filter(platform=platform)
    for root_run in query.order_by(desc(models.Run.id)).page(page, page_size):
        yield load_run_node_tree(root_run)

def load_run_node_tree(root_run):
    root_node = RunNode((root_run.path.rstrip('/'),), root_run)
    path2node = {root_node.path_tuple: root_node}
    for run in select(run for run in models.Run if run.root_run is root_run):
        path_tuple = tuple(run.path.rstrip('/').split('/'))
        path2node[path_tuple] = RunNode(path_tuple, run)
    for path, node in path2node.items():
        if len(path) == 1: continue
        parent = path2node[path[:-1]]
        parent.children.append(node)
    for node in path2node.values():
        node.children = sorted(node.children, key=lambda node: node.path_tuple)
    return root_node

        
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

@app.route('/run/<int:run_id>')
@db_session
def run(run_id):
    run = models.Run[run_id]
    return render_template(
        'run.html',
        run_name=run.name,
        run_node=load_run_node_tree(run),
        )


def load_branch_row(branch):
    for platform in models.Platform.select():

        def load_last_run(test_path):
            return select(run for run in models.Run
                          if run.test.path==test_path
                          and run.platform==platform
                          and run.branch==branch).order_by(
                              desc(models.Run.id)).first()

        last_build_run = load_last_run('build')
        yield SimpleNamespace(
            started_at=last_build_run.started_at if last_build_run else None,
            build=last_build_run,
            unit=load_last_run('unit'),
            functional=load_last_run('functional'),
            )

def load_branch_table():
    for branch in models.Branch.select():
        yield SimpleNamespace(
            branch_name=branch.name,
            platform_list=list(load_branch_row(branch)),
            )

@app.route('/branch/')
@db_session
def branch_list():
    branch_table = list(load_branch_table())
    platform_list = models.Platform.select()
    return render_template(
        'branch_matrix.html',
        branch_table=branch_table,
        platform_list=platform_list)


# versions must be compared as ints
def parse_version(version_str):
    try:
        return map(int, version_str.split('.'))
    except ValueError:
        return (99999,)  # show invalid versions first

def load_version_list(branch, platform):
    for version in sorted(filter(
            None, select(run.version for run in models.Run
                         if run.branch==branch and run.platform==platform)), key=parse_version, reverse=True):

        def load_run_rec(test_path):
            root_run = select(run for run in models.Run
                              if run.test.path==test_path
                              and run.branch==branch
                              and run.platform==platform
                              and run.version==version
                              ).order_by(desc(models.Run.id)).first()
            if root_run:
                test_count = dict(select((run.outcome, count(run)) for run in models.Run
                                         if run.path.startswith(root_run.path)
                                         and run.test.is_leaf))
            else:
                test_count = None
            return SimpleNamespace(run=root_run, test_count=test_count)

        yield SimpleNamespace(
            version=version,
            build=load_run_rec('build'),
            unit=load_run_rec('unit'),
            functional=load_run_rec('functional'),
            )

@app.route('/branch/<branch_name>/<platform_name>/')
@db_session
def branch_version_list(branch_name, platform_name):
    branch = models.Branch.get(name=branch_name)
    platform = models.Platform.get(name=platform_name)
    return render_template(
        'branch_version_list.html',
        branch_name=branch_name,
        platform_name=platform_name,
        version_list=load_version_list(branch, platform))

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
        'Content-Disposition': 'attachment; filename="%s"' % artifact.name,
        }


def init():
    db_config = DbConfig.from_string(os.environ['DB_CONFIG'])
    # sql_debug(True)
    models.db.bind('postgres', host=db_config.host, user=db_config.user, password=db_config.password)
    models.db.generate_mapping(create_tables=True)

init()
