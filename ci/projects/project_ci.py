# CI project for multibranch pipeline - build/test single customization, every platform on every commit

import logging

from project_build import BuildProject
from command import (
    BooleanProjectParameter,
    BuildJobCommand,
    )

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

    def make_build_job_name(self, customization, platform):
        return platform

    def get_project_parameters(self):
        default_platforms = set(self.config.ci.platforms)
        return BuildProject.get_project_parameters(self) + [
            BooleanProjectParameter(platform, 'Build platform %s' % platform, default_value=platform in default_platforms)
            for platform in self.all_platform_list
            ]

    def send_result_email(self, sender, smtp_password, project, branch, build_num):
        build_info = sender.render_and_send_email(smtp_password, project, branch, build_num, test_mode=self.in_assist_mode)
        return build_info

    def make_final_processing_command_list(self, build_info):
        return (BuildProject.make_final_processing_command_list(self, build_info) +
                [self._make_funtest_job_command()])
    
    def _make_funtest_job_command(self):
        return BuildJobCommand(
            job='{}/{}'.format(DOWNSTREAM_FUNTEST_PROJECT, self.nx_vms_branch_name),
            wait_for_completion=False,
            )
