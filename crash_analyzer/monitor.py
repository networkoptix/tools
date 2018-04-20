#!/usr/bin/env python3

import argparse
import logging
import time
import traceback
import hurry.filesize as filesize
from typing import Tuple, List

import crash_info
import external_api
import utils

logger = logging.getLogger(__name__)

NAME = 'Crash Monitor and Analyzer'
VERSION = '2.0'
FAILED_CRASH_ID = 'FAILED'


class Options:
    def __init__(self, directory: str,
                 reports_size_limit: str = '10G',
                 dump_tool_size_limit: str = '10G',
                 **extra):
        self.directory = utils.Directory(directory)
        self.records_file = self.directory.file('records.json')
        self.reports_directory = self.directory.directory('reports')
        self.reports_size_limit = utils.Size(reports_size_limit)
        self.dump_tool_directory = self.directory.directory('dump_tool')
        self.dump_tool_size_limit = utils.Size(dump_tool_size_limit)
        self.extension = '*'
        self.min_version = '3.2'
        self.min_report_count = 2
        self.reports_each_run = 1000
        self.stand_by_sleep_s = 60
        for key, value in extra.items():
            assert isinstance(value, type(getattr(self, key)))
            setattr(self, key, value)


class Monitor:
    def __init__(self, options: dict, fetch: dict, upload: dict, analyze: dict):
        self._options = Options(**options)
        self._options.reports_directory.make()
        self._options.dump_tool_directory.make()
        self._fetch, self._upload, self._analyze = fetch, upload, analyze
        self._analyze['cache_directory'] = self._options.dump_tool_directory.path
        self._records = self._options.records_file.parse(dict())

    def run_service(self):
        logging.info('Starting service...')
        while True:
            try:
                self.analyze()
                self.upload()
                while not self.fetch():
                    time.sleep(self._options.stand_by_sleep_s)

            except InterruptedError:
                logging.info('Service has stopped')
                return

            except Exception:
                logger.critical(traceback.format_exc())
                time.sleep(self._options.stand_by_sleep_s)

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
        size = directory.size()
        if size > self._options.reports_size_limit:
            logger.info('Reports directory size is {}, remove failed dumps'.format(size))
            for r in self._records:
                # TODO: Also remove crash directory is it is not enough.
                if r.get('crash_id') == FAILED_CRASH_ID:
                    directory.file(name).remove()

        return len(new_reports)

    def analyze(self) -> int:
        to_analyze = [crash_info.Report(name)
                      for name, data in self._records.items() if not data.get('crash_id')]

        logger.info('Analyze {} reports in local database'.format(len(to_analyze)))
        reasons = crash_info.analyze_reports_concurrent(
            to_analyze, directory=self._options.reports_directory, **self._analyze)

        analyzed = {report.name: reason for report, reason in reasons}
        for report in to_analyze:
            reason = analyzed.get(report.name)
            crash_id = reason.crash_id if reason else FAILED_CRASH_ID
            self._records[report.name]['crash_id'] = crash_id

        self.flush_records()
        cache_size = self._options.dump_tool_directory.size()
        if cache_size > self._options.dump_tool_size_limit:
            logger.info('Dump tool cache has reached {}, clean up'.format(cache_size))
            for d in self._options.dump_tool_directory.directories():
                if not d.path.endswith('release'):
                    d.remove()

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

        logger.info('Create or update {} issues with new reports'.format(len(crashes_to_push)))
        for result in utils.run_concurrent(self._jira_sync, crashes_to_push,
                                           directory=self._options.reports_directory, **self._upload):
            if isinstance(result, Exception):
                logger.error(result)
            else:
                issue, reports = result
                logger.info('Issue {} updated with {} new reports'.format(issue, len(reports)))
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
            reason = crash_info.analyze_report(report, directory)  # < Fast for known reports.
            issue = jira.create_issue(report, reason)

        jira.update_issue(issue, reports)
        return issue, reports


def main():
    try:
        import subprocess
        change_set, *_ = subprocess.check_output('hg id').decode().split()
    except (ImportError, OSError):
        change_set = 'UNKNOWN'

    parser = argparse.ArgumentParser('{} version {}.{}'.format(NAME, VERSION, change_set))
    parser.add_argument('config_file')

    arguments = parser.parse_args()
    config = utils.File(arguments.config_file).parse()
    utils.setup_logging(
        **config.pop('logging'),
        title=(parser.prog + ', config: ' + arguments.config_file))

    monitor = Monitor(**config)
    monitor.run_service()


if __name__ == '__main__':
    main()
