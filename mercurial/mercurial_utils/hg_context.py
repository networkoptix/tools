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

    def rebase(self, source=None, dest=None, *args):
        command = ("rebase",)
        if source:
            command += ("--source", source)
        if dest:
            command += ("--dest", dest)
        command += args
        print(self.execute(*command))

    def update(self, rev=None, clean=False):
        command = ("update",)
        if rev:
            command += (rev,)
        if clean:
            command += ("--clean",)
        print(self.execute(*command))
