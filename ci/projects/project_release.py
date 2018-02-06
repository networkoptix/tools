# Release project for multibranch pipeline - build/test requested customizations and platforms on user request

import logging

from project_build import BuildProject
from command import (
    ChoiceProjectParameter,
    MultiChoiceProjectParameter,
    )

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

    def make_build_job_name(self, customization, platform):
        return '{}-{}'.format(customization, platform)

    def get_project_parameters(self):
        return BuildProject.get_project_parameters(self) + [
            ChoiceProjectParameter('release', 'Build beta or release', ['beta', 'release']),
            ChoiceProjectParameter('cloud_group', 'Cloud group', CLOUD_GROUP_LIST),
            MultiChoiceProjectParameter('platform_list', 'Platforms to build',
                                            choices=self.all_platform_list, selected_choices=['linux-x64']),
            MultiChoiceProjectParameter('customization_list', 'Customizations to build',
                                            choices=self.config.customization_list, selected_choices=['default']),
            ]

    def send_result_email(self, sender, smtp_password, project, branch, build_num):
        build_info = sender.render_email(project, branch, build_num, test_mode=self.in_assist_mode)
        build_user = self.jenkins_env.build_user
        if build_user:
            recipient_list = ['{} <{}>'.format(build_user.full_name, build_user.email)]
            sender.send_email(smtp_password, build_info.subject_and_html, recipient_list)
        return build_info
