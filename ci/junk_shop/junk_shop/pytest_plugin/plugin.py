'''pytest plugin capturing run results, artifacts stdout/stderr/log/etc to postgres database'''

import collections
import sys
import logging
import traceback
from datetime import datetime, timedelta

from pony.orm import db_session, commit
import pytest
from _pytest.fixtures import FixtureLookupErrorRepr
from _pytest._code.code import ReprExceptionInfo

from .. import models


LOG_FORMAT = '%(asctime)-15s %(levelname)-7s %(threadName)-11s %(message)s'
LOG_MESSAGE_COUNT_LIMIT = 10000


class HeadAndTailHandler(logging.Handler):

    # keep first and last limit/2 log messages

    def __init__(self, limit):
        super(HeadAndTailHandler, self).__init__()
        self._limit = limit
        self._head_message_list = []
        self._tail_message_list = collections.deque(maxlen=limit/2)
        self._dropped_record_count = 0
        self.captured_size = 0

    def emit(self, record):
        try:
            msg = self.format(record)
            if isinstance(msg, unicode):
                msg = msg.encode('utf-8', 'replace')
            msg += '\n'
            if len(self._head_message_list) < self._limit / 2:
                self._head_message_list.append(msg)
            else:
                if len(self._tail_message_list) == self._tail_message_list.maxlen:
                    self._dropped_record_count += 1
                self._tail_message_list.append(msg)
            self.captured_size += len(msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def pop_collected(self):
        head = ''.join(self._head_message_list)
        tail = ''.join(self._tail_message_list)
        if self._dropped_record_count:
            data = head + '[ %d messages are dropped ]\n' % self._dropped_record_count + tail
        else:
            data = head + tail
        self._clear()
        return data

    def close(self):
        # do not hold memory until gc collects us
        self._clear()
        super(HeadAndTailHandler, self).close()

    def _clear(self):
        del self._head_message_list[:]
        self._tail_message_list.clear()
        self._dropped_record_count = 0
        self.captured_size = 0


class LogCapturer(object):

    def __init__(self, log_format):
        self._log_handler = handler = HeadAndTailHandler(LOG_MESSAGE_COUNT_LIMIT)
        handler.setFormatter(logging.Formatter(log_format))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.NOTSET)

    def close(self):
        self._log_handler.close()
        root_logger = logging.getLogger()
        root_logger.removeHandler(self._log_handler)

    def pick_collected(self):
        try:
            return self._log_handler.pop_collected()
        except MemoryError as x:
            # logger is probably already failed by this point, using print
            print 'Error: captured log is too large (%r): %r' % (self._log_handler.captured_size, x)
            traceback.print_exc()
            return None


class DbCapturePlugin(object):

    def __init__(self, config, db_capture_repository, run_id_file=None, run_name=None):
        self.capture_manager = config.pluginmanager.getplugin('capturemanager')
        self.repo = db_capture_repository
        self.run_id_file = run_id_file
        self.run_name = run_name
        self.log_capturer = None
        self.root_run = None
        self.current_test_run = None
        self.stage_run = None

    def pytest_unconfigure(self):
        if self.log_capturer:
            self.log_capturer.close()
        
    @db_session
    def pytest_sessionstart(self, session):
        self.root_run = self._produce_root_run()
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
        outerr = self.capture_manager.suspendcapture()
        if outerr:
            out, err = outerr
        else:
            out = err = None
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
            message = None
            if isinstance(report.longrepr, ReprExceptionInfo):
                message = report.longrepr.reprcrash.message
            if isinstance(report.longrepr, FixtureLookupErrorRepr):
                message = report.longrepr.errorstring
            if message:
                current_test_run.error_message = message.splitlines()[0]
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

    def _produce_root_run(self):
        test_path = [self.run_name or 'functional']
        run = self.repo.produce_test_run(self.root_run, test_path)
        return models.Run[run.id]  # ensure it is from current transaction

    def _produce_test_run(self, nodeid=None, is_test=False):
        test_path = ['functional']
        if nodeid:
            test_path += nodeid.replace('::', '/').split('/')
        run = self.repo.produce_test_run(self.root_run, test_path, is_test)
        return models.Run[run.id]  # ensure it is from current transaction
