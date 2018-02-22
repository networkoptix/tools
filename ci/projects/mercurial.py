# writing to mercurial repository

from host import LocalHost


class MercurialWriter(object):

    def __init__(self, repository_dir, repository_url, ssh_key_path):
        self._repository_dir = repository_dir
        self._repository_url = repository_url
        self._ssh_key_path = ssh_key_path
        self._host = LocalHost()

    def set_bookmark(self, bookmark):
        self._run_hg_command(['bookmark', bookmark])
        self._run_hg_command(['push', '-B', bookmark], check_retcode=False)  # hg returns 1 when pushing only bookmarks

    def _run_hg_command(self, args, check_retcode=True):
        args = [
            'hg',
            '--config', 'paths.default-push=%s' % self._repository_url,
            '--config', 'ui.ssh=ssh -i %s' % self._ssh_key_path,
            ] + args
        self._host.run_command(args, cwd=self._repository_dir, check_retcode=check_retcode)
