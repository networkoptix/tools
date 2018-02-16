# CI project for multibranch pipeline - build/test single customization, every platform on every commit

import logging
import os.path

from project_build import BuildProject
from command import (
    BooleanProjectParameter,
    BuildJobCommand,
    )
from host import LocalHost
from test_watcher_selector import make_email_recipient_list

log = logging.getLogger(__name__)


DEFAULT_CUSTOMIZATION = 'hanwha'
DEFAULT_CLOUD_GROUP = 'test'
DEFAULT_RELEASE = 'beta'
DOWNSTREAM_FUNTEST_PROJECT = 'funtest'


class CiProject(BuildProject):

    project_id = 'ci'

    @property
    def days_to_keep_old_builds(self):
        return self.config.ci.days_to_keep_old_builds

    @property
    def enable_concurrent_builds(self):
        return self.config.ci.enable_concurrent_builds

    @property
    def requested_platform_list(self):
        return [p for p in self.all_platform_list if self.params.get(p)]

    @property
    def customization(self):
        return DEFAULT_CUSTOMIZATION

    @property
    def requested_customization_list(self):
        return [self.customization]

    @property
    def release(self):
        return DEFAULT_RELEASE

    @property
    def cloud_group(self):
        return DEFAULT_CLOUD_GROUP

    @property
    def must_store_artifacts_in_different_customization_dirs(self):
        return False

    def get_project_parameters(self):
        default_platforms = set(self.config.ci.platforms)
        return BuildProject.get_project_parameters(self) + [
            BooleanProjectParameter(platform, 'Build platform %s' % platform, default_value=platform in default_platforms)
            for platform in self.all_platform_list
            ]

    def must_skip_this_build(self):
        nx_vms_scm_info = self.scm_info['nx_vms']
        host = LocalHost()
        head = host.get_command_output(
            ['hg', 'heads', nx_vms_scm_info.branch, '--template={node|short}'],
            cwd=os.path.join(self.workspace_dir, 'nx_vms'),
            )
        if nx_vms_scm_info.revision == head:
            return False
        log.warning('Checked out nx_vms revision is %s, but head is already %s; skipping this build',
                        nx_vms_scm_info.revision, head)
        return True

    def make_email_recipient_list(self, build_info):
        if self.in_assist_mode:
            return self.build_user_email_list
        if not build_info.has_failed_builds and build_info.has_failed_tests:
            return make_email_recipient_list(self.config.tests_watchers, build_info)
        return build_info.changeset_email_list

    def make_postprocess_command_list(self, failed_build_platform_list):
        # do we have any platform to test which is built?
        if set(self.config.fun_tests.platforms) - set(failed_build_platform_list):
            return [self._make_funtest_job_command()]
        else:
            return []
    
    def _make_funtest_job_command(self):
        return BuildJobCommand(
            job='{}/{}'.format(DOWNSTREAM_FUNTEST_PROJECT, self.nx_vms_branch_name),
            wait_for_completion=False,
            )
