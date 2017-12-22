# project just for adding/updating 'project' parameter

from project import JenkinsProject
from command import SetProjectPropertiesCommand


class ConfigureProject(JenkinsProject):

    project_id = 'configure'
    days_to_keep_old_builds = 10

    def stage_init(self):
        return [self.set_project_properties_command]

    @property
    def set_project_properties_command(self):
        return SetProjectPropertiesCommand(
            parameters=self.default_parameters,
            enable_concurrent_builds=False,
            days_to_keep_old_builds=self.days_to_keep_old_builds,
            )
