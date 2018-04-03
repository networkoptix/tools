from pony.orm import db_session, select
import click

from junk_shop.webapp import app
from .. import models


@app.cli.command()
@db_session
def list_projects():
    '''List projects'''
    for project in models.Project.select().order_by(models.Project.id):
        click.echo(project.name)

@app.cli.command()
@db_session
def list_branches():
    '''List Branches'''
    for branch in models.Branch.select().order_by(models.Branch.id):
        click.echo(branch.name)


@app.cli.command()
@click.argument('branch_name')
@db_session
def kill_branch(branch_name):
    '''Remove branch and it's runs and artifacts'''
    branch = models.Branch.get(name=branch_name)
    if not branch:
        click.echo('No such branch: %r' % branch_name)
        return
    click.echo('Deleting brach id=%r' % branch.id)
    branch.delete()

@app.cli.command()
@click.argument('project_name')
@click.argument('branch_name')
@click.option('--dry-run/--no-dry-run')
@db_session
def kill_builds(project_name, branch_name, dry_run):
    '''Remove builds belonging to particular project and branch, and it's runs and artifacts'''
    project = models.Project.get(name=project_name)
    if not project:
        click.echo('No such project: %r' % project_name)
        return
    branch = models.Branch.get(name=branch_name)
    if not branch:
        click.echo('No such branch: %r' % branch_name)
        return
    click.echo('Deleting builds for project id=%r, brach id=%r' % (project.id, branch.id))
    query = select(build for build in models.Build if build.project is project and build.branch is branch)
    count = query.count()
    click.echo('Will delete %d builds' % count)
    if not dry_run:
        query.delete()


@app.cli.command()
@click.argument('project_name')
@click.argument('branch_name')
@click.argument('build_num')
@click.option('--dry-run/--no-dry-run')
@db_session
def kill_build(project_name, branch_name, build_num, dry_run):
    '''Remove single build, it's runs and artifacts'''
    project = models.Project.get(name=project_name)
    if not project:
        click.echo('No such project: %r' % project_name)
        return
    branch = models.Branch.get(name=branch_name)
    if not branch:
        click.echo('No such branch: %r' % branch_name)
        return
    build = models.Build.get(project=project, branch=branch, build_num=int(build_num))
    if not build:
        click.echo('No such build: %r' % build_num)
        return
    click.echo('Deleting build id=%r for project id=%r, brach id=%r' % (build.id, project.id, branch.id))
    if not dry_run:
        build.delete()

