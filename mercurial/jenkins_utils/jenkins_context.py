from __future__ import print_function

import logging
import re
import time
import jenkins

DEFAULT_SEARCH_DEPTH = 20
RUN_BUILD_CHECK_FREQUENCY_SECONDS = 5


class JenkinsBuildStatus:
    def __init__(self, build_info):
        self.description = build_info['description'].split('\n')[0]
        self.running = build_info['building']
        self.result = build_info['result']
        self.url = build_info['url']
        self.number = build_info['number']
        self.runner = 0
        if 'runner' in build_info['description']:
            self.runner = int(re.search(
                ".*/(\d+)/'.*",
                build_info['description'].split('\n')[1]).group(1))

    def __str__(self):
        return '{}: {}. {}. Url: {}. Runner {}'.format(
            self.number,
            self.description,
            self.result if not self.running else 'Running',
            self.url,
            self.runner)

    def __repr__(self):
        return 'JenkinsBuildStatus ({})'.format(self.__str__)


class JenkinsContext:
    def __init__(self, url, username, password, job_name=None, runner_name=None):
        self._jenkins = jenkins.Jenkins(url, username=username, password=password)
        self._job_name = job_name
        self._runner_name = runner_name

    def _get_build_url(self, id):
        info = self._jenkins.get_queue_item(id)
        try:
            return info['executable']['url']
        except KeyError:
            logging.debug("Build is not started yet: {}".format(info['why']))
            return None

    def _status(self, job_name, build_number):
        logging.debug("Requesting build info for build {} on {}".format(build_number, job_name))
        build_info = self._jenkins.get_build_info(job_name, build_number)
        return JenkinsBuildStatus(build_info) if build_info else None

    def job_status(self, description, job_name=None, depth=None):
        job_name = job_name or self._job_name
        depth = depth or DEFAULT_SEARCH_DEPTH
        job_info = self._jenkins.get_job_info(job_name)

        for build in job_info['builds'][:depth]:
            build_number = build['number']
            status = self._status(job_name, build_number)
            if description in status.description:
                return status
        return None

    def list_builds(self, job_name=None, only_running=True, depth=None):
        job_name = job_name or self._job_name
        depth = depth or DEFAULT_SEARCH_DEPTH
        job_info = self._jenkins.get_job_info(job_name)
        for build in job_info['builds'][:depth]:
            build_number = build['number']
            status = self._status(job_name, build_number)
            if status.running or not only_running:
                yield status

    def start_build(self, job_name=None, parameters=None):
        job_name = job_name or self._job_name
        logging.debug("Starting build with parameters {}".format(parameters))
        try:
            id = self._jenkins.build_job(job_name, parameters)
            url = self._get_build_url(id)
            while not url:
                time.sleep(RUN_BUILD_CHECK_FREQUENCY_SECONDS)
                url = self._get_build_url(id)
            return url
        except jenkins.JenkinsException as e:
            logging.info(repr(e))
            return None

    def cancel_build(self, build_number, job_name=None, runner_name=None):
        job_name = job_name or self._job_name
        runner_name = runner_name or self._runner_name
        logging.debug("Cancelling build {}".format(build_number))
        status = self._status(job_name, build_number)
        runner_status = self._status(runner_name, status.runner)
        while runner_status.running:
            self._jenkins.stop_build(runner_name, status.runner)
            time.sleep(RUN_BUILD_CHECK_FREQUENCY_SECONDS)
            runner_status = self._status(runner_name, status.runner)
        while status.running:
            self._jenkins.stop_build(job_name, build_number)
            time.sleep(RUN_BUILD_CHECK_FREQUENCY_SECONDS)
            status = self._status(job_name, build_number)
        return (status, runner_status)
