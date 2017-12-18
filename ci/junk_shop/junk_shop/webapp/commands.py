from pony.orm import db_session
import click

from junk_shop.webapp import app
from .. import models


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
