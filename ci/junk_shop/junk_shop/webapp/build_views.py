from flask import render_template
from pony.orm import db_session, select, desc
from .. import models
from junk_shop.webapp import app


@app.route('/project/<project_name>/<branch_name>/<int:build_num>')
@db_session
def build(project_name, branch_name, build_num):
    build = models.Build.get(lambda build:
        build.project.name == project_name and
        build.branch.name == branch_name and
        build.build_num == build_num)
    repository = build.repository_url.split('/')[-1]
    jenkins_build_num = build.jenkins_url.rstrip('/').split('/')[-1]
    changeset_list = list(build.changesets.order_by(desc(1)))
    platform_list = list(select(run.platform for run in models.Run if run.build is build))
    for run, root_run in select(
            (run, run.root_run) for run in models.Run if
            run.root_run.build is build and
            run.test.is_leaf):
        pass
    return render_template(
        'build.html',
        build=build,
        project_name=project_name,
        branch_name=branch_name,
        repository=repository,
        jenkins_build_num=jenkins_build_num,
        changeset_list=changeset_list,
        platform_list=platform_list,
        )
