import logging

from command import (
    SetProjectPropertiesCommand,
    PrepareVirtualEnvCommand,
    NodeCommand,
    )
from project import JenkinsProject

log = logging.getLogger(__name__)


class TestProject(JenkinsProject):

    project_id = 'test'

    def stage_init(self):
        job_command_list = [
            SetProjectPropertiesCommand(
                parameters=self.default_parameters,
                enable_concurrent_builds=False,
                days_to_keep_old_builds=2,
                ),
            self.prepare_devtools_command,
            PrepareVirtualEnvCommand(self.devtools_python_requirements),
            self.make_python_stage_command('node'),
            ]
        return [
            NodeCommand('linux', command_list=job_command_list)
            ]

    def stage_node(self):
        log.info('executor_number=%r', self.jenkins_env.executor_number)
