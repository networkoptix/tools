''' Database schema for captured data'''

from datetime import datetime, timedelta
from pony.orm import *


db = Database()


class Project(db.Entity):
    name = Required(str)
    builds = Set('Build')

class CloudGroup(db.Entity):
    _table_ = 'cloud_group'
    name = Required(str)
    builds = Set('Build')

class Customization(db.Entity):
    name = Required(str)
    builds = Set('Build')

class Branch(db.Entity):
    name = Required(str)
    builds = Set('Build')

class Platform(db.Entity):
    name = Required(str)
    runs = Set('Run')

class RunParameter(db.Entity):
    _table_ = 'run_parameter'
    name = Required(str)
    values = Set('RunParameterValue')


class ArtifactType(db.Entity):
    _table_ = 'artifact_type'
    name = Required(str)
    ext = Optional(str)
    content_type = Required(str)
    artifacts = Set('Artifact')

class Metric(db.Entity):
    name = Required(str)
    values = Set('MetricValue')

class Test(db.Entity):
    path = Required(str)  # functional/some_dir/something_test.py/test_that
    is_leaf = Required(bool)  # False for dir and modules aggregates, True for actual tests
    runs = Set('Run')


# records information for particular jenkins build
class Build(db.Entity):
    project = Required(Project)
    branch = Required(Branch)
    build_num = Required(int)
    version = Optional(str)
    release = Optional(str)  # beta, release
    configuration = Optional(str)  # release, debug
    cloud_group = Optional(CloudGroup)
    customization = Optional(Customization)
    is_incremental = Optional(bool)
    jenkins_url = Optional(str)
    repository_url = Optional(str)
    revision = Optional(str)
    duration = Optional(timedelta)
    composite_key(project, branch, build_num)
    runs = Set('Run')
    changesets = Set('BuildChangeSet')

class BuildChangeSet(db.Entity):
    _table_ = 'build_changeset'
    build = Required(Build, index=True)
    revision = Required(str)
    date = Required(datetime, sql_type='timestamptz')
    user = Required(str)
    email = Required(str)
    desc = Optional(str)


class Run(db.Entity):
    root_run = Optional('Run')
    path = Optional(str, index=True)
    name = Optional(str)
    build = Optional(Build, index=True)
    test = Optional(Test)
    outcome = Optional(str)
    error_message = Optional(str)
    started_at = Required(datetime, sql_type='timestamptz')
    duration = Optional(timedelta)
    platform = Optional(Platform)
    children = Set('Run')
    artifacts = Set('Artifact')
    run_parameters = Set('RunParameterValue')
    metrics = Set('MetricValue')

class Artifact(db.Entity):
    run = Required(Run)
    type = Required(ArtifactType)
    short_name = Required(str)
    full_name = Required(str)
    is_error = Required(bool)
    encoding = Optional(str)
    data = Required(buffer, lazy=True)

class RunParameterValue(db.Entity):
    _table_ = 'run_parameter_value'
    run_parameter = Required(RunParameter)
    run = Required(Run)
    value = Required(str)

class MetricValue(db.Entity):
    _table_ = 'metric_value'
    metric = Required(Metric)
    run = Required(Run)
    value = Required(float)
