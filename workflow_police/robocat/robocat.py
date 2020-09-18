#!/usr/bin/env python3

import gitlab

import time
import logging
import argparse

import merge_request_handler

logger = logging.getLogger(__name__)


class Bot:
    def __init__(self, project_id, dry_run):
        self._gitlab = gitlab.Gitlab.from_config("nx_gitlab")
        self._project = self._gitlab.projects.get(project_id)
        self._handler = merge_request_handler.MergeRequestHandler(self._project)

        self._gitlab.auth()
        self._username = self._gitlab.user.username
        self._dry_run = dry_run

    def start(self, mr_poll_rate):
        logger.info(f"Started for project [{self._project.name}] with {mr_poll_rate} secs poll rate"
                    + (" (--dry-run)" if self._dry_run else ""))

        for mr in self.get_merge_requests(mr_poll_rate):
            ignore_reason = self._handler.handle(merge_request_handler.MergeRequest(mr, self._dry_run))
            if ignore_reason:
                logger.info(f"MR!{mr.iid}: Ignored because {ignore_reason}")

    def get_merge_requests(self, mr_poll_rate):
        while True:
            start_time = time.time()
            for mr in self._project.mergerequests.list(state='opened', order_by='updated_at'):
                if mr.work_in_progress:
                    continue
                if not mr.assignee or mr.assignee["username"] != self._username:
                    continue
                yield mr

            sleep_time = max(0, start_time + mr_poll_rate - time.time())
            time.sleep(sleep_time)


def main():
    parser = argparse.ArgumentParser("workflow_robocat")
    parser.add_argument('-p', '--project-id', help="ID of project in gitlab", required=True)
    parser.add_argument('--mr-poll-rate', help="Merge requests polling rate in seconds ", type=int, default=30)
    parser.add_argument('--log-level', help="Logs level", choices=logging._nameToLevel.keys(), default=logging.INFO)
    parser.add_argument('--dry-run', help="Run single iteration, don't change any states", action="store_true")
    arguments = parser.parse_args()

    logging.basicConfig(
        level=arguments.log_level,
        format='%(asctime)s %(levelname)s %(name)s\t%(message)s')

    bot = Bot(arguments.project_id, arguments.dry_run)
    bot.start(arguments.mr_poll_rate)


if __name__ == '__main__':
    main()
