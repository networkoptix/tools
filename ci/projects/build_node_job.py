# build and run unit tests on a node, for single customization, for single platform

import logging
import os.path
import pprint
import glob
import yaml
from collections import namedtuple

from pony.orm import db_session
from pyvalid import accepts, returns

from junk_shop import (
    models,
    DbCaptureRepository,
    run_unit_tests,
)
from utils import prepare_empty_dir, list_inst, dict_inst
from command import (
    StashCommand,
    )
from cmake import CMake
from build import BuildInfo, CMakeBuilder

log = logging.getLogger(__name__)


BUILD_INFO_STASH_NAME_FORMAT = 'build-info-{}-{}'  # customization, platform
BUILD_INFO_FILE_NAME_FORMAT = 'build_info_{}_{}.yaml'  # customization, platform
QT_PDB_NAME = 'qt_pdb.zip'


class PlatformBuildInfo(namedtuple(
    'PlatformBuildInfo', [
        'customization',
        'platform',
        'is_succeeded',
        'current_config_path',
        'unit_tests_bin_dir',
        'artifacts_dir',
        'typed_artifact_list',  # artifact type (str: distributive, update, qtpdb, misc) -> file list (str list)
        ])):

    @classmethod
    def from_build_info(cls, customization, platform, build_info, typed_artifact_list):
        return cls(
            customization=customization,
            platform=platform,
            is_succeeded=build_info.is_succeeded,
            current_config_path=build_info.current_config_path,
            unit_tests_bin_dir=build_info.unit_tests_bin_dir,
            artifacts_dir=build_info.artifacts_dir,
            typed_artifact_list=typed_artifact_list,
            )

    @classmethod
    def from_dict(cls, data):
        return cls(
            customization=data['customization'],
            platform=data['platform'],
            is_succeeded=data['is_succeeded'],
            current_config_path=data['current_config_path'],
            unit_tests_bin_dir=data['unit_tests_bin_dir'],
            artifacts_dir=data['artifacts_dir'],
            typed_artifact_list=data['typed_artifact_list'],
            )

    @accepts(
        object,
        customization=basestring,
        platform=basestring,
        is_succeeded=bool,
        current_config_path=basestring,
        unit_tests_bin_dir=basestring,
        artifacts_dir=basestring,
        typed_artifact_list=dict_inst(basestring, list_inst(basestring))
        )
    def __init__(
            self,
            customization,
            platform,
            is_succeeded,
            current_config_path,
            unit_tests_bin_dir,
            artifacts_dir,
            typed_artifact_list,
            ):
        super(PlatformBuildInfo, self).__init__(
            customization=customization,
            platform=platform,
            is_succeeded=is_succeeded,
            current_config_path=current_config_path,
            unit_tests_bin_dir=unit_tests_bin_dir,
            artifacts_dir=artifacts_dir,
            typed_artifact_list=typed_artifact_list,
            )

    def to_dict(self):
        return dict(self._asdict())

    def report(self):
        log.debug('Platform Build Info:')
        for line in pprint.pformat(self.to_dict()).splitlines():
            log.debug('\t%s' % line.rstrip())


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
                 webadmin_external_dir,
                 ):
        self._cmake_version = cmake_version
        self._executor_number = executor_number
        self._is_unix = is_unix
        self._workspace_dir = workspace_dir
        self._platform_config = platform_config
        self._platform_branch_config = platform_branch_config
        self._webadmin_external_dir = webadmin_external_dir
        self._error_list = []
        self._repository = DbCaptureRepository(db_config, build_parameters)

    def run(self, do_build, clean_build, build_tests, run_unit_tests, unit_tests_timeout):
        if do_build:
            platform_build_info, run_id = self._build(clean_build, build_tests)
        else:
            platform_build_info = self._load_platform_build_info()
            run_id = None  # do not save errors artifact if there were no build
            log.info('Build is skipped')
            platform_build_info.report()
        if platform_build_info.is_succeeded and run_unit_tests:
            self._run_unit_tests(platform_build_info, unit_tests_timeout)
        self._save_errors_artifact(run_id)
        return list(self._make_stash_command_list(platform_build_info))

    @property
    def _customization(self):
        return self._repository.build_parameters.customization

    @property
    def _platform(self):
        return self._repository.build_parameters.platform

    @property
    def _platform_build_info_path(self):
        return BUILD_INFO_FILE_NAME_FORMAT.format(self._customization, self._platform)

    def _build(self, clean_build, build_tests):
        log.info('Executor number: %s', self._executor_number)
        cmake = CMake(self._cmake_version)
        cmake.ensure_required_cmake_operational()

        builder = CMakeBuilder(self._executor_number, self._platform_config, self._platform_branch_config, self._repository, cmake)
        build_info = builder.build('nx_vms', 'build', self._webadmin_external_dir, build_tests, clean_build)
        typed_artifact_list = self._make_artifact_list(build_info)
        platform_build_info = PlatformBuildInfo.from_build_info(
            self._customization, self._platform, build_info, typed_artifact_list)
        self._save_platform_build_info(platform_build_info)
        return (platform_build_info, build_info.run_id)

    def _load_platform_build_info(self):
        with open(self._platform_build_info_path) as f:
            return PlatformBuildInfo.from_dict(yaml.load(f))

    def _save_platform_build_info(self, platform_build_info):
        with open(self._platform_build_info_path, 'w') as f:
            yaml.dump(platform_build_info.to_dict(), f, default_flow_style=False)

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

    def _make_stash_command_list(self, platform_build_info):
        platform_build_info_stash_name = BUILD_INFO_STASH_NAME_FORMAT.format(self._customization, self._platform)
        yield StashCommand(platform_build_info_stash_name, [self._platform_build_info_path])
        if not platform_build_info.is_succeeded:
            return
        for t, artifact_list in platform_build_info.typed_artifact_list.items():
            if not artifact_list:
                continue
            stash_name = 'dist-%s-%s-%s' % (self._customization, self._platform, t)
            if t == 'unit_tests':
                dir = platform_build_info.unit_tests_bin_dir
            else:
                dir = platform_build_info.artifacts_dir
            yield StashCommand(stash_name, artifact_list, dir)

    def _make_artifact_list(self, build_info):
        dir = build_info.artifacts_dir
        config = self._platform_config
        return dict(
            distributive=self._list_artifacts(
                dir, config.distributive_mask_list, exclude_list=config.update_mask_list + [QT_PDB_NAME]),
            unit_tests=self._list_artifacts(
                build_info.unit_tests_bin_dir, ['appserver2_ut']),
            update=self._list_artifacts(
                dir, config.update_mask_list, exclude_list=[QT_PDB_NAME]),
            qtpdb=self._list_artifacts(
                dir, [QT_PDB_NAME]),
            misc=self._list_artifacts(
                dir, ['*'], exclude_list=config.distributive_mask_list + config.update_mask_list + [QT_PDB_NAME]),
            )

    def _list_artifacts(self, artifacts_dir, include_list, exclude_list=None):
        if exclude_list:
            exclude_set = set(self._list_artifacts(artifacts_dir, exclude_list))
        else:
            exclude_set = set()
        artifact_list = []
        for mask in include_list:
            for path in glob.glob(os.path.join(artifacts_dir, mask)):
                relative_path = os.path.relpath(path, artifacts_dir)
                if relative_path not in exclude_set:
                    artifact_list.append(relative_path)
        if not artifact_list:
            self._add_error('No artifacts were produced matching masks: {}'.format(', '.join(include_list)))
        return artifact_list

    def _add_error(self, error):
        log.error(error)
        self._error_list.append(error)

    @db_session
    def _save_errors_artifact(self, run_id):
        if not run_id or not self._error_list:
            return
        run = models.Run[run_id]
        self._repository.add_artifact(
            run, 'errors', 'errors', self._repository.artifact_type.output, '\n'.join(self._error_list), is_error=True)
