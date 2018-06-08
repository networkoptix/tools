# Release project for multibranch pipeline - build/test requested customizations and platforms on user request

import logging

from build import bool_to_cmake_param
from project_build import VERSION_FILE, BuildProject
from command import (
    StringProjectParameter,
    BooleanProjectParameter,
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
    def checkout_nx_vms_revision(self):
        return self.params.get('revision') or None

    @property
    def custom_cmake_args(self):
        args = '-DwithClouds=%s' % bool_to_cmake_param(self.params.withClouds or False)
        if self.params.custom_cmake_args:
            args = args + ' ' + self.params.custom_cmake_args
        return args

    @property
    def run_unit_tests_by_default(self):
        return False

    def get_project_parameters(self):
        return BuildProject.get_project_parameters(self) + [
            ChoiceProjectParameter('release', 'Build beta or release', ['beta', 'release']),
            ChoiceProjectParameter(
                'cloud_group', 'Cloud group', CLOUD_GROUP_LIST, default_choice=self.branch_config.release.default_cloud_group),
            BooleanProjectParameter('hardware_signing',
                                        'Enable hardware signing, use hardware key to sign files', default_value=False),
            BooleanProjectParameter('trusted_timestamping',
                                        'Use trusted timestamping.', default_value=False),
            BooleanProjectParameter('withClouds', '-DwithClouds cmake argument value.', default_value=False),
            StringProjectParameter('revision', 'Specific revision to checkout (optional)', default_value=''),
            StringProjectParameter('custom_cmake_args', 'Additional arguments to cmake', default_value=''),
            MultiChoiceProjectParameter('platform_list', 'Platforms to build',
                                            choices=self.all_platform_list, selected_choices=['linux-x64']),
            MultiChoiceProjectParameter('customization_list', 'Customizations to build',
                                            choices=self.config.customization_list, selected_choices=['default']),
            ]

    @property
    def should_build_unit_tests(self):
        return False

    @property
    def is_signing_enabled(self):
        return True

    @property
    def use_trusted_timestamping(self):
        return self.params.trusted_timestamping

    def is_hardware_signing_enabled(self, customization, platform):
        hardware_signing_node_map = {(item.customization, item.platform): item.node
                                         for item in self.config.release.hardware_signing}
        return self.params.hardware_signing and (customization, platform) in hardware_signing_node_map

    def post_process(self, build_info, build_info_path, platform_build_info_map):
        deployer = Deployer(
            config=self.config,
            artifacts_stored_in_different_customization_dirs=self.must_store_artifacts_in_different_customization_dirs,
            ssh_key_file=None,  # default key from .ssh is ok
            build_num=self.jenkins_env.build_number,
            branch=self.nx_vms_branch_name,
            )
        deployer.deploy_artifacts(
            customization_list=self.requested_customization_list,
            platform_list=self.requested_platform_list,
            build_info_path=build_info_path,
            version_path=VERSION_FILE,
            platform_build_info_map=platform_build_info_map,
            )

    def make_email_recipient_list(self, build_info):
        return self.build_user_email_list
