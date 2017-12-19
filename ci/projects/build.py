import logging
import os.path
import os
import sys
from collections import namedtuple
import datetime
import shutil
import platform
import yaml

from utils import setup_logging, ensure_dir_exists, ensure_dir_missing, is_list_inst
from config import PlatformConfig, Config, PlatformBranchConfig, BranchConfig
from host import CommandResults, LocalHost
from cmake import CMake
from junk_shop import DbConfig, BuildParameters, DbCaptureRepository, store_output_and_exit_code

log = logging.getLogger(__name__)


CONFIGURE_TIMEOUT = datetime.timedelta(hours=2)
BUILD_TIMEOUT = datetime.timedelta(hours=2)


class BuildInfo(namedtuple(
    'BuildInfo', 'is_succeeded, artifact_mask_list, current_config_path, version, unit_tests_bin_dir, run_id')):

    def __init__(self, is_succeeded, artifact_mask_list, current_config_path, version, unit_tests_bin_dir, run_id):
        assert isinstance(is_succeeded, bool), repr(is_succeeded)
        assert is_list_inst(artifact_mask_list, basestring), repr(artifact_mask_list)
        assert isinstance(current_config_path, basestring), repr(current_config_path)
        assert version is None or isinstance(version, basestring), repr(version)
        assert isinstance(unit_tests_bin_dir, basestring), repr(unit_tests_bin_dir)
        assert isinstance(run_id, int), repr(run_id)
        super(BuildInfo, self).__init__(
            is_succeeded=is_succeeded,
            artifact_mask_list=artifact_mask_list,
            current_config_path=current_config_path,
            version=version,
            unit_tests_bin_dir=unit_tests_bin_dir,
            run_id=run_id,
            )


class CMakeBuilder(object):

    PlatformConfig = namedtuple('PlatformConfig', 'build_tool is_unix')

    _system_platform_config = dict(
        Linux=PlatformConfig('Ninja', is_unix=True),
        Darwin=PlatformConfig('Ninja', is_unix=True),
        # Windows=PlatformConfig('Visual Studio 14 2015 Win64'),  # for older, pre-4.0 branches
        Windows=PlatformConfig('Visual Studio 15 2017 Win64', is_unix=False),
        )

    def __init__(self, cmake):
        assert isinstance(cmake, CMake), repr(cmake)
        self._cmake = cmake
        self._host = LocalHost()
        self._system = platform.system()
        self._working_dir = os.getcwd()  # python steps are run in working dir

    @property
    def _platform_config(self):
        return self._system_platform_config[self._system]

    def build(self, junk_shop_repository, platform_config, branch_config, src_dir, build_dir, clean_build):
        assert isinstance(junk_shop_repository, DbCaptureRepository), repr(junk_shop_repository)
        assert isinstance(platform_config, PlatformConfig), repr(platform_config)
        assert branch_config is None or isinstance(branch_config, PlatformBranchConfig), repr(branch_config)
        build_params = junk_shop_repository.build_parameters
        self._prepare_build_dir(build_dir, clean_build)
        cmake_configuration = build_params.configuration.capitalize()
        configure_results = self._configure(src_dir, build_dir, branch_config, build_params, cmake_configuration)
        exit_code = configure_results.exit_code
        output = configure_results.stdout
        if configure_results.exit_code == 0:
            build_results = self._build(build_dir, cmake_configuration)
            exit_code = build_results.exit_code
            output += '\n' + build_results.stdout
            if build_results.exit_code == 0:
                log.info('Building with cmake succeeded')
            else:
                log.info('Building with cmake failed with exit code: %d', build_results.exit_code)
        else:
            log.info('Configuring with cmake failed with exit code: %d', configure_results.exit_code)
        build_info = store_output_and_exit_code(junk_shop_repository, output, exit_code)
        cmake_build_info = self._read_cmake_build_info_file(build_dir)
        log.info('Build results are stored to junk-shop database at %r: outcome=%r, run.id=%r',
                     junk_shop_repository.db_config, build_info.outcome, build_info.run_id)
        if self._platform_config.is_unix:
            unit_tests_bin_dir = os.path.join(build_dir, 'bin')
        else:
            # Visual studio uses multi-config setup
            unit_tests_bin_dir = os.path.join(build_dir, cmake_configuration, 'bin')
        return BuildInfo(
            is_succeeded=build_info.passed,
            artifact_mask_list=[os.path.join(build_dir, mask) for mask in platform_config.artifact_mask_list],
            current_config_path=os.path.join(build_dir, 'current_config.py'),
            version=cmake_build_info.get('version'),
            unit_tests_bin_dir=unit_tests_bin_dir,
            run_id=build_info.run_id,
            )

    def _prepare_build_dir(self, build_dir, clean_build):
        cmake_cache_path = os.path.join(build_dir, 'CMakeCache.txt')
        if clean_build and os.path.exists(build_dir):
            log.info('Clean build: removing build dir: %s', build_dir)
            shutil.rmtree(build_dir)
        elif os.path.exists(cmake_cache_path):
            log.info('Removing cmake cache file: %s', cmake_cache_path)
            os.remove(cmake_cache_path)
        ensure_dir_exists(build_dir)
        cleaner = 'nx_vms/build_utils/python/clear_cmake_build.py'
        if os.path.isfile(cleaner):
            log.info('Cleaning previous distributives using %s', cleaner)
            self._host.run_command([cleaner, '--build-dir', build_dir])
        else:
            ensure_dir_missing(os.path.join(build_dir, 'distrib'))  # todo: remove when cleaner is merged to all branches

    def _configure(self, src_dir, build_dir, branch_config, build_params, cmake_configuration):
        build_tool = self._platform_config.build_tool
        src_full_path = os.path.abspath(src_dir)
        target_device = self._platform2target_device(build_params.platform)
        platform_args = []
        if target_device:
            platform_args += ['-DtargetDevice={}'.format(target_device)]
        if branch_config and branch_config.c_compiler:
            platform_args += ['-DCMAKE_C_COMPILER={}'.format(branch_config.c_compiler)]
        if branch_config and branch_config.cxx_compiler:
            platform_args += ['-DCMAKE_CXX_COMPILER={}'.format(branch_config.cxx_compiler)]
        configure_args = [
            '-DdeveloperBuild=OFF',
            '-DCMAKE_BUILD_TYPE=%s' % cmake_configuration,
            '-DcloudGroup=%s' % build_params.cloud_group,
            '-Dcustomization=%s' % build_params.customization,
            '-DbuildNumber=%d' % build_params.build_num,
            '-Dbeta=%s' % ('TRUE' if build_params.is_beta else 'FALSE'),
            ] + platform_args + [
            '-G', build_tool,
            src_full_path,
            ]
        # if build_params.target_device:
        #     configure_args.append('-DtargetDevice=%s' % build_params.target_device)
        log.info('Configuring with cmake: %s', self._host.args2cmdline(configure_args))
        return self._cmake.run_cmake(
            configure_args, env=self._env, cwd=build_dir, check_retcode=False, timeout=CONFIGURE_TIMEOUT)

    def _build(self, build_dir, cmake_configuration):
        build_args = [
            '--build', '.',
            '--config', cmake_configuration,
            ]
        log.info('Building with cmake: %s', self._host.args2cmdline(build_args))
        return self._cmake.run_cmake(
            build_args, env=self._env, cwd=build_dir, check_retcode=False, timeout=BUILD_TIMEOUT)

    def _platform2target_device(self, platform):
        if platform in ['linux-x64', 'win-x64', 'mac']:
            return None  # targetDevice is not specified for them
        return platform

    @property
    def _env(self):
        return dict(os.environ, environment=self._working_dir)

    def _read_cmake_build_info_file(self, build_dir):
        path = os.path.join(build_dir, 'build_info.txt')
        if not os.path.isfile(path):
            return {}
        with open(path) as f:
            return dict([line.split('=') for line in f.read().splitlines()])


def test_me():
    setup_logging(logging.DEBUG)
    cmake = CMake('3.9.6')
    cmake.ensure_required_cmake_operational()

    sys.path.append(os.path.expanduser('~/proj/devtools/ci/junk_shop'))
    from junk_shop import BuildParameters, store_output_and_exit_code

    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    config = Config.from_dict(yaml.load(open(config_path)))
    db_config = DbConfig.from_string(sys.argv[1])
    project = sys.argv[2]
    branch = sys.argv[3]
    platform = sys.argv[4]
    if len(sys.argv) >= 6:
        branch_config = BranchConfig.from_dict(yaml.load(open(sys.argv[5])))
        platform_branch_config = branch_config.platforms.get(platform)
    else:
        platform_branch_config = None
    build_params = BuildParameters(
        project=project,
        branch=branch,
        platform=platform,
        cloud_group='test',
        customization='default',
        build_num=1000,
        configuration='release',
        )
    repository = DbCaptureRepository(db_config, build_params)
    builder = CMakeBuilder(cmake)
    build_dir = 'build-{}'.format(platform)
    build_info = builder.build(repository, config.platforms[platform], platform_branch_config, 'nx_vms', build_dir, clean_build=False)
    log.info('Build info: %r', build_info)


if __name__ == '__main__':
    test_me()
