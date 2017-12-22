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
    StashCommand,
    UnstashCommand,
    ArchiveArtifactsCommand,
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

    days_to_keep_old_builds = 30

    def get_project_parameters(self):
        return BuildProject.get_project_parameters(self) + [
            ChoiceProjectParameter('release', 'Build beta or release', ['beta', 'release']),
            ChoiceProjectParameter('cloud_group', 'Cloud group', CLOUD_GROUP_LIST),
            MultiChoiceProjectParameter('platform_list', 'Platforms to build',
                                            choices=self.all_platform_list, selected_choices=['linux-x64']),
            MultiChoiceProjectParameter('customization_list', 'Customizations to build',
                                            choices=self.config.customization_list, selected_choices=['default']),
            ]

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
            cloud_group=self.params.cloud_group)

    def stage_prepare_for_build(self):
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
        workspace_dir = self.workspace_dir(customization, platform)
        return BuildProject.make_parallel_job(self, job_name, workspace_dir, platform, customization=customization)

    def workspace_dir(self, customization, platform):
        if self.in_assist_mode:
            return 'psa-release-{}-{}-{}'.format(self.jenkins_env.job_name, customization, platform)
        else:
            return 'release-{}-{}-{}'.format(self.nx_vms_branch_name, customization, platform)

    def stage_node(self, customization, platform):
        log.info('Node stage: node=%s, customization=%s, platform=%s', self.current_node, customization, platform)
        platform_config = self.config.platforms[platform]
        platform_branch_config = self.branch_config.platforms.get(platform)
        junk_shop_repository = self.create_junk_shop_repository(platform=platform, customization=customization)

        build_info = self._build(junk_shop_repository, platform_branch_config, platform_config)
        return self.post_build_actions(junk_shop_repository, build_info)

    def stage_finalize(self):
        nx_vms_scm_info = self.scm_info['nx_vms']
        self.db_config.bind(models.db)
        project = self.project_name
        branch = nx_vms_scm_info.branch
        build_num = self.jenkins_env.build_number
        sender = EmailSender(self.config)
        build_info = sender.render_email(project, branch, build_num, test_mode=self.in_assist_mode)
        if build_info.has_failed_builds:
            build_result = SetBuildResultCommand.brFAILURE
        elif build_info.has_failed_tests:
            build_result = SetBuildResultCommand.brUNSTABLE
        else:
            return
        return [SetBuildResultCommand(build_result)]
