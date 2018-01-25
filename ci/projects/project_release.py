# Release project for multibranch pipeline - build/test requested customizations and platforms on user request

import logging

from junk_shop import (
    models,
    )
from project_build import BuildProject
from command import (
    ScriptCommand,
    CheckoutCommand,
    CheckoutScmCommand,
    UnstashCommand,
    CleanDirCommand,
    ParallelCommand,
    ChoiceProjectParameter,
    MultiChoiceProjectParameter,
    )
from email_sender import EmailSender

log = logging.getLogger(__name__)


DAYS_TO_KEEP_OLD_BUILDS = 30

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

    days_to_keep_old_builds = DAYS_TO_KEEP_OLD_BUILDS

    def get_project_parameters(self):
        return BuildProject.get_project_parameters(self) + [
            ChoiceProjectParameter('release', 'Build beta or release', ['beta', 'release']),
            ChoiceProjectParameter('cloud_group', 'Cloud group', CLOUD_GROUP_LIST),
            MultiChoiceProjectParameter('platform_list', 'Platforms to build',
                                            choices=self.all_platform_list, selected_choices=['linux-x64']),
            MultiChoiceProjectParameter('customization_list', 'Customizations to build',
                                            choices=self.config.customization_list, selected_choices=['default']),
            ]

    def must_actually_do_build(self):
        if not self.jenkins_env.build_user:
            return False  # do not build if triggered by multibranch scan, just update parameters
        return super(ReleaseProject, self).must_actually_do_build()

    @property
    def run_unit_tests_by_default(self):
        return False

    @property
    def requested_platform_list(self):
        platform_list = self.params.get('platform_list')
        if not platform_list:
            return []
        return [p for p in self.all_platform_list if p in platform_list.split(',')]

    @property
    def requested_customization_list(self):
        customization_list = self.params.get('customization_list')
        log.info('params customization_list = %r', customization_list)
        if not customization_list:
            return []
        return [c for c in self.config.customization_list if c in customization_list.split(',')]

    def create_build_parameters(self, platform=None, customization=None):
        return BuildProject.create_build_parameters(
            self, platform, customization,
            release=self.params.release,
            cloud_group=self.params.cloud_group,
            )

    def stage_prepare_for_build(self):
        self.clean_stamps.init_master(self.params)
        self.init_build_info()

        log.info('requested platform_list = %r', self.requested_platform_list)
        log.info('requested customization_list = %r', self.requested_customization_list)

        job_list = [self.make_parallel_job(customization, platform)
                        for platform in self.requested_platform_list
                        for customization in self.requested_customization_list]
        return [
            ParallelCommand(job_list),
            self.make_python_stage_command('finalize'),
            ]

    def make_parallel_job(self, customization, platform):
        job_name = '{}-{}'.format(customization, platform)
        workspace_dir = self.make_workspace_dir(customization, platform)
        return BuildProject.make_parallel_job(self, job_name, workspace_dir, platform, customization=customization)

    def make_workspace_dir(self, customization, platform):
        if self.in_assist_mode:
            return 'psa-release-{}-{}-{}'.format(self.jenkins_env.job_name, customization, platform)
        else:
            return 'release-{}-{}-{}'.format(self.nx_vms_branch_name, customization, platform)

    def stage_node(self, customization, platform, phase=1):
        log.info('Node stage: node=%s, phase#%s, customization=%s, platform=%s', self.current_node, phase, customization, platform)

        if self.clean_stamps.check_must_clean_node():
            assert phase == 1, repr(phase)  # must never happen on phase 2
            return [CleanDirCommand()] + self.make_node_stage_command_list(platform=platform, customization=customization, phase=2)

        platform_config = self.config.platforms[platform]
        platform_branch_config = self.branch_config.platforms.get(platform)
        junk_shop_repository = self.create_junk_shop_repository(platform=platform, customization=customization)

        build_info = self.build(junk_shop_repository, platform_branch_config, platform_config)
        if self.params.run_unit_tests and platform_config.should_run_unit_tests and build_info.is_succeeded:
            self.run_unit_tests(junk_shop_repository, build_info, self.config.ci.timeout)

        return self.post_build_actions(junk_shop_repository, build_info, customization, self.params.cloud_group)

    def stage_finalize(self):
        nx_vms_scm_info = self.scm_info['nx_vms']
        self.db_config.bind(models.db)
        project = self.project_name
        branch = nx_vms_scm_info.branch
        build_num = self.jenkins_env.build_number
        sender = EmailSender(self.config)
        build_info = sender.render_email(project, branch, build_num, test_mode=self.in_assist_mode)
        # do not send, commiters have nothing to do with this release build
        # todo: retrieve user who requested this build from jenkins env and send email to him/her
        return self.make_set_build_result_command_list(build_info)
