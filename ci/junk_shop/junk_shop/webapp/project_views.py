from flask import request, render_template
from pony.orm import db_session, select, desc, exists
from .. import models
from junk_shop.webapp import app
from .utils import paginator, DEFAULT_BUILD_LIST_PAGE_SIZE
from .matrix_cell import MatrixCell


@app.route('/project/')
@db_session
def project_list():
    latest_build_map = {  # (project, branch) -> last build
        (rec[0], rec[1]): rec[2] for rec in
        select((build.project, build.branch, max(build.build_num))
               for build in models.Build
               if exists(build.runs)
               and build.branch.is_active)}
    build_num_set = set(latest_build_map.values())  # just to narrow down following select
    project_map = {}  # project -> branch set
    branch_map = {}  # (project, branch) -> build
    platform_map = {}  # (project, branch, platform) -> MatrixCell
    for build, run in select(
            (run.build, run) for run in models.Run
            if run.build.branch.is_active and
            run.build.build_num in build_num_set and
            run.test.path in ['build', 'unit', 'functional']).order_by(2):
        if latest_build_map.get((build.project, build.branch)) != build.build_num:
            continue
        project_map.setdefault(build.project, set()).add(build.branch)
        branch_map[(build.project, build.branch)] = build
        cell = platform_map.setdefault((build.project, build.branch, run.platform), MatrixCell())
        cell.add_run(run)
    platform_list = models.Platform.select().order_by(models.Platform.order_num)
    ordered_project_list = models.Project.select().order_by(models.Project.order_num)
    ordered_branch_list = models.Branch.select().order_by(models.Branch.order_num)
    project_list = [project for project in ordered_project_list if project in project_map]
    project_branch_list = {
        project: [branch for branch in ordered_branch_list if branch in project_map[project]]
        for project in project_list}
    return render_template(
        'project_list.html',
        platform_list=platform_list,
        project_list=project_list,
        project_branch_list=project_branch_list,
        branch_map=branch_map,
        platform_map=platform_map,
        )


@app.route('/project/<project_name>/<branch_name>')
@db_session
def branch(project_name, branch_name):
    page = int(request.args.get('page', 1))
    page_size = DEFAULT_BUILD_LIST_PAGE_SIZE
    query = select(
        (build.build_num, build) for build in models.Build
        if build.project.name == project_name and
        build.branch.name == branch_name)
    rec_count = query.count()
    build_list = [build for build_num, build in query.order_by(desc(1)).page(page, page_size)]
    build_changesets_map = {}  # build -> changeset list
    for changeset in select(build.changesets for build in models.Build if build in build_list).order_by(desc(1)):
        changeset_list = build_changesets_map.setdefault(changeset.build, [])
        changeset_list.append(changeset)
    platform_map = {}  # (build, platform) -> MatrixCell
    for build, run in select(
            (run.build, run) for run in models.Run
            if run.build in build_list and run.test.path in ['build', 'unit', 'functional']).order_by(2):
        cell = platform_map.setdefault((build, run.platform), MatrixCell())
        cell.add_run(run)
    scalability_platform_list = list(select(
        run.root_run.platform.name for run in models.Run
        if run.root_run.build.project.name == project_name and
        run.root_run.build.branch.name == branch_name and
        run.test.path.startswith('functional/scalability_test.py') and
        run.test.is_leaf and exists(run.metrics)))
    platform_list = list(select(run.platform for run in models.Run if run.build in build_list).order_by(models.Platform.order_num))
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
