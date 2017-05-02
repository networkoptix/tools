''' Database schema for captured data'''

from datetime import datetime, timedelta
from pony.orm import *


db = Database()


class CloudGroup(db.Entity):
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
    branch = Optional(Branch)
    version = Optional(str)
    cloud_group = Optional(CloudGroup)
    customization = Optional(Customization)
    release = Optional(str)  # beta, release
    kind = Optional(str)  # release, debug
    platform = Optional(Platform)
    children = Set('Run')

class Artifact(db.Entity):
    type = Required(ArtifactType)
    name = Required(str)
    is_error = Required(bool)
    run = Required(Run)
    data = Required(buffer)
