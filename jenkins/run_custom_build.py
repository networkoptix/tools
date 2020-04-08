#!/usr/bin/env python3

import argparse
import logging
import requests

import sys
import time
from builtins import input
from distutils.util import strtobool
from jenkins_utils import JenkinsContext
from git_context import GitContext

BUILD_KEY = 'Auto-validate:'
BUILD_PLATFORMS = ['linux-x64', 'mac', 'windows-x64']
UNIT_TEST_PLATFORMS = ['linux-x64', 'windows-x64']
JUNKSHOP_CHECK_FREQUENCY_SECONDS = 60
JENKINS_SEARCH_DEPTH = 20

jenkins = JenkinsContext(
    url='http://jenkins.lan.hdw.mx',
    username='custom-build-trigger-script',
    password='11c2f31535f69907c429bf398f59658fb9',
    job_name='custom.any.preset.full',
    runner_name='custom.any.vms.runner')

git = GitContext()
build_id = '{} {} [{}]'.format(BUILD_KEY, git.rev, git.branch)


class JunkshopStatus:
    def __init__(self):
        self.build_ok = False
        self.tests_ok = False
        self.completed = False

    def __str__(self):
        return 'Completed: {}, Build: {}, Tests: {}'.format(
            self.completed, self.build_ok, self.tests_ok)


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


def check_junkshop_status():
    '''
    Validate if build passed on all platforms. Unit tests are ignored for now.
    '''
    url = 'http://junkshop.lan.hdw.mx/check_revision/{}'.format(git.rev)
    logging.debug("Junkshop request url: {}".format(url))
    response = requests.get(url)
    json = response.json()

    result = JunkshopStatus()
    if len(json) == 0:
        logging.debug("Json is empty")
        return None

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


def check_jenkins_status(depth=None):
    job_status = jenkins.job_status(description=build_id, depth=depth)
    if job_status:
        print("Build was found on jenkins, see {}".format(job_status.url))
    return job_status


def list_jenkins_builds(print_all=False, depth=None):
    only_running = not print_all
    print("All builds:" if print_all else "Running builds:")
    for build in jenkins.list_builds(only_running=only_running, depth=depth):
        print(build)


def start_jenkins_build():
    build_parameters = [
        ('BRANCH', 'validate_custom_build'),  # Actually that's only a junkshop id
        ('VMS_BUILD_CHOICE_OPTION', git.rev),
        ('VMS_BUILD_CHOICE', 'VMS_NEW_BUILD_BY_COMMIT'),
        ('BUILD_DESCRIPTION', build_id),
        ('UT_ENABLED', 'ON'),
    ]
    for platform in BUILD_PLATFORMS:
        build_parameters += [('PLATFORMS', platform)]
    url = jenkins.start_build(parameters=build_parameters)
    print(url)


def wait_until_rev_checked():
    print("Waiting for build to complete")
    junkshop_status = check_junkshop_status()
    while not junkshop_status or not junkshop_status.completed:
        time.sleep(JUNKSHOP_CHECK_FREQUENCY_SECONDS)
        junkshop_status = check_junkshop_status()
        logging.debug("Current status is {}".format(junkshop_status))
    return junkshop_status


def get_build_url(server, id):
    info = server.get_queue_item(id)
    try:
        return info['executable']['url']
    except KeyError:
        print("Build is not started yet: {}".format(info['why']))
        return None


def validate_commit(depth=None, force=False):
    print("Validating revision {} [{}]".format(git.rev, git.branch))

    if force:
        start_jenkins_build()

    junkshop_status = check_junkshop_status()
    if not junkshop_status:
        print("Build was not found on junkshop, looking up on jenkins")
        jenkins_status = check_jenkins_status(depth)
        if not jenkins_status:
            confirm("Build was not found on jenkins. Launch new build?")
            start_jenkins_build()
        elif not jenkins_status.running:
            confirm("Build on jenkins is finished with result '{}'. Launch new build?".format(
                jenkins_status.result))
            start_jenkins_build()
    if not junkshop_status or not junkshop_status.completed:
        junkshop_status = wait_until_rev_checked()
    print("Job finished, status: {}".format(junkshop_status))


def cancel_build(build_number=None, depth=None):
    if not build_number:
        jenkins_status = check_jenkins_status(depth)
        if not jenkins_status:
            print("Build [{}] was not found".format(build_id))
            return
        build_number = jenkins_status.number
    print("Cancelling build {}".format(build_number))
    status, runner_status = jenkins.cancel_build(build_number=build_number)
    print(status)
    print(runner_status)


def validate_command(args):
    validate_commit(args.depth, args.force)


def list_command(args):
    list_jenkins_builds(args.all, args.depth)


def cancel_command(args):
    cancel_build(args.id, args.depth)


def _setup_validation_parser(parser):
    parser.add_argument('-f', '--force', help="Force start build", action='store_true')
    parser.add_argument('-d', '--depth', help="Jenkins search depth", type=int)
    parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    _setup_validation_parser(parser)

    subparsers = parser.add_subparsers(title="actions", dest='cmd')

    parser_validate = subparsers.add_parser('validate', help='Validate given revision (default)')
    _setup_validation_parser(parser_validate)
    parser_validate.set_defaults(func=validate_command)

    parser_list = subparsers.add_parser('list', help='List running builds')
    parser_list.add_argument(
        '-a',
        '--all',
        help="List all builds including completed",
        action='store_true')
    parser_list.add_argument('-d', '--depth', help="Jenkins search depth", type=int)
    parser_list.add_argument('-v', '--verbose', help="Verbose output", action='store_true')
    parser_list.set_defaults(func=list_command)

    parser_cancel = subparsers.add_parser('cancel', help='Cancel running build')
    parser_cancel.add_argument('-v', '--verbose', help="Verbose output", action='store_true')
    cancel_target_group = parser_cancel.add_mutually_exclusive_group()
    cancel_target_group.add_argument('-i', '--id', help="Build id", type=int)
    parser_cancel.set_defaults(func=cancel_command)

    args = parser.parse_args()
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level)

    if not args.cmd:
        validate_command(args)
    else:
        args.func(args)
