from flask import request, render_template
from pony.orm import db_session, select, desc, exists
from ..utils import SimpleNamespace
from .. import models
from junk_shop.webapp import app
from .utils import paginator


DEFAULT_BUILD_LIST_PAGE_SIZE = 10


class PlatformRec(object):

    def __init__(self, build, run):
        self.version = build.version
        self.started_at = run.started_at
        self.build = None
        self.unit = None
        self.functional = None

    def set_run(self, run):
        setattr(self, run.test.path, SimpleNamespace(run=run))
        self.started_at = min(filter(None, [self.started_at, run.started_at]))


@app.route('/project/')
@db_session
def project_list():
    latest_build_map = {  # (project, branch) -> last build
        (rec[0], rec[1]) : rec[2] for rec in
        select((build.project, build.branch, max(build.build_num))
               for build in models.Build
               if exists(build.runs))}
    build_num_set = set(latest_build_map.values())  # just to narrow down following select
    project_list = {}  # project -> branch -> build
    platform_map = {}  # (project, branch, platform) -> PlatformRec
    for build, run in select(
            (run.build, run) for run in models.Run
            if run.build.build_num in build_num_set and
            run.test.path in ['build', 'unit', 'functional']).order_by(2):
        if latest_build_map.get((build.project, build.branch)) != build.build_num:
            continue
        project_list.setdefault(build.project, {})[build.branch] = build
        rec = platform_map.setdefault((build.project, build.branch, run.platform), PlatformRec(build, run))
        rec.set_run(run)
    platform_list = models.Platform.select()
    return render_template(
        'project_list.html',
        platform_list=platform_list,
        project_list=project_list,
        platform_map=platform_map,
        )

@app.route('/project/<project_name>/<branch_name>')
@db_session
def branch(project_name, branch_name):
    page = int(request.args.get('page', 1))
    page_size = DEFAULT_BUILD_LIST_PAGE_SIZE
    query = select(
        build for build in models.Build
        if build.project.name == project_name and
           build.branch.name == branch_name)
    rec_count = query.count()
    build_list = list(query.order_by(desc(1)).page(page, page_size))
    build_changesets_map = {}  # build -> changeset list
    for changeset in select(build.changesets for build in models.Build if build in build_list).order_by(desc(1)):
        changeset_list = build_changesets_map.setdefault(changeset.build, [])
        changeset_list.append(changeset)
    platform_map = {}  # (build, platform) -> PlatformRec
    for build, run in select(
            (run.build, run) for run in models.Run
            if run.build in build_list and run.test.path in ['build', 'unit', 'functional']).order_by(2):
        rec = platform_map.setdefault((build, run.platform), PlatformRec(build, run))
        rec.set_run(run)
    scalability_platform_list = list(select(
        run.root_run.platform.name for run in models.Run
        if run.root_run.build.project.name == project_name and run.root_run.build.branch.name == branch_name and
           run.test.path.startswith('functional/scalability_test.py') and run.test.is_leaf and exists(run.metrics)))
    platform_list = list(select(run.platform for run in models.Run if run.build in build_list))
    return render_template(
        'branch.html',
        paginator=paginator(page, rec_count, page_size),
        project_name=project_name,
        branch_name=branch_name,
        platform_list=platform_list,
        build_list=build_list,
        build_changesets_map=build_changesets_map,
        platform_map=platform_map,
        scalability_platform_list=scalability_platform_list,
        )
