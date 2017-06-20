''' Database schema for captured data'''

from datetime import datetime, timedelta
from pony.orm import *


db = Database()


class Project(db.Entity):
    name = Required(str)
    runs = Set('Run')

class CloudGroup(db.Entity):
    _table_ = 'cloud_group'
    name = Required(str)
    runs = Set('Run')

class Customization(db.Entity):
    name = Required(str)
    runs = Set('Run')

class Branch(db.Entity):
    name = Required(str)
    runs = Set('Run')

class Platform(db.Entity):
    name = Required(str)
    runs = Set('Run')

class ArtifactType(db.Entity):
    _table_ = 'artifact_type'
    name = Required(str)
    content_type = Required(str)
    artifacts = Set('Artifact')

class Test(db.Entity):
    path = Required(str)  # functional/some_dir/something_test.py/test_that
    is_leaf = Required(bool)  # False for dir and modules aggregates, True for actual tests
    runs = Set('Run')


class Run(db.Entity):
    root_run = Optional('Run')
    path = Optional(str, index=True)
    name = Optional(str)
    test = Optional(Test)
    outcome = Optional(str)
    started_at = Required(datetime, sql_type='timestamptz')
    duration = Optional(timedelta)
    artifacts = Set('Artifact')
    project = Optional(Project)
    branch = Optional(Branch)
    version = Optional(str, index=True)
    cloud_group = Optional(CloudGroup)
    customization = Optional(Customization)
    release = Optional(str)  # beta, release
    kind = Optional(str)  # release, debug
    platform = Optional(Platform)
    vc_changeset_id = Optional(str)  # version control changeset id of this build (hg id --debug)
    children = Set('Run')

class Artifact(db.Entity):
    run = Required(Run)
    type = Required(ArtifactType)
    name = Required(str)
    is_error = Required(bool)
    encoding = Optional(str)
    data = Required(buffer, lazy=True)
