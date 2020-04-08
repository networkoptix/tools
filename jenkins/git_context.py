import subprocess


class GitContext:
    def __init__(self):
        self.rev = self.get_current_revision()
        self.branch = self.get_current_branch()

    def execute_command(self, command):
        return subprocess.check_output(
            command.split(),
            stderr=subprocess.STDOUT,
            universal_newlines=True)

    def get_current_revision(self):
        return self.execute_command("git rev-parse --short=12 HEAD").strip('\n')

    def get_current_branch(self):
        return self.execute_command("git rev-parse --abbrev-ref HEAD").strip('\n')
