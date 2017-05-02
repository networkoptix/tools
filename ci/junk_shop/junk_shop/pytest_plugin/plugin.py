'''pytest plugin capturing run results, artifacts stdout/stderr/log/etc to postgres database'''

import sys
import logging
from datetime import datetime, timedelta
from argparse import ArgumentTypeError
import py
from pony.orm import db_session, commit, select, raw_sql
import pytest
from ..utils import SimpleNamespace, datetime_utc_now
from .. import models


LOG_FORMAT = '%(asctime)-15s %(levelname)-7s %(message)s'


class Parameters(object):

    example = 'branch=dev_3.0.0,version=3.0.10,release=beta,kind=debug,platform=linux-64'
    known_parameters = ['branch', 'version', 'cloud_group', 'customization', 'release', 'kind', 'platform']

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
        self.branch = None
        self.version = None
        self.cloud_group = None
        self.customization = None
        self.release = None
        self.kind = None
        self.platform = None


class ArtifactType(object):

    def __init__(self, name, content_type):
        self.name = name
        self.content_type = content_type
        self.id = None


class DpCaptureRepository(object):

    def __init__(self, db_config, parameters):
        self.parameters = parameters
        self.artifact_type = SimpleNamespace(
            traceback=ArtifactType('traceback', 'text/plain'),
            output=ArtifactType('output', 'text/plain'),
            log=ArtifactType('log', 'text/plain'),
            core=ArtifactType('core', 'application/octet-stream'),
            )
        models.db.bind('postgres', host=db_config.host, user=db_config.user, password=db_config.password)
        models.db.generate_mapping(create_tables=True)

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
            )
        if self.parameters:
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
            branch=models.Branch,
            cloud_group=models.CloudGroup,
            customization=models.Customization,
            platform=models.Platform,
            )
        model = param2model.get(parameter)
        if not model:
            return value or ''  # plain str or None
        if value is None:
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

    def add_artifact(self, run, name, artifact_type_rec, data, is_error=False):
        assert run
        if not data: return
        at = self._produce_artifact_type(artifact_type_rec)
        if type(data) is unicode:
            data = data.encode('utf-8')
        artifact = models.Artifact(type=at, name=name, is_error=is_error, run=run, data=data)
        #print '----- added artifact %s for run %s' % (artifact.type, run.path)

    def set_test_outcome(self, parent_run):
        outcome = 'passed'
        for run in self._select_run_children(parent_run):
            if not run.outcome:
                self.set_test_outcome(run)
            if run.outcome != 'passed':
                outcome = 'failed'
        parent_run.outcome = outcome


class LogCapturer(object):

    def __init__(self, log_format):
        self._log_stream = py.io.TextIO()
        self._log_handler = handler = logging.StreamHandler(self._log_stream)
        handler.setFormatter(logging.Formatter(log_format))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.NOTSET)

    def close(self):
        self._log_handler.close()
        self._log_stream.close()
        root_logger = logging.getLogger()
        root_logger.removeHandler(self._log_handler)

    def pick_collected(self):
        log = self._log_stream.getvalue().strip()
        self._log_stream.seek(0)
        self._log_stream.truncate()
        return log


class DbCapturePlugin(object):

    def __init__(self, config, db_config, parameters):
        assert not config.getvalue('capturelog')  # mutually exclusive
        self.capture_manager = config.pluginmanager.getplugin('capturemanager')
        self.repo = DpCaptureRepository(db_config, parameters)
        self.log_capturer = None
        self.root_run = None
        self.test_run = {}  # test path -> models.Run
        self.current_test_run = None
        self.stage_run = None

    def pytest_unconfigure(self):
        if self.log_capturer:
            self.log_capturer.close()
        
    @db_session
    def pytest_sessionstart(self, session):
        self.root_run = self._produce_test_run()
        self.log_capturer = LogCapturer(LOG_FORMAT)

    @db_session
    def pytest_sessionfinish(self, session):
        if hasattr(self.capture_manager, '_capturing'):  # initialized yet?
            self.capture_manager.resumecapture()
        root_run = models.Run[self.root_run.id]
        self.repo.set_test_outcome(root_run)

    @db_session
    def pytest_collectreport(self, report):
        root_run = models.Run[self.root_run.id]
        module_run = self._produce_test_run(report.nodeid)
        for name, contents in report.sections:
            if name == 'Captured stdout':
                self.repo.add_artifact(module_run, 'stdout', self.repo.artifact_type.output, contents.strip())
            if name == 'Captured stderr':
                self.repo.add_artifact(module_run, 'stderr', self.repo.artifact_type.output, contents.strip(), is_error=True)
        self.repo.add_artifact(module_run, 'import', self.repo.artifact_type.log, self.log_capturer.pick_collected())
        if report.failed:
            module_run.outcome = 'failed'
            self.repo.add_artifact(module_run, 'traceback', self.repo.artifact_type.traceback, str(report.longrepr), is_error=True)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_fixture_setup(self, fixturedef, request):
        yield
        self.save_captured_to_fixture(fixturedef.argname)

    def pytest_fixture_post_finalizer(self, fixturedef):
        if getattr(fixturedef, 'cached_result', None):
            self.save_captured_to_fixture(fixturedef.argname)

    @db_session
    def save_captured_to_fixture(self, name):
        if self.stage_run:
            parent_run = self.stage_run
        else:
            parent_run = self.root_run  # session fixture teardown
        out, err = self.capture_manager.suspendcapture()
        log = self.log_capturer.pick_collected()
        if out or err or log:
            run = self.repo.add_run(name=name, parent=parent_run)
        if out:
            self.repo.add_artifact(run, 'stdout', self.repo.artifact_type.output, out.strip())
        if err:
            self.repo.add_artifact(run, 'stderr', self.repo.artifact_type.output, err.strip(), is_error=True)
        if log:
            self.repo.add_artifact(run, 'test', self.repo.artifact_type.log, log)
        self.capture_manager.resumecapture()

    @db_session
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        self.current_test_run = self._produce_test_run(item.nodeid, is_test=True)
        self.stage_run = self.repo.produce_run(self.current_test_run, 'setup')
        commit()
        yield

    @db_session
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        self.stage_run = self.repo.produce_run(self.current_test_run, 'call')
        commit()
        yield

    @db_session
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item, nextitem):
        self.stage_run = self.repo.produce_run(self.current_test_run, 'teardown')
        commit()
        yield

    @db_session
    def pytest_runtest_logreport(self, report):
        root_run = models.Run[self.root_run.id]
        current_test_run = models.Run[self.current_test_run.id]
        stage_run = models.Run[self.stage_run.id]
        stage_run.outcome = report.outcome
        stage_run.duration = timedelta(seconds=report.duration)
        if report.failed:
            self.repo.add_artifact(stage_run, 'traceback', self.repo.artifact_type.traceback, str(report.longrepr), is_error=True)
            root_run.outcome = current_test_run.outcome = 'failed'
        if report.when == 'call':
            if report.capstdout:
                self.repo.add_artifact(stage_run, 'stdout', self.repo.artifact_type.output, report.capstdout.strip())
            if report.capstderr:
                self.repo.add_artifact(stage_run, 'stderr', self.repo.artifact_type.output, report.capstderr.strip(), is_error=True)
            self.repo.add_artifact(stage_run, 'test', self.repo.artifact_type.log, self.log_capturer.pick_collected())
        self.stage_run = None
        if report.when == 'teardown':
            if not current_test_run.outcome:
                current_test_run.outcome = 'passed'
            self.current_test_run = None

    def _iter_path_parents(self, path):
        path_list = path.split('/')
        for i in range(len(path_list)):
            path = '/'.join(path_list[:i+1])
            name = path_list[i]
            is_leaf = i == len(path_list) - 1
            yield (path, name, is_leaf)

    def _produce_test_run(self, nodeid=None, is_test=False):
        run_path = 'functional'
        if nodeid:
            run_path += '/' + nodeid.replace('::', '/')
        run = self.root_run
        # create all parent nodes too
        for path, name, is_leaf in self._iter_path_parents(run_path):
            test = models.Test.get(path=path)
            if test:
                assert test.is_leaf == (is_leaf and is_test), repr(path)
            else:
                test = models.Test(path=path, is_leaf=is_leaf and is_test)
            parent_run = run
            run = self.test_run.get(path)
            if not run:
                run = self.repo.add_run(name, parent_run, test)
                self.test_run[path] = run
        return run
