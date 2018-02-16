# Release project for multibranch pipeline - build/test requested customizations and platforms on user request

import logging

from project_build import BuildProject
from command import (
    ChoiceProjectParameter,
    MultiChoiceProjectParameter,
    )
from deploy import Deployer

log = logging.getLogger(__name__)


CLOUD_GROUP_LIST = [
    'test',
    'tmp',
    'dev',
    'demo',
    'stage',
    'prod',
    ]


class ReleaseProject(BuildProject):

    project_id = 'release'

    def must_actually_do_build(self):
        if not self.jenkins_env.build_user:
            return False  # do not build if triggered by multibranch scan, just update project properties
        return super(ReleaseProject, self).must_actually_do_build()

    @property
    def days_to_keep_old_builds(self):
        return self.config.release.days_to_keep_old_builds

    @property
    def enable_concurrent_builds(self):
        return self.config.release.enable_concurrent_builds

    @property
    def requested_platform_list(self):
        platform_list = self.params.get('platform_list')
        if not platform_list:
            return []
        return [p for p in self.all_platform_list if p in platform_list.split(',')]

    @property
    def release(self):
        return self.params.release

    @property
    def cloud_group(self):
        return self.params.cloud_group

    @property
    def customization(self):
        return None  # no customization for models.Build; each root models.Run will have it's own

    @property
    def requested_customization_list(self):
        customization_list = self.params.get('customization_list')
        if not customization_list:
            return []
        return [c for c in self.config.customization_list if c in customization_list.split(',')]

    @property
    def must_store_artifacts_in_different_customization_dirs(self):
        return True

    @property
    def add_qt_pdb_by_default(self):
        return True

    @property
    def run_unit_tests_by_default(self):
        return False

    def get_project_parameters(self):
        return BuildProject.get_project_parameters(self) + [
            ChoiceProjectParameter('release', 'Build beta or release', ['beta', 'release']),
            ChoiceProjectParameter('cloud_group', 'Cloud group', CLOUD_GROUP_LIST),
            MultiChoiceProjectParameter('platform_list', 'Platforms to build',
                                            choices=self.all_platform_list, selected_choices=['linux-x64']),
            MultiChoiceProjectParameter('customization_list', 'Customizations to build',
                                            choices=self.config.customization_list, selected_choices=['default']),
            ]

    def deploy_artifacts(self, build_info_path, platform_build_info_map):
        deployer = Deployer(
            config=self.config,
            artifacts_stored_in_different_customization_dirs=self.must_store_artifacts_in_different_customization_dirs,
            ssh_key_file=self.credentials.deploy.key_path,
            build_num=self.jenkins_env.build_number,
            branch=self.nx_vms_branch_name,
            )
        deployer.deploy_artifacts(
            customization_list=self.requested_customization_list,
            platform_list=self.requested_platform_list,
            build_info_path=build_info_path,
            platform_build_info_map=platform_build_info_map,
            )

    def make_email_recipient_list(self, build_info):
        return self.build_user_email_list
