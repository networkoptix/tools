from flask import url_for, redirect
from pony.orm import db_session
from .. import models
from junk_shop.webapp import app
from .run import artifact_disposition
from .artifact import decode_artifact_data


@app.route('/')
def index():
    return redirect(url_for('project_list'))


@app.route('/artifact/<int:artifact_id>')
@db_session
def artifact(artifact_id):
    artifact = models.Artifact.get(id=artifact_id)
    data = decode_artifact_data(artifact)
    headers = {
        'Content-Type': artifact.type.content_type,
        'Content-Disposition': '%s; filename="%s%s"' % (
            artifact_disposition(artifact.type.content_type), artifact.full_name, artifact.type.ext),
        }
    return str(data), headers
