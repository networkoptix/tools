from flask import render_template, abort
from pony.orm import db_session
from junk_shop.webapp import app
from ..build_info import BuildInfoLoader


@app.route('/project/<project_name>/<branch_name>/<int:build_num>')
@db_session
def build(project_name, branch_name, build_num):
    loader = BuildInfoLoader(project_name, branch_name, build_num)
    if not loader.build:
        abort(404)
    build_info = loader.load_build_info()
    return render_template('build.html', **build_info._asdict())
