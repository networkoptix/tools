# build and run unit tests on a node, for single customization, for single platform

import logging
import os.path
import pprint
import glob
import yaml

from pony.orm import db_session

from junk_shop import (
    DbCaptureRepository,
    run_unit_tests,
)
from utils import prepare_empty_dir
from command import (
    StashCommand,
    )
from cmake import CMake
from build import BuildInfo, CMakeBuilder


log = logging.getLogger(__name__)


PLATFORM_BUILD_INFO_PATH = 'platform_build_info.yaml'


# build and run tests on single node for single customization/platofrm
class BuildNodeJob(object):

    def __init__(self,
                 cmake_version,
                 executor_number,
                 db_config,
                 is_unix,
                 workspace_dir,
                 build_parameters,
                 platform_config,
                 platform_branch_config,
                 ):
        self._cmake_version = cmake_version
        self._executor_number = executor_number
        self._db_config = db_config
        self._is_unix = is_unix
        self._workspace_dir = workspace_dir
        self._platform_config = platform_config
        self._platform_branch_config = platform_branch_config
        self._error_list = []
        self._repository = DbCaptureRepository(db_config, build_parameters)

    def run(self, do_build, clean_build, build_tests, run_unit_tests, unit_tests_timeout):
        if do_build:
            build_info = self._build(clean_build, build_tests)
        else:
            build_info = self._load_platform_build_info()
            log.info('Build is skipped')
            log.debug('Build Info:')
            for line in pprint.pformat(dict(build_info._asdict())).splitlines():
                log.debug('\t%s' % line.rstrip())
        if build_info.is_succeeded and run_unit_tests:
            self._run_unit_tests(build_info, unit_tests_timeout)
        if not build_info.is_succeeded:
            return None
        command_list = self._make_post_build_actions(build_info)
        self._save_errors_artifact(build_info)
        return command_list

    @property
    def _customization(self):
        return self._repository.build_parameters.customization

    @property
    def _platform(self):
        return self._repository.build_parameters.platform

    def _build(self, clean_build, build_tests):
        log.info('Executor number: %s', self._executor_number)
        cmake = CMake(self._cmake_version)
        cmake.ensure_required_cmake_operational()

        builder = CMakeBuilder(self._executor_number, self._platform_config, self._platform_branch_config, self._repository, cmake)
        build_info = builder.build('nx_vms', 'build', build_tests, clean_build)
        with open(PLATFORM_BUILD_INFO_PATH, 'w') as f:
            yaml.dump(dict(build_info._asdict()), f, default_flow_style=False)
        return build_info

    def _load_platform_build_info(self):
        with open(PLATFORM_BUILD_INFO_PATH) as f:
            return BuildInfo.from_dict(yaml.load(f))

    def _run_unit_tests(self, build_info, timeout):
        if self._is_unix:
            ext = ''
        else:
            ext = '.exe'
        unit_test_mask_list = os.path.join(build_info.unit_tests_bin_dir, '*_ut%s' % ext)
        test_binary_list = [os.path.basename(path) for path in glob.glob(unit_test_mask_list)]
        if not test_binary_list:
            self._add_error('No unit tests were produced matching masks: {}'.format(unit_test_mask_list))
            return
        unit_tests_dir = os.path.join(self._workspace_dir, 'unit_tests')
        bin_dir = os.path.abspath(build_info.unit_tests_bin_dir)
        prepare_empty_dir(unit_tests_dir)
        log.info('Running unit tests in %r: %s', unit_tests_dir, ', '.join(test_binary_list))
        logging.getLogger('junk_shop.unittest').setLevel(logging.INFO)  # prevent unit tests from logging stdout/stderr
        is_passed = run_unit_tests(
            self._repository, build_info.current_config_path, unit_tests_dir, bin_dir, test_binary_list, timeout)
        log.info('Unit tests are %s', 'passed' if is_passed else 'failed')

    def _make_post_build_actions(self, build_info):
        return (
            self._make_stash_command_list(
                'dist-%s-%s-distributive' % (self._customization, self._platform),
                build_info.artifacts_dir, self._platform_config.distributive_mask_list,
                exclude_list=self._platform_config.update_mask_list) +
            self._make_stash_command_list(
                'dist-%s-%s-update' % (self._customization, self._platform),
                build_info.artifacts_dir, self._platform_config.update_mask_list)
            )

    def _make_stash_command_list(self, stash_name, artifacts_dir, artifact_mask_list, exclude_list=None):
        artifact_list = list(self._list_artifacts(artifacts_dir, artifact_mask_list, exclude_list))
        if not artifact_list:
            error = 'No artifacts were produced matching masks: {}'.format(', '.join(artifact_mask_list))
            self._add_error(error)
            return []
        return [StashCommand(stash_name, artifact_list, artifacts_dir)]

    def _list_artifacts(self, artifacts_dir, include_list, exclude_list=None):
        if exclude_list:
            exclude_set = set(self._list_artifacts(artifacts_dir, exclude_list))
        else:
            exclude_set = set()
        for mask in include_list:
            for path in glob.glob(os.path.join(artifacts_dir, mask)):
                relative_path = os.path.relpath(path, artifacts_dir)
                if relative_path not in exclude_set:
                    yield relative_path

    def _add_error(self, error):
        log.error(error)
        self._error_list.append(error)

    @db_session
    def _save_errors_artifact(self, build_info):
        if not self._error_list:
            return
        run = models.Run[build_info.run_id]
        self._repository.add_artifact(
            run, 'errors', 'errors', self._repository.artifact_type.output, '\n'.join(self._error_list), is_error=True)
