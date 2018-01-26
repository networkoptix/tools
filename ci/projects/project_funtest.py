# Project for running functional tests.
# Input files (distributives) to test are taken from upstream project artifacts

import sys
import os
import os.path
import logging
import glob
import yaml
from datetime import timedelta

from utils import ensure_dir_missing, ensure_dir_exists, prepare_empty_dir
from project_nx_vms import BUILD_INFO_FILE, NxVmsProject
from command import (
    StashCommand,
    UnstashCommand,
    CopyArtifactsCommand,
    ScriptCommand,
    CleanDirCommand,
    ParallelCommand,
    StringProjectParameter,
    ChoiceProjectParameter,
    ParallelJob,
    NodeCommand,
    PrepareVirtualEnvCommand,
    SetProjectPropertiesCommand,
    SetBuildResultCommand,
    )
from host import LocalHost
from email_sender import EmailSender

log = logging.getLogger(__name__)


UPSTREAM_PROJECT = 'ci'
WORK_DIR = 'work'
BIN_DIR = os.path.join(WORK_DIR, 'bin')
TEST_DIR = os.path.join(WORK_DIR, 'test')
DIST_DIR = 'dist'
DIST_STASH = 'dist'
FUN_TESTS_PYTHON_REQUIREMENTS = 'nx_vms/func_tests/requirements.txt'


class FunTestProject(NxVmsProject):

    project_id = 'funtest'

    def stage_init(self):
        command_list = [self.set_project_properties_command]

        if self.params.action != 'test':
            return command_list

        ensure_dir_missing(DIST_DIR)  # cleanup previous copied artifacts
        job_list = [self.make_parallel_job(platform) for platform in self.requested_platform_list]
        command_list += self.initial_stash_nx_vms_command_list + [
            self.copy_artifacts_command,
            StashCommand(DIST_STASH, ['%s/**' % DIST_DIR]),
            ParallelCommand(job_list),
            self.make_python_stage_command('finalize'),
            ]
        return command_list

    @property
    def set_project_properties_command(self):
        return SetProjectPropertiesCommand(
            parameters=self.get_project_parameters(),
            enable_concurrent_builds=self.config.fun_tests.enable_concurrent_builds,
            days_to_keep_old_builds=self.config.fun_tests.days_to_keep_old_builds,
            )

    def get_project_parameters(self):
        parameters = self.default_parameters + [
            ChoiceProjectParameter('action', 'Action to perform: run tests or just update project properties',
                                       ['test', 'update_properties']),
            StringProjectParameter('tests', 'Space-separated test list to run; by default (empty value) run all', default_value=''),
            StringProjectParameter(
                'build_num', 'Which build to test; by default (empty value) one that triggered this job', default_value=''),
            ]
        return parameters

    @property
    def requested_platform_list(self):
        return self.config.fun_tests.platforms

    def make_parallel_job(self, platform):
        job_command_list = self.prepare_devtools_command_list + self.prepare_nx_vms_command_list + [
            PrepareVirtualEnvCommand(self.devtools_python_requirements + [FUN_TESTS_PYTHON_REQUIREMENTS]),
            self.make_python_stage_command('prepare_dir', platform=platform),
            ]
        job_name = platform
        node = self.config.fun_tests.node
        workspace_dir = self.make_workspace_dir(platform)
        return ParallelJob(job_name, [NodeCommand(node, workspace_dir, job_command_list)])

    @property
    def copy_artifacts_command(self):
        if self.params.build_num:
            selector = CopyArtifactsCommand.selSpecificBuild
            try:
                build_num = int(self.params.build_num)
            except ValueError:
                assert False, 'Invalid build_num: %r' % build_num
        else:
            if self.in_assist_mode:
                selector = CopyArtifactsCommand.selCompleted
            else:
                selector = CopyArtifactsCommand.selUpstream
            build_num = None
        upstream_project_name = UPSTREAM_PROJECT + '/' + self.nx_vms_branch_name
        return CopyArtifactsCommand(upstream_project_name, DIST_DIR, selector, build_num)

    def make_workspace_dir(self, platform):
        if self.in_assist_mode:
            return 'psa-{}-{}-{}'.format(self.project_id, self.jenkins_env.job_name, platform)
        else:
            return '{}-{}-{}'.format(self.project_id, self.nx_vms_branch_name, platform)

    def stage_prepare_dir(self, platform):
        ensure_dir_missing(DIST_DIR)  # cleanup previous unstashed artifacts
        return [
            UnstashCommand(DIST_STASH),
            self.make_python_stage_command('run_tests', platform=platform),
            ]

    def stage_run_tests(self, platform):
        log.info('Running functional tests for platform %r; executor#%s', platform, self.jenkins_env.executor_number)
        build_info = self._load_build_info()
        prepare_empty_dir(WORK_DIR)
        self._pick_binaries()
        server_deb_path = self._pick_server_deb_path()
        log.info('Will test distributive %s', server_deb_path)
        if not server_deb_path:
            log.error('Build %s/%s #%s did not produce server distributive',
                          build_info['project'], build_info['branch'], build_info['build_num'])
            return [SetBuildResultCommand(SetBuildResultCommand.brFAILURE)]
        self._run_tests(build_info, platform, server_deb_path)

    def _load_build_info(self):
        with open(os.path.join(DIST_DIR, BUILD_INFO_FILE)) as f:
            return yaml.load(f)

    def _pick_binaries(self):
        bin_dir = os.path.join(self.workspace_dir, BIN_DIR)
        binaries_url = self.config.fun_tests.binaries_url
        log.info('copying aux binaries from %r to %r', binaries_url, bin_dir)
        ensure_dir_exists(bin_dir)
        rsync_args = ['rsync', '-v', '-a', '--delete', self.config.fun_tests.binaries_url, bin_dir]
        host = LocalHost()
        host.run_command(rsync_args)

    def _pick_server_deb_path(self):
        path_list = glob.glob(os.path.join(self.workspace_dir, DIST_DIR, '*-server-*-linux64*.deb'))
        assert len(path_list) <= 1, repr(path_list)  # fix glob above - it must not return more than 1 path
        return path_list[0]

    def _run_tests(self, build_info, platform, server_deb_path):
        if self.params.tests:
            test_list = self.params.tests.split(' ')
            for test_name in test_list:
                log.info('Will run test: %s', test_name)
        else:
            test_list = []
            log.info('Will run all tests')
        vm_name_prefix = 'funtest-%s-' % self.jenkins_env.executor_number
        vm_port_base = self.config.fun_tests.port_base + self.jenkins_env.executor_number * self.config.fun_tests.port_range
        timeout = self.config.fun_tests.timeout
        build_parameters = [
            'project=%s' % build_info['project'],
            'branch=%s' % build_info['branch'],
            'build_num=%s' % build_info['build_num'],
            'customization=%s' % build_info['customization'],
            'platform=%s' % platform,
            ]
        options = [
            '--work-dir=%s' % os.path.join(self.workspace_dir, TEST_DIR),
            '--bin-dir=%s' % os.path.join(self.workspace_dir, BIN_DIR),
            '--mediaserver-dist-path=%s' % server_deb_path,
            '--reinstall',
            '--cloud-group=%s' % build_info['cloud_group'],
            '--customization=%s' % build_info['customization'],
            '--timeout=%d' % timeout.total_seconds(),
            '--build-parameters=%s' % ','.join(build_parameters),
            '--vm-port-base=%s' % vm_port_base,
            '--vm-name-prefix=%s' % vm_name_prefix,
            ]
        pytest_args = [self._pytest_path] + options + test_list
        env = dict(os.environ,
                   PYTEST_PLUGINS='junk_shop.pytest_plugin',
                   AUTOTEST_EMAIL_PASSWORD=self.credentials.service_email,
                   JUNK_SHOP_CAPTURE_DB='%s@%s' % (self.credentials.junk_shop_db, self.config.junk_shop.db_host),
                   )
        host = LocalHost()
        result = host.run_command(
            pytest_args,
            cwd=os.path.join(self.workspace_dir, 'nx_vms/func_tests'),
            env=env,
            check_retcode=False,
            timeout=timeout + timedelta(minutes=10),  # give pytest some time to handle timeout itself
            )
        log.info('Functional tests %s' % ('PASSED' if result.exit_code == 0 else 'FAILED'))
        for line in result.stdout.splitlines():
            log.info('\t%s', line.rstrip())

    @property
    def _pytest_path(self):
        dir, _ = os.path.split(sys.executable)
        return os.path.join(dir, 'pytest')

    def stage_finalize(self):
        pass
