#!/usr/bin/env python
"""Get performance metrics from test  rail

    1. How many cases in the test rail.
    2. How many cases are automated (percent).
    3. How long is for regress testing.
    3. How much time do automation saves.
"""
import csv
import pprint
from datetime import timedelta
from enum import Enum
import argparse
import logging
from pathlib import Path

from testrail import APIClient
from timedelta_str import str_to_timedelta, timedelta_to_str

TEST_RAIL_URL = 'https://networkoptix.testrail.net/'
VMS_PROJECT_NAME = 'VMS'
ZERO_TIMEDELTA = timedelta(seconds=0)

_logger = logging.getLogger(__name__)


class CaseStatus(Enum):
    NOT_READY = 0
    IN_REVIEW = 1
    READY = 2
    NOT_ACTUAL = 3


class AutoTestStatus(Enum):
    NOT_AUTOMATED = 0
    IN_REVIEW = 1
    AUTOMATED = 2
    CAN_NOT_BE_AUTOTESTED = 3
    PLANNED = 4


class Stats:

    def __init__(
            self,
            count=0,
            duration=ZERO_TIMEDELTA,
            automated=0,
            automated_duration=ZERO_TIMEDELTA,
            planned=0,
            planned_duration=ZERO_TIMEDELTA,
            ):
        self.count = count
        self.duration = duration
        self.automated = automated
        self.automated_duration = automated_duration
        self.planned = planned
        self.planned_duration = planned_duration

    def __add__(self, other):
        self.count += other.count
        self.duration += other.duration
        self.automated += other.automated
        self.automated_duration += other.automated_duration
        self.planned += other.planned
        self.planned_duration += other.planned_duration
        return self

    def __repr__(self):
        return 'count: {:>5d}, duration:{:>15s}, automated:{:>5d}, automated_duration:{:>15s}, planned:{:>5d}, planned_duration:{:>15s}'.format(
            self.count,
            timedelta_to_str(self.duration),
            self.automated,
            timedelta_to_str(self.automated_duration),
            self.planned,
            timedelta_to_str(self.planned_duration),
            )

    def to_dict(self):
        return dict(
            count=self.count,
            duration=timedelta_to_str(self.duration),
            automated=self.automated,
            automated_duration=timedelta_to_str(self.automated_duration),
            planned=self.planned,
            planned_duration=timedelta_to_str(self.planned_duration),
            )

    @classmethod
    def from_dict(cls, val):

        automated_status = AutoTestStatus(val['custom_autotest_status'] or 0)
        automated = automated_status == AutoTestStatus.AUTOMATED
        planned = automated_status == AutoTestStatus.PLANNED

        if val['estimate']:
            duration = str_to_timedelta(val['estimate'])
        else:
            duration = ZERO_TIMEDELTA

        return cls(
            count=1,
            duration=duration,
            automated=1 if automated else 0,
            automated_duration=duration if automated else ZERO_TIMEDELTA,
            planned=1 if planned else 0,
            planned_duration=duration if planned else ZERO_TIMEDELTA,
        )


def write_csv_results(path, first_column_name, stat_dict, total_stats):
    with path.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=[first_column_name] + list(total_stats.to_dict()))
        writer.writeheader()
        for priority, stats in stat_dict.items():
            writer.writerow({first_column_name: priority, **stats.to_dict()})
        writer.writerow({first_column_name: 'Total', **total_stats.to_dict()})


def process_cases(args):
    client = APIClient(args.url)
    client.user = args.user
    client.password = args.password
    priorities = {p['id']: p['name'] for p in client.send_get('get_priorities')}
    projects = client.send_get('get_projects')
    [project] = [project for project in projects if project['name'] == VMS_PROJECT_NAME]
    project_id = project['id']
    suites = client.send_get(f'get_suites/{project_id}')
    section_count = 0
    total_stats = Stats()
    stats_by_priority = {}
    stats_by_suites = {}
    for suite in suites:
        _logger.info("Process suite '%s'", suite['name'])
        suite_id = suite['id']
        sections = client.send_get(f'get_sections/{project_id}&suite_id={suite_id}')
        section_count += len(sections)
        suite_stat_item = Stats()
        for section in sections:
            _logger.info("Process section '%s.%s'", suite['name'], section['name'])
            section_id = section['id']
            cases = client.send_get(f'get_cases/{project_id}&suite_id={suite_id}&section_id={section_id}')
            for case in cases:
                try:
                    _logger.debug("Process case:\n%s", pprint.pformat(case))
                    case_status = CaseStatus(case.get('custom_test_case_status', 0) or 0)
                    if case_status in [CaseStatus.READY, CaseStatus.IN_REVIEW]:
                        case_stats_item = Stats.from_dict(case)
                        priority = priorities[case['priority_id']]
                        priority_stat_item = stats_by_priority.setdefault(priority, Stats())
                        priority_stat_item += case_stats_item
                        total_stats += case_stats_item
                        suite_stat_item += case_stats_item
                except Exception as exc:
                    _logger.error("Can't process case '%s.%s.%s': %r", suite['name'], section['name'], case['title'], exc)
                    raise
        stats_by_suites[suite['name']] = suite_stat_item

    if args.csv_dir_path:
        args.csv_dir_path.mkdir(parents=True, exist_ok=True)
        write_csv_results(
            args.csv_dir_path / 'priorities.csv',
            'priority',
            stats_by_priority,
            total_stats,
            )
        write_csv_results(
            args.csv_dir_path / 'suites.csv',
            'suite',
            stats_by_suites,
            total_stats,
            )
    else:
        suite_count = len(suites)
        suite_column_width = max(len(word) for word in stats_by_suites)
        priority_column_width = max(len(word) for word in stats_by_priority)
        first_column_width = max(suite_column_width, priority_column_width)
        print(f'Project {VMS_PROJECT_NAME}: suites={suite_count}, sections={section_count}')
        print('By priorities:')
        for priority, stats in stats_by_priority.items():
            print('  {}: {}'.format(priority.ljust(first_column_width), stats))
        print('By suites:')
        for suite, stats in stats_by_suites.items():
            print('  {}: {}'.format(suite.ljust(first_column_width), stats))
        print('  {}: {}'.format('Total'.ljust(first_column_width), total_stats))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Get VMS project metrics from NX TestRail"))
    parser.add_argument(
        '--url', default=TEST_RAIL_URL,
        help="NX TestRail URL, default=%(default)r..")
    parser.add_argument(
        '--user', help="NX TestRail user")
    parser.add_argument(
        '--password', help="NX TestRail password")
    parser.add_argument(
        '--csv-dir-path', type=Path, required=False,
        help="Output directory path to store results in CSV format.")
    parser.add_argument(
        '--verbose', '-v',
        action='store_const',
        const=logging.DEBUG,
        default=logging.INFO,
        dest='log_level',
        help="Show debug messages too.")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format='%(asctime)-15s %(levelname)7s %(message)s')
    process_cases(args)


if __name__ == '__main__':
    main()
