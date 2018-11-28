#!/usr/bin/env python

from __future__ import print_function

import argparse
import jenkins
import os
import requests
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from mercurial_utils import HgContext


PLATFORMS = ['bpi', 'linux-x64', 'mac', 'windows-x64', 'webadmin']


def check_revision(rev):
    '''
    Validate if build passed on all platforms. Unit tests are ignored for now.
    '''
    response = requests.get('http://junkshop.enk.me/check_revision/{}'.format(rev))
    json = response.json()
    # Throws KeyError if something was not found
    return all(json[platform]['build'] == 'passed' for platform in PLATFORMS)


def wait_until_rev_checked(rev):
    while not check_revision(rev):
        time.sleep(5)


def get_build_url(server, id):
    info = server.get_queue_item(id)
    try:
        return info['executable']['url']
    except KeyError:
        print("Build is not started yet: {}".format(info['why']))
        return None


def validate_commit():
    hg = HgContext()
    phase = hg.execute("phase").split()[1]
    if phase != "public":
        hg.execute("push")
        # TODO: Launch custom build on jenkins?

    rev = hg.execute("id", "-i")
    # wait_until_rev_checked(rev)

    build_parameters = [
        ('BRANCH', 'validate_custom_build'),  # Actually that's only a junkshop id
        ('VMS_BUILD_CHOICE_OPTION', rev),
        ('PLATFORMS', 'linux-x64'),
        ('PLATFORMS', 'windows-x64'),
        ('PLATFORMS', 'mac'),
        ('BUILD_DESCRIPTION', 'Auto-validate: {}'.format(rev))
    ]
    print(build_parameters)

    server = jenkins.Jenkins(
        'http://jenkins2.enk.me',
        username='custom-build-trigger-script',
        password='password-for-custom-build-trigger-script')
    try:
        id = server.build_job('custom.any.preset.full', build_parameters)
        url = get_build_url(server, id)
        while not url:
            time.sleep(5)
            url = get_build_url(server, id)
        print(url)
    except jenkins.JenkinsException as e:
        print(repr(e))

    print("Success!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    validate_commit()
