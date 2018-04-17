#!/usr/bin/env python3

import argparse
import logging
import time
import traceback
from typing import Tuple, List

import crash_info
import external_api
import utils

logger = logging.getLogger(__name__)

FAILED_CRASH_ID = 'FAILED'


class Options:
    def __init__(self, directory: str, **extra):
        self.directory = utils.Directory(directory)
        self.records_file = self.directory.file('records.json')
        self.reports_directory = self.directory.directory('reports')
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
        self._fetch, self._upload, self._analyze = fetch, upload, analyze
        self._analyze['cache_directory'] = self._options.directory.directory('dump_tool').path
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

    def fetch(self):
        logger.info('Fetching new reports from server')
        new_reports = external_api.fetch_new_crashes(
            self._options.reports_directory, known_reports=self._records.keys(), **self._fetch)

        if not new_reports:
            return 0

        for name in new_reports:
            self._records[name] = dict(name=name)

        self.flush_records()
        return len(new_reports)

    def analyze(self):
        to_analyze = [crash_info.Report(r['name'])
                      for r in self._records.values() if not r.get('crash_id')]

        logger.info('Analyze {} reports in local database'.format(len(to_analyze)))
        analyzed = {report.name: reason for report, reason in crash_info.analyze_files_concurrent(
            to_analyze, directory=self._options.reports_directory, **self._analyze)}

        for report in to_analyze:
            reason = analyzed.get(report.name)
            crash_id = reason.crash_id if reason else FAILED_CRASH_ID
            self._records[report.name]['crash_id'] = crash_id

        self.flush_records()
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

        if crashes_to_push:
            self.flush_records()

    @staticmethod
    def _jira_sync(crash_tuple: Tuple[str, List[crash_info.Report]], directory: utils.Directory,
                   api: type = external_api.Jira, **options):
        jira = api(**options)
        issue, reports = crash_tuple
        if not issue:
            report = reports[0]  # < Any will do.
            reason = crash_info.analyze_file(report, directory)  # < Fast for known reports.
            issue = jira.create_issue(report, reason)

        jira.update_issue(issue, reports)
        return issue, reports


def main():
    parser = argparse.ArgumentParser('Crash Monitor and Analyzer')
    parser.add_argument('configuration_file')

    arguments = parser.parse_args()
    config = utils.File(arguments.configuration_file).parse()
    utils.setup_logging(**config['logging'])

    monitor = Monitor(
        Options(**config['options']),
        external_api.CrashServer(**config['crashServer']),
        external_api.Jira(**config['jira']))

    monitor.run_service()


if __name__ == '__main__':
    main()
