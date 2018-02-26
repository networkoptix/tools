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
from mercurial import MercurialWriter

log = logging.getLogger(__name__)


DEFAULT_CUSTOMIZATION = 'hanwha'
DEFAULT_CLOUD_GROUP = 'test'
DEFAULT_RELEASE = 'beta'
DOWNSTREAM_FUNTEST_PROJECT = 'funtest'
HG_BOOKMARK_FORMAT = '{branch}_stable'


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

    @property
    def deploy_webadmin_for_version(self):
        return True

    def get_project_parameters(self):
        default_platforms = set(self.config.ci.platforms)
        return BuildProject.get_project_parameters(self) + [
            BooleanProjectParameter(platform, 'Build platform %s' % platform, default_value=platform in default_platforms)
            for platform in self.all_platform_list
            ]

    def must_skip_this_build(self):
        nx_vms_scm_info = self.scm_info['nx_vms']
        host = LocalHost()
        result = host.run_command(
            ['hg', 'incoming', '--branch', nx_vms_scm_info.branch],
            cwd=os.path.join(self.workspace_dir, 'nx_vms'),
            check_retcode=False,
            )
        if result.exit_code == 0:
            log.warning('Have incoming commits for repository nx_vms; skipping this build')
            return True
        head = host.get_command_output(
            ['hg', 'heads', nx_vms_scm_info.branch, '--template={node|short}'],
            cwd=os.path.join(self.workspace_dir, 'nx_vms'),
            )
        if nx_vms_scm_info.revision != head:
            log.warning('Checked out nx_vms revision is %s, but head is already %s; skipping this build',
                            nx_vms_scm_info.revision, head)
            return True
        return False

    def post_process(self, build_info, build_info_path, platform_build_info_map):
        # set bookmark if all platform are built successfuly
        if build_info.failed_build_platform_list:
            return
        writer = MercurialWriter(
            repository_dir=os.path.join(self.workspace_dir, 'nx_vms'),
            repository_url=self.config.services.mercurial_repository_url.rstrip('/') + '/nx_vms',
            ssh_key_path=self.credentials.jenkins_hg_push.key_path,
            )
        writer.set_bookmark(HG_BOOKMARK_FORMAT.format(branch=self.nx_vms_branch_name))

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
