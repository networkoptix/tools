import os
import subprocess
import distutils.spawn


class HgContext:
    def __init__(self):
        self._hg = self.find_hg()

    @staticmethod
    def find_hg():
        hg = os.getenv("HG")
        return hg if hg else distutils.spawn.find_executable("hg")

    def execute(self, *args):
        return subprocess.check_output([self._hg] + list(args)).decode("utf-8").strip()

    def execute_interactive(self, *args):
        subprocess.call([self._hg] + list(args))

    def log(self, rev=None, template=None, split_by="\n", *args):
        command = ("log",)
        if rev:
            command += ("--rev", rev)
        if template:
            command += ("--template", template)
        command += args

        output = self.execute(*command)
        if split_by:
            output = output.split(split_by)
        return output

    def phase(self, rev):
        return self.log(rev=rev, template="{phase}")[0]

    def heads(self, branch=None):
        command = ("heads", "--template", "{node}\n")
        if branch:
            command += tuple(branch)
        return self.execute(*command).split()

    def rebase(self, source=None, base=None, dest=None, *args):
        command = ("rebase",)
        if source:
            command += ("--source", source)
        if base:
            command += ("--base", base)
        if dest:
            command += ("--dest", dest)
        command += args
        self.execute_interactive(*command)

    def update(self, rev=None, clean=False):
        command = ("update",)
        if rev:
            command += (rev,)
        if clean:
            command += ("--clean",)
        self.execute_interactive(*command)

    def branch(self, rev=".", *args):
        return self.log(rev=rev, template="{branch}")[0]

    def commit(self, message=None, edit=False, amend=False, user=None):
        command = ("commit",)
        if edit:
            command += ("--edit",)
        if amend:
            command += ("--amend",)
        if user:
            command += ("--user", user)
        if message:
            command += ("--message", message)
        self.execute_interactive(*command)
