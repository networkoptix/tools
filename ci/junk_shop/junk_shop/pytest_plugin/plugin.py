'''pytest plugin capturing run results, artifacts stdout/stderr/log/etc to postgres database'''

import sys
import logging
from datetime import datetime, timedelta
import py
from pony.orm import db_session, commit
import pytest
from .. import models


LOG_FORMAT = '%(asctime)-15s %(levelname)-7s %(message)s'


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

    def __init__(self, config, db_capture_repository, run_id_file=None):
        assert not config.getvalue('capturelog')  # mutually exclusive
        self.capture_manager = config.pluginmanager.getplugin('capturemanager')
        self.repo = db_capture_repository
        self.run_id_file = run_id_file
        self.log_capturer = None
        self.root_run = None
        self.current_test_run = None
        self.stage_run = None

    def pytest_unconfigure(self):
        if self.log_capturer:
            self.log_capturer.close()
        
    @db_session
    def pytest_sessionstart(self, session):
        self.root_run = self._produce_test_run()
        self.log_capturer = LogCapturer(LOG_FORMAT)
        if self.run_id_file:
            with open(self.run_id_file, 'w') as f:
                print >>f, self.root_run.id

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
        stage_name = module_run.name
        for name, contents in report.sections:
            if name == 'Captured stdout':
                self.repo.add_artifact(module_run, 'stdout', '%s.stdout' % stage_name, self.repo.artifact_type.output, contents.strip())
            if name == 'Captured stderr':
                self.repo.add_artifact(module_run, 'stderr', '%s.stderr' % stage_name, self.repo.artifact_type.output, contents.strip(), is_error=True)
        self.repo.add_artifact(module_run, 'import', '%s.import' % stage_name, self.repo.artifact_type.log, self.log_capturer.pick_collected())
        if report.failed:
            module_run.outcome = 'failed'
            self.repo.add_artifact(module_run, 'traceback', '%s.traceback' % stage_name, self.repo.artifact_type.traceback, str(report.longrepr), is_error=True)

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
            stage_name = '%s-%s-%s' % (self.current_test_run.name, self.stage_run.name, name)
        else:
            parent_run = self.root_run  # session fixture teardown
            stage_name = '%s-%s' % (self.root_run.name, name)
        out, err = self.capture_manager.suspendcapture()
        log = self.log_capturer.pick_collected()
        if out or err or log:
            run = self.repo.add_run(name=name, parent=parent_run)
        if out:
            self.repo.add_artifact(run, 'stdout', '%s.stdout' % stage_name, self.repo.artifact_type.output, out.strip())
        if err:
            self.repo.add_artifact(run, 'stderr', '%s.stderr' % stage_name, self.repo.artifact_type.output, err.strip(), is_error=True)
        if log:
            self.repo.add_artifact(run, 'test', stage_name, self.repo.artifact_type.log, log)
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
        self.stage_run = self.repo.produce_run(self.current_test_run, 'test')
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
        stage_name = '%s-%s' % (self.current_test_run.name, stage_run.name)
        if report.failed:
            self.repo.add_artifact(stage_run, 'traceback', '%s.traceback' % stage_name, self.repo.artifact_type.traceback, str(report.longrepr), is_error=True)
            root_run.outcome = current_test_run.outcome = 'failed'
        if report.outcome == 'skipped':
            current_test_run.outcome = 'skipped'
        if report.when == 'call':
            if report.capstdout:
                self.repo.add_artifact(stage_run, 'stdout', '%s.stdout' % stage_name, self.repo.artifact_type.output, report.capstdout.strip())
            if report.capstderr:
                self.repo.add_artifact(stage_run, 'stderr', '%s.stderr' % stage_name, self.repo.artifact_type.output, report.capstderr.strip(), is_error=True)
            self.repo.add_artifact(stage_run, 'test', stage_name, self.repo.artifact_type.log, self.log_capturer.pick_collected())
        self.stage_run = None
        if report.when == 'teardown':
            if not current_test_run.outcome:
                current_test_run.outcome = 'passed'
            self.current_test_run = None

    def _produce_test_run(self, nodeid=None, is_test=False):
        test_path = ['functional']
        if nodeid:
            test_path += nodeid.replace('::', '/').split('/')
        return self.repo.produce_test_run(self.root_run, test_path, is_test)
