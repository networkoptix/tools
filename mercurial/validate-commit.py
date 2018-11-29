#!/usr/bin/env python

from __future__ import print_function

import argparse
import jenkins
import logging
import requests
import sys
import time
from builtins import input
from distutils.util import strtobool
from mercurial_utils import HgContext

BUILD_KEY = 'Auto-validate:'
BUILD_PLATFORMS = ['bpi', 'linux-x64', 'mac', 'windows-x64']
UNIT_TEST_PLATFORMS = ['linux-x64', 'windows-x64']
JENKINS_URL = 'http://jenkins2.enk.me'
JENKINS_USER = 'custom-build-trigger-script'
JENKINS_PASSWORD = 'password-for-custom-build-trigger-script'
JENKINS_JOB_NAME = 'custom.any.preset.full'


class JunkshopStatus:
    def __init__(self):
        self.present = False
        self.build_ok = False
        self.tests_ok = False
        self.completed = False

    def __str__(self):
        if not self.present:
            return 'Absent'
        return 'Completed: {}, Build: {}, Tests: {}'.format(
            self.completed, self.build_ok, self.tests_ok)


class JenkinsStatus:
    def __init__(self):
        self.present = False
        self.running = False


def ask_question(question):
    print('{} [y/n]'.format(question))
    while True:
        try:
            return strtobool(input().lower())
        except ValueError:
            print('Please respond with \'y\' or \'n\'.\n')


def confirm(question):
    if not ask_question(question):
        sys.exit(1)


def ensure_revision_is_public(hg, rev):
    while hg.phase(rev) != "public":
        confirm("Revision is not public. Push it?")
        hg.push(rev=rev, new_branch=True)


def make_build_id(rev):
    return ' '.join([BUILD_KEY, rev])


def check_junkshop_status(rev):
    '''
    Validate if build passed on all platforms. Unit tests are ignored for now.
    '''
    url = 'http://junkshop.enk.me/check_revision/{}'.format(rev)
    logging.debug("Junkshop request url: {}".format(url))
    response = requests.get(url)
    json = response.json()

    result = JunkshopStatus()
    if len(json) == 0:
        logging.debug("Json is empty")
        return result

    result.present = True
    try:
        # If webadmin failed, nothing will be built further.
        if json['webadmin']['build'] != 'passed':
            logging.debug("Webadmin failed")
            result.completed = True
            result.build_ok = False
            return result

        completed = True
        build_ok = True
        tests_ok = True
        for platform in BUILD_PLATFORMS:
            if not json[platform]['build']:
                logging.debug("Platform {} was not found".format(platform))
                completed = False
            elif json[platform]['build'] != 'passed':
                logging.debug("Platform {} was failed to build".format(platform))
                build_ok = False
            elif platform in UNIT_TEST_PLATFORMS and json[platform]['unit'] != 'passed':
                logging.debug("Platform {} unit tests failed".format(platform))
                tests_ok = False

        result.completed = completed
        result.build_ok = build_ok
        result.tests_ok = tests_ok
    except KeyError as e:
        logging.debug("Key {} was not found in the json".format(e))
    return result


def check_jenkins_status(rev):
    build_id = make_build_id(rev)
    server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USER, password=JENKINS_PASSWORD)
    job_info = server.get_job_info(JENKINS_JOB_NAME)

    result = JenkinsStatus()
    for build in job_info['builds']:
        build_number = build['number']
        build_info = server.get_build_info(JENKINS_JOB_NAME, build_number)
        description = build_info['description']
        if build_id in description:
            print("Build was found on jenkins, see {}".format(build_info['url']))
            result.present = True
            result.running = build_info['building']
            return result
    return result


def start_jenkins_build(rev):
    server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USER, password=JENKINS_PASSWORD)
    build_parameters = [
        ('BRANCH', 'validate_custom_build'),  # Actually that's only a junkshop id
        ('VMS_BUILD_CHOICE_OPTION', rev),
        ('BUILD_DESCRIPTION', make_build_id(rev))
    ]
    for platform in BUILD_PLATFORMS:
        build_parameters += [('PLATFORMS', platform)]
    logging.debug("Starting build with parameters {}".format(build_parameters))

    try:
        id = server.build_job(JENKINS_JOB_NAME, build_parameters)
        url = get_build_url(server, id)
        while not url:
            time.sleep(5)
            url = get_build_url(server, id)
        print(url)
    except jenkins.JenkinsException as e:
        print(repr(e))


def wait_until_rev_checked(rev):
    print("Waiting for build to complete")
    junkshop_status = check_junkshop_status(rev)
    while not junkshop_status.completed:
        time.sleep(5)
        junkshop_status = check_junkshop_status(rev)
        logging.debug("Current status is {}".format(junkshop_status))
    print("Job finished, status: {}".format(junkshop_status))


def get_build_url(server, id):
    info = server.get_queue_item(id)
    try:
        return info['executable']['url']
    except KeyError:
        print("Build is not started yet: {}".format(info['why']))
        return None


def validate_commit(rev=None):
    hg = HgContext()
    if not rev:
        rev = hg.execute("id", "-i")
    logging.debug("Validating revision {}".format(rev))

    ensure_revision_is_public(hg, rev)

    junkshop_status = check_junkshop_status(rev)
    if not junkshop_status.present:
        print("Build was not found on junkshop, looking up on jenkins")
        jenkins_status = check_jenkins_status(rev)
        if not jenkins_status.present:
            confirm("Build was not found on jenkins. Launch new build?")
            start_jenkins_build(rev)
        elif not jenkins_status.running:
            confirm("Build on jenkins is aborted. Launch new build?")
            start_jenkins_build(rev)
    wait_until_rev_checked(rev)
    print("Success!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--rev', help="Revision to check")
    parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true')
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level)

    validate_commit(args.rev)
