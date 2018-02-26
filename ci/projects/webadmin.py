# steps required to build webadmin

import os
import os.path
import logging
import errno
import ConfigParser

from pony.orm import db_session, flush

from junk_shop.utils import status2outcome
from junk_shop import models
from utils import prepare_empty_dir, ensure_dir_exists
from command import StashCommand
from state import SshKeyCredential
from host import LocalHost

log = logging.getLogger(__name__)


BUILD_DIR = 'build-webadmin'
BUILD_SCRIPT_PATH = 'nx_vms/webadmin/build.sh'
DEPLOY_SCRIPT_PATH = 'nx_vms/webadmin/deploy.sh'
RDEP_CONFIGURE_PATH = 'nx_vms/build_utils/python/rdep_configure.py'
SERVER_EXTERNAL_DIR = 'server-external'
SERVER_EXTERNAL_SUB_PATH = 'bin/external.dat'
WEBADMIN_STASH_NAME = 'webadmin'
RDEP_SSH_COMMAND_TEMPLATE = 'ssh -l {user} -i {key_path}'


class BuildWebAdminJob(object):

    def __init__(self, ssh_key_credential, workspace_dir, repository):
        assert isinstance(ssh_key_credential, SshKeyCredential), repr(ssh_key_credential)
        self._ssh_key_credential = ssh_key_credential
        self._workspace_dir = workspace_dir
        self._repository = repository
        self._host = LocalHost()

    def run(self, do_build, deploy, deploy_for_version):
        if do_build:
            run_id = self._do_build()
        result_path = os.path.join(self._build_dir, SERVER_EXTERNAL_DIR, SERVER_EXTERNAL_SUB_PATH)
        assert os.path.isfile(result_path), 'Webadmin was not built: build result is missing: %r' % result_path
        if do_build and deploy:
            self._deploy(run_id, deploy_for_version)
        return [StashCommand(WEBADMIN_STASH_NAME, [SERVER_EXTERNAL_SUB_PATH], os.path.join(BUILD_DIR, SERVER_EXTERNAL_DIR))]

    def _do_build(self):
        prepare_empty_dir(self._build_dir)
        build_script_path = os.path.join(self._workspace_dir, BUILD_SCRIPT_PATH)
        try:
            result = self._host.run_command(
                [build_script_path],
                cwd=self._build_dir,
                check_retcode=False,
                merge_stderr=True,
                )
            is_succeeded = result.exit_code == 0
            log.info('Webadmin build is %s' % ('SUCCEEDED' if is_succeeded else 'FAILED'))
            return self._store_build_output(result.stdout, is_succeeded)
        except OSError as x:
            if x.errno != errno.EACCES:
                raise
            error = 'Permission denied when executing %r; this script is broken' % build_script_path
            log.error(error)
            return self._store_build_output(error, is_succeeded=False)

    def _deploy(self, run_id, deploy_for_version):
        self._prepare_packages_dir()
        deploy_script_path = os.path.join(self._workspace_dir, DEPLOY_SCRIPT_PATH)
        args = [deploy_script_path]
        if deploy_for_version:
            args += ['--deploy-release-version']
        try:
            result = self._host.run_command(
                args,
                cwd=self._build_dir,
                env=self._rdep_env,
                check_retcode=False,
                merge_stderr=True,
                )
            is_succeeded = result.exit_code == 0
            log.info('Webadmin deployment is %s' % ('SUCCEEDED' if is_succeeded else 'FAILED'))
            self._store_artifact(run_id, 'deploy', 'deployment-output', result.stdout, is_error=not is_succeeded)
            if not is_succeeded:
                self._store_artifact(run_id, 'errors', 'deployment-errors', 'Deployment is failed', is_error=True)
        except OSError as x:
            if x.errno != errno.EACCES:
                raise
            error = 'Permission denied when executing %r; this script is broken' % deploy_script_path
            log.error(error)
            self._store_artifact(run_id, 'deploy', 'deployment-error', error, is_error=True)
            self._store_artifact(run_id, 'errors', 'deployment-errors', error, is_error=True)

    def _prepare_packages_dir(self):
        packages_dir = os.path.join(self._workspace_dir, 'packages')
        ensure_dir_exists(packages_dir)
        config_path = os.path.join(packages_dir, '.rdep')
        if not os.path.exists(config_path):
            rdep_configure_path = os.path.join(self._workspace_dir, RDEP_CONFIGURE_PATH)
            self._host.run_command([rdep_configure_path], env=self._rdep_env)
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        config.set('General', 'ssh', RDEP_SSH_COMMAND_TEMPLATE.format(
            user=self._ssh_key_credential.user,
            key_path=self._ssh_key_credential.key_path,
            ))
        with open(config_path, 'w') as f:
            config.write(f)

    @property
    def _rdep_env(self):
        return dict(os.environ,
                    environment=self._workspace_dir)

    @property
    def _build_dir(self):
        return os.path.join(self._workspace_dir, BUILD_DIR)

    @db_session
    def _store_build_output(self, output, is_succeeded):
        test = self._repository.produce_test('build', is_leaf=True)
        run = self._repository.add_run('build', test=test)
        run.outcome = status2outcome(is_succeeded)
        self._repository.add_artifact(
            run, 'output', 'build-output', self._repository.artifact_type.output, output, is_error=not is_succeeded)
        flush()  # get run.id
        return run.id

    @db_session
    def _store_artifact(self, run_id, short_name, full_name, output, is_error):
        run = models.Run[run_id]
        if is_error:
            run.outcome = status2outcome(False)  # build errors are only shown for failed outcomes
        self._repository.add_artifact(run, short_name, full_name, self._repository.artifact_type.output, output, is_error)
