import os
from datetime import datetime, timedelta
import bz2
from flask import Flask, request, render_template, make_response, url_for, redirect
from jinja2 import Markup
from pony.orm import db_session, desc, select, raw_sql, count, exists, sql_debug
from .utils import SimpleNamespace, datetime_utc_now, DbConfig
from . import models

app = Flask(__name__)


DEFAULT_RUN_LIST_PAGE_SIZE = 20

VERSION_LIST_SQL='''Select version FROM run
WHERE branch = $branch and platform = $platform
GROUP BY version
ORDER BY string_to_array(version, '.')::int[] DESC
LIMIT $limit OFFSET $offset'''


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

    def __init__(self, artifact_id, artifact_name, is_error, type_name, content_type):
        self.id = artifact_id
        self.name = artifact_name
        self.is_error = is_error
        self.is_binary = not content_type.startswith('text/')
        if type_name not in ['output', 'traceback', 'core']:
            self.name += ' ' + type_name


class RunNode(object):

    def __init__(self, path_tuple, run, artifacts=None, lazy=False, has_children=False):
        self.path_tuple = path_tuple
        self.run = run
        self.artifacts = artifacts or []
        self.children = []  # RunNode list
        self.lazy = lazy  # children must by retrieved using ajax if True
        self._has_children = has_children

    @property
    def has_children(self):
        return self.children or self._has_children


def load_artifacts(root_run_list):
    run_id2artifacts = {}  # Run -> ArtifactRec list
    for run_id, artifact_id, artifact_name, is_error, type_name, content_type in select(
            (run.id, artifact.id, artifact.name, artifact.is_error, artifact.type.name, artifact.type.content_type)
            for artifact in models.Artifact
            for run in models.Run
            if (run.root_run in root_run_list or run in root_run_list) and artifact.run == run).order_by(2):
        rec = ArtifactRec(artifact_id, artifact_name, is_error, type_name, content_type)
        run_id2artifacts.setdefault(run_id, []).append(rec)
    return run_id2artifacts

def load_root_run_node_list(page, page_size, branch=None, platform=None, version=None):
    query = select(run for run in models.Run if run.root_run is None)
    if branch:
        query = query.filter(branch=branch)
    if platform:
        query = query.filter(platform=platform)
    if version:
        query = query.filter(version=version)
    root_run_list = query.order_by(desc(models.Run.id)).page(page, page_size)
    run_id2artifacts = load_artifacts(root_run_list)
    run_has_children = dict(select((run.id, exists(run.children)) for run in models.Run if run in root_run_list))
    return [RunNode((run.path.rstrip('/'),), run, run_id2artifacts.get(run.id),
                    lazy=True, has_children=run_has_children[run.id])
                    for run in root_run_list]

def load_run_node_tree(root_run):
    run_id2artifacts = load_artifacts([root_run])
    root_node = RunNode((root_run.path.rstrip('/'),), root_run, run_id2artifacts.get(root_run.id))
    path2node = {root_node.path_tuple: root_node}
    for run in select(run for run in models.Run if run.root_run is root_run):
        path_tuple = tuple(run.path.rstrip('/').split('/'))
        path2node[path_tuple] = RunNode(path_tuple, run, run_id2artifacts.get(run.id))
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
    return render_template(
        'branch_platform_version_list.html',
        current_page=page,
        page_count=page_count,
        branch_name=branch_name,
        platform_name=platform_name,
        version_list=load_version_list(page, page_size, branch, platform))


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


def init():
    db_config = DbConfig.from_string(os.environ['DB_CONFIG'])
    if 'SQL_DEBUG' in os.environ:
        sql_debug(True)
    models.db.bind('postgres', host=db_config.host, user=db_config.user, password=db_config.password)
    models.db.generate_mapping(create_tables=True)

init()
