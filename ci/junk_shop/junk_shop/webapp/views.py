import bz2
from flask import url_for, redirect
from pony.orm import db_session
from .. import models
from junk_shop.webapp import app
from .run import artifact_disposition


@app.route('/')
def index():
    return redirect(url_for('project_list'))


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
    headers = {
        'Content-Type': artifact.type.content_type,
        'Content-Disposition': '%s; filename="%s%s"' % (
            artifact_disposition(artifact.type.content_type), artifact.full_name, artifact.type.ext),
        }
    return str(data), headers
