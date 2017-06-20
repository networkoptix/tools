import os
from argparse import ArgumentTypeError
import bz2
from pony.orm import commit, select, raw_sql, sql_debug
from .utils import SimpleNamespace, datetime_utc_now
from . import models


class Parameters(object):

    example = ','.join([
        'project=ci',
        'branch=dev_3.0.0',
        'version=3.0.10',
        'release=beta',
        'kind=debug',
        'platform=linux-64',
        'vc_changeset_id=6f305e61fc95ecf3caf2fcc6dcdf51b18811e12e',
        ])
    known_parameters = ['project', 'branch', 'version', 'cloud_group', 'customization', 'release', 'kind', 'platform', 'vc_changeset_id']

    @classmethod
    def from_string(cls, parameters_str):
        error_msg = 'Expected parameters in form "%s", but got: %r' % (cls.example, parameters_str)
        parameters = cls()
        for pair in parameters_str.split(','):
            l = pair.split('=')
            if len(l) != 2:
                raise ArgumentTypeError(error_msg)
            name, value = l
            if name not in cls.known_parameters:
                raise ArgumentTypeError('Unknown parameter: %r. Known are: %s' % (name, ', '.join(known_names)))
            setattr(parameters, name, value)
        return parameters

    def __init__(self):
        self.project = None
        self.branch = None
        self.version = None
        self.cloud_group = None
        self.customization = None
        self.release = None
        self.kind = None
        self.platform = None
        self.vc_changeset_id = None


class ArtifactType(object):

    def __init__(self, name, content_type):
        self.name = name
        self.content_type = content_type
        self.id = None


class DbCaptureRepository(object):

    def __init__(self, db_config, parameters):
        self.parameters = parameters
        self.artifact_type = SimpleNamespace(
            traceback=ArtifactType('traceback', 'text/plain'),
            output=ArtifactType('output', 'text/plain'),
            log=ArtifactType('log', 'text/plain'),
            core=ArtifactType('core', 'application/octet-stream'),
            )
        if 'SQL_DEBUG' in os.environ:
            sql_debug(True)
        models.db.bind('postgres', host=db_config.host, user=db_config.user,
                       password=db_config.password, port=db_config.port)
        models.db.generate_mapping(create_tables=True)
        self.test_run = {}  # test path -> models.Run

    def _select_run_children(self, parent):
        return select(run for run in models.Run if raw_sql("run.path similar to $parent.path || '[^/]+/'"))

    def add_run(self, name=None, parent=None, test=None):
        root_run = None
        if parent:
            parent = models.Run[parent.id]
            root_run = parent.root_run or parent
        run = models.Run(
            root_run=root_run if parent else None,
            name=name or '',
            test=test,
            started_at=datetime_utc_now(),
            outcome='incomplete' if test else '',
            )
        if self.parameters and not parent:
            for name in Parameters.known_parameters:
                setattr(run, name, self._produce_parameter(name, getattr(self.parameters, name)))
        commit()
        run.path = '%s%d/' % (parent.path if parent else '', run.id)
        return run

    def _produce_artifact_type(self, artifact_type_rec):
        if artifact_type_rec.id:
            return models.ArtifactType[artifact_type_rec.id]
        at = models.ArtifactType.get(name=artifact_type_rec.name)
        if not at:
            at = models.ArtifactType(name=artifact_type_rec.name, content_type=artifact_type_rec.content_type)
            commit()
        artifact_type_rec.id = at.id
        return at

    def _produce_parameter(self, parameter, value):
        param2model = dict(
            project=models.Project,
            branch=models.Branch,
            cloud_group=models.CloudGroup,
            customization=models.Customization,
            platform=models.Platform,
            )
        model = param2model.get(parameter)
        if not model:
            return value or ''  # plain str or None
        if not value:
            return None
        rec = model.get(name=value)
        if not rec:
            rec = model(name=value)
        return rec

    def produce_run(self, parent, name):
        run = self._select_run_children(parent).filter(name=name).get()
        if not run:
            run = self.add_run(name, parent)
        return run

    def produce_test(self, test_path, is_leaf):
        test = models.Test.get(path=test_path)
        if test:
            assert test.is_leaf == is_leaf, repr((is_leaf, test_path))
        else:
            test = models.Test(path=test_path, is_leaf=is_leaf)
        return test

    def produce_test_run(self, root_run, test_path_list, is_test=False):
        run = root_run
        # create all parent nodes too
        for path, name, is_leaf in self._iter_path_parents(test_path_list):
            test = self.produce_test(path, is_leaf=is_leaf and is_test)
            parent_run = run
            run = self.test_run.get(path)
            if not run:
                run = self.add_run(name, parent_run, test)
                self.test_run[path] = run
        return run

    def _iter_path_parents(self, path_list):
        for i in range(len(path_list)):
            path = '/'.join(path_list[:i+1])
            name = path_list[i]
            is_leaf = i == len(path_list) - 1
            yield (path, name, is_leaf)

    def add_artifact(self, run, name, artifact_type_rec, data, is_error=False):
        assert run
        if not data: return
        at = self._produce_artifact_type(artifact_type_rec)
        if type(data) is unicode:
            data = data.encode('utf-8')
        compressed_data = bz2.compress(data)
        artifact = models.Artifact(
            type=at,
            name=name,
            is_error=is_error,
            run=run,
            encoding='bz2',
            data=compressed_data)
        #print '----- added artifact %s for run %s' % (artifact.type, run.path)

    def set_test_outcome(self, parent_run):
        outcome = None
        for run in self._select_run_children(parent_run):
            if run.outcome in [None, 'incomplete']:
                self.set_test_outcome(run)
            if run.outcome == 'failed':
                outcome = run.outcome
            elif not outcome and run.outcome == 'passed':
                outcome = run.outcome
            elif not outcome and run.outcome != 'skipped':
                outcome = run.outcome
        parent_run.outcome = outcome or 'skipped'
