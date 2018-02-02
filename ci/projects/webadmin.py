# steps required to build webadmin

import os
import os.path
import logging

from pony.orm import db_session, flush

from junk_shop.utils import status2outcome
from junk_shop import models
from utils import prepare_empty_dir
from command import StashCommand
from host import LocalHost

log = logging.getLogger(__name__)


BUILD_DIR = 'build-webadmin'
BUILD_SCRIPT_PATH = 'nx_vms/webadmin/build.sh'
DEPLOY_SCRIPT_PATH = 'nx_vms/webadmin/deploy.sh'
SERVER_EXTERNAL_DIR = 'server-external/bin'
SERVER_EXTERNAL_NAME = 'external.dat'
WEBADMIN_STASH_NAME = 'webadmin'


class BuildWebAdminJob(object):

    def __init__(self, workspace_dir, repository):
        self._workspace_dir = workspace_dir
        self._repository = repository
        self._host = LocalHost()

    def run(self, do_build, deploy):
        if do_build:
            run_id = self._do_build()
        result_path = os.path.join(self._build_dir, SERVER_EXTERNAL_DIR, SERVER_EXTERNAL_NAME)
        assert os.path.isfile(result_path), 'Webadmin was not built: build result is missing: %r' % result_path
        if do_build and deploy:
            self._deploy(run_id)
        return [StashCommand(WEBADMIN_STASH_NAME, [SERVER_EXTERNAL_NAME], os.path.join(BUILD_DIR, SERVER_EXTERNAL_DIR))]

    def _do_build(self):
        prepare_empty_dir(self._build_dir)
        build_script_path = os.path.join(self._workspace_dir, BUILD_SCRIPT_PATH)
        result = self._host.run_command(
            [build_script_path],
            cwd=self._build_dir,
            check_retcode=False,
            merge_stderr=True,
            )
        is_succeeded = result.exit_code == 0
        log.info('Webadmin build is %s' % ('SUCCEEDED' if is_succeeded else 'FAILED'))
        return self._store_build_output(result.stdout, is_succeeded)

    def _deploy(self, run_id):
        deploy_script_path = os.path.join(self._workspace_dir, DEPLOY_SCRIPT_PATH)
        env = dict(os.environ,
                   environment=self._workspace_dir)
        result = self._host.run_command(
            [deploy_script_path],
            cwd=self._build_dir,
            env=env,
            check_retcode=False,
            merge_stderr=True,
            )
        is_succeeded = result.exit_code == 0
        log.info('Webadmin deployment is %s' % ('SUCCEEDED' if is_succeeded else 'FAILED'))
        self._store_artifact(run_id, 'deploy', result.stdout, is_error=not is_succeeded)

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
    def _store_artifact(self, run_id, name, output, is_error):
        run = models.Run[run_id]
        self._repository.add_artifact(run, name, name, self._repository.artifact_type.output, output, is_error)
