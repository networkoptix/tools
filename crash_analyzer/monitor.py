#!/usr/bin/env python3

import argparse
import logging
import time
from typing import Tuple, List

import crash_info
import external_api
import dump_tool
import utils

logger = logging.getLogger(__name__)

NAME = 'Crash Monitor and Analyzer'
VERSION = '2.0'
FAILED_CRASH_ID = 'FAILED'


class Options:
    def __init__(self, directory: str,
                 reports_size_limit: str = '10G',
                 dump_tool_size_limit: str = '10G',
                 cdb_cache_size_limit: str = '10G',
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
        for key, value in extra.items():
            assert isinstance(value, type(getattr(self, key)))
            setattr(self, key, value)


class Monitor:
    def __init__(self, options: dict, fetch: dict, upload: dict, analyze: dict, debug: dict = {}):
        self._debug = debug
        self._options = Options(**options)
        self._options.reports_directory.make()
        self._options.dump_tool_directory.make()
        self._fetch, self._upload, self._analyze = fetch, upload, analyze
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
        while True:
            try:
                self.analyze()
                self.upload()
                while not self.fetch():
                    time.sleep(self._options.stand_by_sleep_s)

            except (KeyboardInterrupt, utils.KeyboardInterruptError):
                logger.info('Service has stopped')
                return

            except Exception as error:
                logger.critical(utils.format_error(error, include_stack=True))
                time.sleep(self._options.stand_by_sleep_s)
                if debug_exceptions:
                    raise

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
        self._cleanup_cache(
            directory,
            self._options.reports_size_limit,
            lambda d: self._records.get(d.name, {}).get('crash_id') != FAILED_CRASH_ID)

        return len(new_reports)

    def analyze(self) -> int:
        to_analyze = [crash_info.Report(name)
                      for name, data in self._records.items() if not data.get('crash_id')]

        logger.info('Analyze {} report(s) from local cache'.format(len(to_analyze)))
        if not to_analyze:
            return 0

        reasons = crash_info.analyze_reports_concurrent(
            to_analyze, directory=self._options.reports_directory, **self._analyze)

        analyzed = {report.name: reason for report, reason in reasons}
        for report in to_analyze:
            reason = analyzed.get(report.name)
            crash_id = reason.crash_id if reason else FAILED_CRASH_ID
            self._records[report.name]['crash_id'] = crash_id

        self.flush_records()
        self._cleanup_cache(
            self._options.dump_tool_directory,
            self._options.dump_tool_size_limit,
            lambda d: d.name.endswith('release'))
            
        self._cleanup_cache(
            utils.Directory(dump_tool.CDB_CACHE_DIRECTORY),
            self._options.cdb_cache_size_limit,
            lambda d: False)  # < TODO: Consider to keep system libraries.

        return len(analyzed)

    def upload(self):
        crashes_by_id = {}
        for name, record in self._records.items():
            crash_id, issue = record.get('crash_id'), record.get('issue')
            if crash_id and crash_id != FAILED_CRASH_ID:
                crash_data = crashes_by_id.setdefault(crash_id, {'issue': None, 'reports': []})
                if issue:
                    crash_data['issue'] = issue
                else:
                    crash_data['reports'].append(crash_info.Report(name))

        crashes_to_push = []
        for _, data in crashes_by_id.items():
            if data['reports']:
                if data['issue'] or len(data['reports']) >= self._options.min_report_count:
                    crashes_to_push.append((data['issue'], data['reports']))

        logger.info('Create or update {} JIRA issue(s) with new report(s)'.format(len(crashes_to_push)))
        for result in utils.run_concurrent(self._jira_sync, crashes_to_push,
                                           directory=self._options.reports_directory, **self._upload):
            if isinstance(result, Exception):
                logger.error(utils.format_error(result))
            else:
                issue, reports = result
                logger.debug('JIRA issue {} updated with {} new report(s)'.format(issue, len(reports)))
                for r in reports:
                    self._records[r.name]['issue'] = issue
                    self._options.reports_directory.file(r.name).remove()

        if crashes_to_push:
            self.flush_records()

    @staticmethod
    def _jira_sync(crash_tuple: Tuple[str, List[crash_info.Report]], directory: utils.Directory,
                   api: type = external_api.Jira, **options):
        jira = api(**options)
        issue, reports = crash_tuple
        if not issue:
            report = reports[0]  # < Any will do.
            reason = crash_info.analyze_report(
                report, directory, cache_directory=None)  # < Newer use dump tool.
            issue = jira.create_issue(report, reason)

        jira.update_issue(issue, reports, directory=directory)
        return issue, reports
        
    @staticmethod
    def _cleanup_cache(directory: utils.Directory, size_limit: utils.Size, is_impotant: callable):
        def directory_message():
            return 'directory size {} is {} limit {}: {}'.format(
                size, 'within' if size < size_limit else 'over', size_limit, directory.path)

        size = directory.size()
        if size < size_limit:
            return logger.debug('Cleanup is not required for ' + directory_message())

        logger.info('Cleanup is started for ' + directory_message())
        removed_count = 0
        for d in directory.content():
            if not is_impotant(d):
                removed_count += 1
                d.remove()

        logger.info('Cleanup has removed {} items in: {}'.format(removed_count, directory.path))
        size = directory.size()
        if size < size_limit:
            logger.info('Cleanup success for ' + directory_message())
        else:
            logger.error('Cleanup failed for ' + directory_message())


def main():
    try:
        import subprocess
        change_set, *_ = subprocess.check_output('hg id').decode().split()
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
