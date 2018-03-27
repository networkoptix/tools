#!/usr/bin/env python3

import argparse
import logging
import os
import time

import crash_info
import external_api
import utils

logger = logging.getLogger(__name__)


class Options:
    def __init__(self, directory: str, **extra):
        self.directory = directory
        self.format = '*'
        self.min_version = '3.2'
        self.min_report_count = 2
        self.reports_each_run = 1000
        self.stand_by_sleep_s = 60
        self.update(**extra)

    def update(self, **options):
        for key, value in options.items():
            assert type(getattr(self, key)) == type(value)
            setattr(self, key, value)

    def cache_path(self):
        return os.path.join(self.directory, 'cache.txt')

    def reports_path(self, *report):
        return os.path.join(self.directory, 'reports')


class Record:
    def __init__(self, name: str, crash_id: str = '', case: str = ''):
        self.name = name
        self.crash_id = crash_id
        self.case = case


class Monitor:
    def __init__(self, options: Options,
                 crash_server: external_api.CrashServer, jira: external_api.Jira):
        self._options = options
        self._storage = crash_info.Storage(options.reports_path())
        self._crash_server = crash_server
        self._jira = jira
        self._reasons = dict()
        self._records = dict()
        self.reload_cache()
        logger.info('Working directory: {}'.format(os.path.abspath(self._options.directory)))

    def __del__(self):
        if self._records:
            self.flush_cache()

    def reload_cache(self):
        """Reloads runtime cache from file system.
        """
        self._records = dict()
        # TODO: Consider to use yaml instead.
        try:
            with open(self._options.cache_path(), 'r') as f:
                for line in f:
                    split = line[:-1].split(' ')
                    if split[0]:
                        self._records[split[0]] = Record(*split)

        except FileNotFoundError:
            self.flush_cache()

    def flush_cache(self):
        """Flushes runtime cache to file system.
        """
        with open(self._options.cache_path(), 'w') as f:
            for name, record in self._records.items():
                fields = [x for x in [name, record.crash_id, record.case] if x]
                f.write(' '.join(fields) + '\n')

        for name, record in self._records.items():
            if record.crash_id == 'FAILED' or record.case:
                self._storage.delete(name)
                record.crash_id == 'FAILED_REMOVED'

        # TODO: Clean up oldest crash files in case of HDD overflow.

    def download_new_reports(self):
        """Downloads all unknown dumps from crash server, returns names.
        """
        new_records = set()
        report_names = self._crash_server.list_all(self._options.format)
        for name in report_names:
            if len(new_records) > self._options.reports_each_run:
                skipped = len(report_names) - len(new_records)
                logger.debug('Skip downloading {} reports over limit'.format(skipped))
                break

            if self._records.get(name, None):
                continue  # < Already downloaded.

            if crash_info.Report(name).version < self._options.min_version:
                continue  # < Skip uninteresting versions.

            self._storage.save(name, self._crash_server.get(name))
            self._records[name] = Record(name)
            new_records.add(name)

        logger.info('Downloaded {} new report(s) to analyze'.format(len(new_records)))
        return new_records

    def analyze_new_reports(self):
        """Analyze all cached crash reports and fill crash_id.
        """
        for name, record in self._records.items():
            if record.crash_id:
                continue  # < Analysis is not required.

            # TODO: Think about multithreaded solution for dmp.
            try:
                report = crash_info.Report(name)
                reason = self._storage.analyze(report)

            except crash_info.Error as e:
                record.crash_id = 'FAILED'
                logger.warning(e)

            else:
                record.crash_id = reason.crash_id()
                self._reasons[record.crash_id] = reason
                logger.debug('Dump {} is caused by: {}'.format(name, reason))

    def upload_to_jira(self):
        """Uploads all reports which were not uploaded.
        """
        # These maps could be cached in class fields for performance increase. However currently it
        # is far away from being a bottle neck.
        cases_by_crash_id = dict()
        records_by_crash_id = dict()
        for name, record in self._records.items():
            if not record.crash_id.startswith('FAILED'):
                if record.case:
                    cases_by_crash_id[record.crash_id] = record.case
                else:
                    records_by_crash_id.setdefault(record.crash_id, []).append(record)

        for crash_id, records in records_by_crash_id.items():
            case = cases_by_crash_id.get(crash_id, None)
            if not case:
                if len(records) < self._options.min_report_count:
                    continue  # < Not enough reports for creating new case.

                reason = self._reasons.get(crash_id, None)
                if not reason:
                    logger.error('Unable to get reason for crash id: {}'.format(crash_id))
                    continue

                report = crash_info.Report(records[0].name)
                case = self._jira.create_issue(report, reason)

            reports = list(crash_info.Report(r.name) for r in records)
            if self._jira.update_issue(case, reports):
                self._jira.attach_files(case, sum((self._storage.files(r) for r in reports), []))

            for record in records:
                record.case = case

    def run_service(self):
        """Run a download-analyze-upload loop forever.
        """
        logger.info('Service has started')
        while True:
            try:
                # First analyze already downloaded reports in case of reastart.
                self.analyze_new_reports()
                self.upload_to_jira()
                self.flush_cache()

                # Then download new reports and prepare for next run.
                while not self.download_new_reports():
                    time.sleep(self._options.stand_by_sleep_s)

                self.flush_cache()

            except KeyboardInterrupt:
                logger.info('Service has stopped')
                return

            except Exception as e:
                logger.error(e)
                self.flush_cache()
                time.sleep(self._options.stand_by_sleep_s)


def main():
    parser = argparse.ArgumentParser('Crash Monitor and Analyzer')
    parser.add_argument('configuration_file')

    arguments = parser.parse_args()
    config = utils.file_parse(arguments.configuration_file)
    utils.setup_logging(**config['logging'])

    monitor = Monitor(
        Options(**config['options']),
        external_api.CrashServer(**config['crashServer']),
        external_api.Jira(**config['jira']))

    monitor.run_service()


if __name__ == '__main__':
    main()
