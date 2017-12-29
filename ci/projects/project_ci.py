# CI project for multibranch pipeline - build/test single customization, every platform on every commit

import logging
import os.path
import glob
import sys
import time

from junk_shop import models
from project_build import BuildProject
from command import (
    ScriptCommand,
    CleanDirCommand,
    ParallelCommand,
    BooleanProjectParameter,
    )
from email_sender import EmailSender

log = logging.getLogger(__name__)


DEFAULT_CUSTOMIZATION = 'default'
DEFAULT_CLOUD_GROUP = 'test'
DEFAULT_RELEASE = 'beta'
CLEAN_STAMP_PATH = 'clean.stamp'
CLEAN_BUILD_STAMP_PATH = 'clean-build.stamp'


class CiProject(BuildProject):

    project_id = 'ci'

    def get_project_parameters(self):
        return BuildProject.get_project_parameters(self) + [
            BooleanProjectParameter(platform, 'Build platform %s' % platform, default_value=True)
            for platform in self.all_platform_list
            ]

    @property
    def requested_platform_list(self):
        return [p for p in self.all_platform_list if self.params.get(p)]

    def create_build_parameters(self, platform=None):
        return BuildProject.create_build_parameters(
            self,
            platform,
            customization=DEFAULT_CUSTOMIZATION,
            release=DEFAULT_RELEASE,
            cloud_group=DEFAULT_CLOUD_GROUP,
            )

    def stage_prepare_for_build(self):
        self.init_build_info()
        self.init_clean_stamps()

        job_list = [self.make_parallel_job(platform) for platform in self.requested_platform_list]
        return [
            ParallelCommand(job_list),
            self.make_python_stage_command('finalize'),
            ]

    def init_clean_stamps(self):
        self.load_all_clean_stamps()
        if self.params.clean or self.params.clean_only or not self.state.clean_stamp:
            self.state.clean_stamp = self.make_stamp()
        if self.params.clean_build or not self.state.clean_build_stamp:
            self.state.clean_build_stamp = self.make_stamp()
        self.save_all_clean_stamps()

    def make_parallel_job(self, platform):
        job_name = platform
        workspace_dir = self.workspace_dir(platform)
        return BuildProject.make_parallel_job(self, job_name, workspace_dir, platform)

    def workspace_dir(self, platform):
        if self.in_assist_mode:
            return 'psa-ci-{}-{}'.format(self.jenkins_env.job_name, platform)
        else:
            return 'ci-{}-{}'.format(self.nx_vms_branch_name, platform)

    def stage_node(self, platform, phase=1):
        log.info('Node stage: %s (phase#%s)', self.current_node, phase)
        
        node_clean_stamp = self.load_clean_stamp()  # stamp of this node
        if node_clean_stamp and node_clean_stamp != self.state.clean_stamp:
            log.info('This node was cleaned before last clean was requested - cleaning working dir now')
            assert phase == 1, repr(phase)  # must never happen on phase 2
            return [CleanDirCommand()] + self.make_node_stage_command_list(platform=platform, phase=2)
        if not node_clean_stamp:  # this was clean - save it's stamp to this node
            self.save_clean_stamp()

        clean_build = self.params.clean_build
        node_clean_build_stamp = self.load_clean_build_stamp()  # stamp of this node
        if not clean_build and node_clean_build_stamp and node_clean_build_stamp != self.state.clean_build_stamp:
            log.info("This node's build dir was cleaned before last clean build was requested - cleaning it now")
            clean_build = True
        self.save_clean_build_stamp()

        platform_config = self.config.platforms[platform]
        platform_branch_config = self.branch_config.platforms.get(platform)
        junk_shop_repository = self.create_junk_shop_repository(platform=platform)

        build_info = self._build(junk_shop_repository, platform_branch_config, platform_config, clean_build)
        if platform_config.should_run_unit_tests and build_info.is_succeeded:
            self.run_unit_tests(junk_shop_repository, build_info, self.config.ci.timeout)

        return self.post_build_actions(junk_shop_repository, build_info)

    def stage_finalize(self):
        nx_vms_scm_info = self.scm_info['nx_vms']
        self.db_config.bind(models.db)
        smtp_password = self.credentials.service_email
        project = self.project_name
        branch = nx_vms_scm_info.branch
        build_num = self.jenkins_env.build_number
        sender = EmailSender(self.config)
        build_info = sender.render_and_send_email(smtp_password, project, branch, build_num, test_mode=self.in_assist_mode)
        return self.make_set_build_result_command_list(build_info)

    def load_all_clean_stamps(self):
        self.state.clean_stamp = self.load_clean_stamp()
        self.state.clean_build_stamp = self.load_clean_build_stamp()

    def load_clean_stamp(self):
        return self._load_stamp(CLEAN_STAMP_PATH)

    def load_clean_build_stamp(self):
        return self._load_stamp(CLEAN_BUILD_STAMP_PATH)

    def save_all_clean_stamps(self):
        self.save_clean_stamp()
        self.save_clean_build_stamp()

    def save_clean_stamp(self):
        self._save_stamp(self.state.clean_stamp, CLEAN_STAMP_PATH)

    def save_clean_build_stamp(self):
        self._save_stamp(self.state.clean_build_stamp, CLEAN_BUILD_STAMP_PATH)

    def _load_stamp(self, file_path):
        if not os.path.isfile(file_path):
            return None
        with open(file_path) as f:
            return int(f.read().strip())

    def _save_stamp(self, stamp, file_path):
        if not stamp: return  # do not save None
        with open(file_path, 'w') as f:
            f.write(str(stamp))

    def make_stamp(self):
        return int(time.time())
