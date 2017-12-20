# CI project for multibranch pipeline - build/test single customization, every platform on every commit

import logging
import os.path
import glob
import sys

from pony.orm import db_session

from junk_shop import (
    models,
    DbConfig,
    BuildParameters,
    DbCaptureRepository,
    update_build_info,
    store_output_and_exit_code,
    run_unit_tests,
    )
from project_build import BuildProject
from command import (
    ScriptCommand,
    ArchiveArtifactsCommand,
    CleanDirCommand,
    NodeCommand,
    PrepareVirtualEnvCommand,
    ParallelJob,
    ParallelCommand,
    SetBuildResultCommand,
    BooleanProjectParameter,
    )
from cmake import CMake
from build import CMakeBuilder
from email_sender import EmailSender

log = logging.getLogger(__name__)


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

    def stage_prepare_for_build(self):
        junk_shop_repository = self.create_junk_shop_repository()
        update_build_info(junk_shop_repository, 'nx_vms')

        job_list = [self.make_platform_job(platform) for platform in self.requested_platform_list]
        return [
            ParallelCommand(job_list),
            self.make_python_stage_command('finalize'),
            ]

    def make_platform_job(self, platform):
        branch_name = self.nx_vms_branch_name
        platform_config = self.config.platforms[platform]
        node = platform_config.build_node
        workspace_dir = self.workspace_dir(self.jenkins_env.job_name, branch_name, platform)
        job_command_list = []
        if self.params.clean or self.params.clean_only:
            job_command_list += [
                CleanDirCommand(),
                ]
        if not self.params.clean_only:
            job_command_list += [
                self.prepare_devtools_command,
                ] + self.prepare_nx_vms_command_list + [
                PrepareVirtualEnvCommand(self.devtools_python_requirements),
                self.make_python_stage_command('node', platform=platform),
                ]
        return ParallelJob(platform, [NodeCommand(node, workspace_dir, job_command_list)])

    @property
    def nx_vms_branch_name(self):
        if self.in_assist_mode:
            return self.params.branch or DEFAULT_ASSIST_MODE_VMS_BRANCH
        else:
            assert self.jenkins_env.branch_name, (
                'This scripts are intented to be used in multibranch projects only;'
                ' env.BRANCH_NAME must be defined')
            return self.jenkins_env.branch_name

    @property
    def project_name(self):
        if self.in_assist_mode:
            return 'assist-ci-%s' % self.jenkins_env.job_name
        else:
            return self.project_id

    def workspace_dir(self, job_name, branch_name, platform):
        if self.in_assist_mode:
            return 'psa-%s-%s' % (job_name, platform)
        else:
            return 'ci-%s-%s' % (branch_name, platform)

    def stage_node(self):
        log.info('Node stage: %s', self.current_node)
        platform = self.current_command.platform
        platform_config = self.config.platforms[platform]
        platform_branch_config = self.branch_config.platforms.get(platform)
        junk_shop_repository = self.create_junk_shop_repository(platform)

        build_info = self._build(junk_shop_repository, platform_branch_config, platform_config)
        if platform_config.should_run_unit_tests and build_info.is_succeeded:
            self.run_unit_tests(junk_shop_repository, build_info, self.config.ci.timeout)

        if self.has_artifacts(build_info.artifact_mask_list):
            command_list = [ArchiveArtifactsCommand(build_info.artifact_mask_list)]
        else:
            error = 'No artifacts were produced matching masks: {}'.format(', '.join(build_info.artifact_mask_list))
            self.add_build_error(error)
            command_list = []

        self.save_build_errors_artifact(junk_shop_repository, build_info)
        # command_list = self.list_dirs_command_list
        return command_list

    def add_build_error(self, error):
        log.error(error)
        self._build_error_list.append(error)

    @property
    def list_dirs_command_list(self):
        if self.is_unix:
            return [
                ScriptCommand('pwd'),
                ScriptCommand('ls -alh'),
                ScriptCommand('ls -alh build'),
                ]
        else:
            return [
                ScriptCommand('dir'),
                ScriptCommand('dir build'),
                ]

    def create_junk_shop_repository(self, platform=None):
        nx_vms_scm_info = self.scm_info['nx_vms']
        project = self.project_name
        is_incremental = not (self.params.clean or self.params.clean_build)
        build_params = BuildParameters(
            project=project,
            platform=platform,
            build_num=self.jenkins_env.build_number,
            branch=nx_vms_scm_info.branch,
            configuration='release',
            cloud_group='test',
            customization='default',
            is_incremental=is_incremental,
            jenkins_url=self.jenkins_env.build_url,
            repository_url=nx_vms_scm_info.repository_url,
            revision=nx_vms_scm_info.revision,
            )
        return DbCaptureRepository(self.db_config, build_params)

    @property
    def db_config(self):
        user, password = self.credentials.junk_shop_db.split(':')
        return DbConfig(self.config.junk_shop.db_host, user, password)

    def _build(self, junk_shop_repository, platform_branch_config, platform_config):
        cmake = CMake('3.9.6')
        cmake.ensure_required_cmake_operational()

        builder = CMakeBuilder(cmake)
        build_info = builder.build(
            junk_shop_repository, platform_config, platform_branch_config, 'nx_vms', 'build', self.params.clean_build)
        return build_info

    def run_unit_tests(self, junk_shop_repository, build_info, timeout):
        if self.is_unix:
            ext = ''
        else:
            ext = '.exe'
        unit_test_mask_list = os.path.join(build_info.unit_tests_bin_dir, '*_ut%s' % ext)
        test_binary_list = [os.path.basename(path) for path in glob.glob(unit_test_mask_list)]
        if not test_binary_list:
            self.add_build_error('No unit tests were produced matching masks: {}'.format(unit_test_mask_list))
            return
        log.info('Running unit tests: %s', ', '.join(test_binary_list))
        logging.getLogger('junk_shop.unittest').setLevel(logging.INFO)  # Prevent from logging unit tests stdout/stderr
        is_passed = run_unit_tests(
            junk_shop_repository, build_info.current_config_path, build_info.unit_tests_bin_dir, test_binary_list, timeout)
        log.info('Unit tests are %s', 'passed' if is_passed else 'failed')

    def has_artifacts(self, artifact_mask_list):
        for mask in artifact_mask_list:
            if glob.glob(mask):
                return True
        else:
            return False

    @db_session
    def save_artifacts_missing_error(self, repository, build_info):
        run = models.Run[build_info.run_id]
        errors = 'No artifacts were produced matching masks: {}'.format(', '.join(build_info.artifact_mask_list))
        log.error(errors)
        repository.add_artifact(
            run, 'errors', 'errors', repository.artifact_type.output, errors, is_error=True)

    @db_session
    def save_build_errors_artifact(self, repository, build_info):
        if not self._build_error_list:
            return
        run = models.Run[build_info.run_id]
        repository.add_artifact(
            run, 'errors', 'errors', repository.artifact_type.output, '\n'.join(self._build_error_list), is_error=True)

    def stage_finalize(self):
        nx_vms_scm_info = self.scm_info['nx_vms']
        self.db_config.bind(models.db)
        smtp_password = self.credentials.service_email
        project = self.project_name
        branch = nx_vms_scm_info.branch
        build_num = self.jenkins_env.build_number
        sender = EmailSender(self.config)
        build_info = sender.render_and_send_email(smtp_password, project, branch, build_num, test_mode=self.in_assist_mode)
        if build_info.has_failed_builds:
            build_result = 'FAILURE'
        elif build_info.has_failed_tests:
            build_result = 'UNSTABLE'
        else:
            return
        return [SetBuildResultCommand(build_result)]
