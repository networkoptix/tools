import os
from datetime import datetime, timedelta
from flask import Flask, render_template, make_response, url_for, redirect
from jinja2 import Markup
from pony.orm import db_session, desc, select, raw_sql, count
from .utils import SimpleNamespace, datetime_utc_now, DbConfig
from . import models

app = Flask(__name__)


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
        if artifact.type.name not in ['output', 'traceback']:
            self.name += ' ' + artifact.type.name

class RunNode(object):

    def __init__(self, path_tuple, run):
        self.path_tuple = path_tuple
        self.run = run
        self.artifacts = [ArtifactRec(artifact) for artifact in run.artifacts]
        self.children = set()  # converted to list after loading


def load_root_run_node_list(branch=None, platform=None):
    query = select(run for run in models.Run if run.root_run is None)
    if branch:
        query = query.filter(branch=branch)
    if platform:
        query = query.filter(platform=platform)
    for root_run in query.order_by(desc(models.Run.id)):
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
        parent.children.add(node)
    for node in path2node.values():
        node.children = sorted(node.children, key=lambda node: node.path_tuple)  # now a list
    return root_node

        
@app.route('/')
@db_session
def index():
    return redirect(url_for('run_list'))

@app.route('/run/')
@db_session
def run_list():
    return render_template(
        'run_list.html', run_node_list=load_root_run_node_list())

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
        fun_test = models.Test.get(path='functional')
        last_run = models.Run.select().filter(
            test=fun_test,
            platform=platform,
            branch=branch,
            ).order_by(desc(models.Run.id)).first()
        yield SimpleNamespace(
            started_at=last_run.started_at if last_run else None,
            build=None,
            unit=None,
            functional=last_run,
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
    branch_table = load_branch_table()
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
        functional_run = select(run for run in models.Run
                                if run.test==models.Test.get(path='functional')
                                and run.branch==branch
                                and run.platform==platform
                                and run.version==version
                                ).order_by(desc(models.Run.id)).first()
        test_count = dict(select((run.outcome, count(run)) for run in models.Run
                                 if run.path.startswith(functional_run.path)
                                 and run.test.is_leaf))
        yield SimpleNamespace(
            version=version,
            build=None,
            unit=None,
            functional=SimpleNamespace(run=functional_run, test_count=test_count),
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
    return str(artifact.data), {'Content-Type': 'text/plain'}


def init():
    db_config = DbConfig.from_string(os.environ['DB_CONFIG'])
    models.db.bind('postgres', host=db_config.host, user=db_config.user, password=db_config.password)
    models.db.generate_mapping(create_tables=True)

init()
