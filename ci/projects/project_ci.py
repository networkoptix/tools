# CI project for multibranch pipeline - build/test single customization, every platform on every commit

import logging

from junk_shop import models
from project_build import BuildProject
from command import (
    ScriptCommand,
    CleanDirCommand,
    ParallelCommand,
    BooleanProjectParameter,
    BuildJobCommand,
    )
from email_sender import EmailSender

log = logging.getLogger(__name__)


DEFAULT_CUSTOMIZATION = 'hanwha'
DEFAULT_CLOUD_GROUP = 'test'
DEFAULT_RELEASE = 'beta'
DOWNSTREAM_FUNTEST_PROJECT = 'funtest'


class CiProject(BuildProject):

    project_id = 'ci'

    def get_project_parameters(self):
        default_platforms = set(self.config.ci.platforms)
        return BuildProject.get_project_parameters(self) + [
            BooleanProjectParameter(platform, 'Build platform %s' % platform, default_value=platform in default_platforms)
            for platform in self.all_platform_list
            ]

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

    def stage_prepare_for_build(self):
        self.clean_stamps.init_master(self.params)
        self.init_build_info()

        job_list = [self.make_parallel_job(platform) for platform in self.requested_platform_list]
        return [
            ParallelCommand(job_list),
            self.make_python_stage_command('finalize'),
            ]

    def make_parallel_job(self, platform):
        job_name = platform
        workspace_dir = self.make_workspace_dir(platform)
        return BuildProject.make_parallel_job(self, job_name, workspace_dir, platform)

    def make_workspace_dir(self, platform):
        if self.in_assist_mode:
            return 'psa-ci-{}-{}'.format(self.jenkins_env.job_name, platform)
        else:
            return 'ci-{}-{}'.format(self.nx_vms_branch_name, platform)

    def stage_node(self, platform, phase=1):
        log.info('Node stage: %s (phase#%s)', self.current_node, phase)

        if self.clean_stamps.check_must_clean_node():
            assert phase == 1, repr(phase)  # must never happen on phase 2
            return [CleanDirCommand()] + self.make_node_stage_command_list(platform=platform, phase=2)

        return self.run_build_node_job(DEFAULT_CUSTOMIZATION, platform)

    def stage_finalize(self):
        nx_vms_scm_info = self.scm_info['nx_vms']
        self.db_config.bind(models.db)
        smtp_password = self.credentials.service_email
        project = self.project_name
        branch = nx_vms_scm_info.branch
        build_num = self.jenkins_env.build_number
        sender = EmailSender(self.config)
        build_info = sender.render_and_send_email(smtp_password, project, branch, build_num, test_mode=self.in_assist_mode)
        return self.do_final_processing(build_info, separate_customizations=False) + [self._make_funtest_job_command()]

    def _make_funtest_job_command(self):
        return BuildJobCommand(
            job='{}/{}'.format(DOWNSTREAM_FUNTEST_PROJECT, self.nx_vms_branch_name),
            wait_for_completion=False,
            )
