#!/usr/bin/env python3

import argparse
import logging
import time
import timeit
from datetime import timedelta
from typing import Tuple, List

from pytimeparse.timeparse import timeparse

import crash_info
import external_api
import dump_tool
import utils

logger = logging.getLogger(__name__)

NAME = 'Crash Monitor and Analyzer'
VERSION = '2.0'
RETRY_CRASH_ID = 'RETRY'
FAILED_CRASH_ID = 'FAILED'
USELESS_STACK_KEY = 'USELESS_STACK'


class Options:
    def __init__(self, directory: str,
                 reports_size_limit: str = '10G',
                 dump_tool_size_limit: str = '10G',
                 cdb_cache_size_limit: str = '10G',
                 minimal_upload_interval: str = '1d',
                 **extra):
        self.directory = utils.Directory(directory)
        self.records_file = self.directory.file('records.json')
        self.reports_directory = self.directory.directory('reports')
        self.reports_size_limit = utils.Size(reports_size_limit)
        self.dump_tool_directory = self.directory.directory('dump_tool')
        self.dump_tool_size_limit = utils.Size(dump_tool_size_limit)
        self.cdb_cache_size_limit = utils.Size(cdb_cache_size_limit)
        self.extension = '*'
        self.min_version = '3.2'
        self.min_report_count = 2
        self.reports_each_run = 1000
        self.stand_by_sleep_s = 60
        self.keep_uploaded_reports = True
        self.minimal_upload_interval = timeparse(minimal_upload_interval)
        for key, value in extra.items():
            assert isinstance(value, type(getattr(self, key)))
            setattr(self, key, value)


class Monitor:
    def __init__(self, options: dict, fetch: dict, upload: dict, analyze: dict,
                 issue_autoclose_indicators: dict, debug: dict = {}):
        self._debug = debug
        self._options = Options(**options)
        self._options.reports_directory.make()
        self._options.dump_tool_directory.make()
        self._fetch, self._upload, self._analyze = fetch, upload, analyze
        self._autoclose_indicators = issue_autoclose_indicators
        self._analyze['cache_directory'] = self._options.dump_tool_directory.path
        self._records = self._options.records_file.parse(dict())

    def run_service(self):
        debug_concurrent = self._debug.get('run_concurrent', '').split()
        if debug_concurrent:
            logger.warning('Enable debug run_concurrent for ' + repr(debug_concurrent))
            utils.run_concurrent.debug = debug_concurrent

        debug_exceptions = self._debug.get('exceptions', None)
        if debug_exceptions:
            logger.warning('Enable debug exceptions')

        logger.info('Starting service...')
        last_upload_time = timeit.default_timer()
        while True:
            try:
                upload_interval = timeit.default_timer() - last_upload_time
                if upload_interval > self._options.minimal_upload_interval:
                    self._log_critical_error('No JIRA uploads within last {}'.format(
                        timedelta(seconds=(upload_interval))))

                self.analyze()
                if self.upload():
                    last_upload_time = timeit.default_timer()
                while not self.fetch():
                    time.sleep(self._options.stand_by_sleep_s)

            except (KeyboardInterrupt, utils.KeyboardInterruptError):
                logger.info('Service has stopped')
                return

            except Exception as error:
                if debug_exceptions:
                    raise

                self._log_critical_error(utils.format_error(error, include_stack=True))
                time.sleep(self._options.stand_by_sleep_s)

    def cleanup_jira_issues(self):
        try:
            known_issues = set()
            for _, record in self._records.items():
                issue = record.get('issue')
                if issue:
                    known_issues.add(issue)

            logger.info('There are {} known JIRA issue(s)'.format(len(known_issues)))
            if not known_issues:
                logger.warning('There are no known JIRA issues, clean up will start in {} seconds'
                               .format(self._options.stand_by_sleep_s))
                time.sleep(self._options.stand_by_sleep_s)

            options = self._upload.copy()
            options.pop('thread_count')
            jira = external_api.Jira(**options)
            while True:
                jira_issues = jira.all_issues()
                logger.info('There are {} issues in JIRA total'.format(len(jira_issues)))
                deleted = 0
                for issue in jira_issues:
                    if issue.key not in known_issues:
                        logger.info('Remove unknown JIRA issue {}: {}'.format(
                            issue.key, issue.fields.summary))
                        issue.delete()
                        deleted += 1

                if not deleted:
                    return logger.info('No more JIRA issues to delete')

        except KeyboardInterrupt:
            logger.info('Canceled by user')

    def flush_records(self):
        if self._records:
            self._options.records_file.serialize(self._records)

    def fetch(self) -> int:
        logger.info('Fetching new reports from server')
        directory = self._options.reports_directory
        new_reports = external_api.fetch_new_crashes(
            directory, known_reports=self._records.keys(), **self._fetch)

        if not new_reports:
            return 0

        for name in new_reports:
            self._records[name] = dict()
        self.flush_records()

        def is_useful(report):
            r = self._records.get(report.name)
            if r is None:
                logger.warning('Unregistered report file: ' + report.name)
                return False
            return not('issue' in r or r.get('crash_id') == FAILED_CRASH_ID)

        # No force cleanup because it's better to catch warning and increase storage.
        self._cleanup_cache(
            directory, self._options.reports_size_limit, is_useful, is_forced_on_failure=False)

        return len(new_reports)

    def analyze(self) -> int:
        to_analyze = []
        for name, data in self._records.items():
            crash_id = data.get('crash_id')
            if not crash_id or crash_id == RETRY_CRASH_ID:
                to_analyze.append(crash_info.Report(name))

        logger.info('Analyze {} report(s) from local cache'.format(len(to_analyze)))
        analyzed = []
        if to_analyze:
            reasons = crash_info.analyze_reports_concurrent(
                to_analyze, directory=self._options.reports_directory, **self._analyze)

            analyzed = {report.name: reason for report, reason in reasons}
            for report in to_analyze:
                reason = analyzed.get(report.name)
                record = self._records[report.name]
                record['crash_id'] = reason.crash_id if reason else (
                    FAILED_CRASH_ID if record.get('crash_id') else RETRY_CRASH_ID)

            self.flush_records()

        self._cleanup_cache(
            self._options.dump_tool_directory,
            self._options.dump_tool_size_limit,
            lambda d: d.name.endswith('release'))

        self._cleanup_cache(
            utils.MultiDirectory(*dump_tool.CDB_CACHE_DIRECTORIES),
            self._options.cdb_cache_size_limit,
            lambda d: d.size() < self._options.cdb_cache_size_limit / 1000)

        return len(analyzed)

    def upload(self):
        crashes_by_id = {}
        for name, record in self._records.items():
            crash_id, issue = record.get('crash_id'), record.get('issue')
            if crash_id and crash_id != FAILED_CRASH_ID and crash_id != RETRY_CRASH_ID:
                crash_data = crashes_by_id.setdefault(crash_id, {'issue': None, 'reports': []})
                if issue:
                    if issue != USELESS_STACK_KEY:
                        crash_data['issue'] = issue
                else:
                    crash_data['reports'].append(crash_info.Report(name))

        crashes_to_push = []
        for _, data in crashes_by_id.items():
            if data['reports']:
                if data['issue'] or len(data['reports']) >= self._options.min_report_count:
                    crashes_to_push.append((data['issue'], data['reports']))

        logger.info('Create or update {} JIRA issue(s) with new report(s)'.format(len(crashes_to_push)))
        uploads_count = 0
        for result in utils.run_concurrent(
                self._jira_sync, crashes_to_push, directory=self._options.reports_directory,
                autoclose_indicators=self._autoclose_indicators, **self._upload):
            if isinstance(result, external_api.JiraError):
                logger.warning(utils.format_error(result))
            elif isinstance(result, Exception):
                logger.error(utils.format_error(result))
            else:
                uploads_count += 1
                issue, reports = result
                logger.debug('JIRA issue {} updated with {} new report(s)'.format(issue, len(reports)))
                for r in reports:
                    self._records[r.name]['issue'] = issue
                    if not self._options.keep_uploaded_reports:
                        self._options.reports_directory.file(r.name).remove()

        if crashes_to_push:
            self.flush_records()
        return uploads_count

    @staticmethod
    def _jira_sync(crash_tuple: Tuple[str, List[crash_info.Report]], directory: utils.Directory,
                   api: type = external_api.Jira, **options):
        jira = api(**options)
        issue, reports = crash_tuple
        if not issue:
            report = reports[0]  # < Any will do.
            try:
                reason = crash_info.analyze_report(
                    report, directory, cache_directory=None)  # < Newer use dump tool.
            except crash_info.AnalyzeError as error:
                # This may happen when stack is considered to be useless after a logic change.
                logger.warning(utils.format_error(error, include_stack=True))
                logger.error('Skip creating issue for reports with useless stack')
                return USELESS_STACK_KEY, reports

            issue = jira.create_issue(report, reason)
            jira.autoclose_issue_if_required(issue, reason)

        jira.update_issue(issue, reports, directory=directory)
        return issue, reports

    @classmethod
    def _cleanup_cache(cls, directory: utils.Directory, size_limit: utils.Size,
                       is_important: callable, is_forced_on_failure: bool = True):
        def directory_message():
            return 'size {} is {} limit {} in {}'.format(
                size, 'within' if size < size_limit else 'over', size_limit, directory)

        size = directory.size()
        if size < size_limit:
            return logger.debug('Cleanup is not required for ' + directory_message())

        logger.info('Cleanup is started for ' + directory_message())
        removed_count = 0
        for d in directory.content():
            if not is_important(d):
                removed_count += 1
                d.remove()

        logger.info('Cleanup has removed {} items in {}'.format(removed_count, directory))
        size = directory.size()
        if size < size_limit:
            logger.info('Cleanup success for ' + directory_message())
        elif is_forced_on_failure:
            logger.warning('Starting forced cleanup for ' + directory_message())
            cls._cleanup_cache(directory, size_limit, lambda x: False, is_forced_on_failure=False)
        else:
            logger.error('Cleanup failed for ' + directory_message())

    @staticmethod
    def _log_critical_error(message: str):
        try:
            logger.critical(message)

        except Exception as log_error:
            print(utils.format_error(log_error, include_stack=True))
            print(message)


def main():
    try:
        import subprocess
        change_set, *_ = subprocess.check_output(['hg', 'id']).decode().split()
    except (ImportError, OSError):
        change_set = 'UNKNOWN'

    parser = argparse.ArgumentParser('{} version {}.{}'.format(NAME, VERSION, change_set))
    parser.add_argument('config_file')
    parser.add_argument('--cleanup-jira-issues', action='store_true',
                        help='Just remove unknown JIRA issue(s)')
    parser.add_argument('-o', '--override', action='append', default=[],
                        help='SECTION.KEY=VALUE to override config')

    arguments = parser.parse_args()
    config = utils.File(arguments.config_file).parse()
    for override in arguments.override:
        utils.update_dict(config, override)

    utils.setup_logging(
        **config.pop('logging'),
        title=(parser.prog + ', config: ' + arguments.config_file))

    monitor = Monitor(**config)
    if arguments.cleanup_jira_issues:
        monitor.cleanup_jira_issues()
    else:
        monitor.run_service()


if __name__ == '__main__':
    main()
