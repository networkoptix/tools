import logging
import os.path
import os
import sys
from collections import namedtuple
import datetime
import shutil
import platform
from utils import setup_logging, ensure_dir_exists
from host import CommandResults, LocalHost
from cmake import CMake
from junk_shop import DbConfig, BuildParameters, store_output_and_exit_code

log = logging.getLogger(__name__)


CONFIGURE_TIMEOUT = datetime.timedelta(hours=2)
BUILD_TIMEOUT = datetime.timedelta(hours=2)


class CMakeBuilder(object):

    PlatformConfig = namedtuple('PlatformConfig', 'build_tool')

    platform_config = dict(
        Linux=PlatformConfig('Ninja'),
        Darwin=PlatformConfig('Ninja'),
        # Windows=PlatformConfig('Visual Studio 14 2015 Win64'),  # for older, pre-4.0 branches
        Windows=PlatformConfig('Visual Studio 15 2017 Win64'),
        )

    def __init__(self, cmake):
        assert isinstance(cmake, CMake), repr(cmake)
        self._cmake = cmake
        self._host = LocalHost()
        self._system = platform.system()
        self._working_dir = os.getcwd()  # python steps are run in working dir

    def build(self, src_dir, build_dir, build_params, clean_build, junk_shop_db_config):
        assert isinstance(build_params, BuildParameters), repr(build_params)
        assert isinstance(junk_shop_db_config, DbConfig), repr(junk_shop_db_config)
        self._prepare_build_dir(build_dir, clean_build)
        cmake_configuration = build_params.configuration.capitalize()
        configure_results = self._configure(src_dir, build_dir, build_params, cmake_configuration)
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
        build_info = store_output_and_exit_code(junk_shop_db_config, build_params, output, exit_code)
        log.info('Build results are stored to junk-shop database at %r: outcome=%r, run.path=%r',
                     junk_shop_db_config, build_info.outcome, build_info.run_path)

    def _prepare_build_dir(self, build_dir, clean_build):
        cmake_cache_path = os.path.join(build_dir, 'CMakeCache.txt')
        if clean_build and os.path.exists(build_dir):
            log.info('Clean build: removing build dir: %s', build_dir)
            shutil.rmtree(build_dir)
        elif os.path.exists(cmake_cache_path):
            log.info('Removing cmake cache file: %s', cmake_cache_path)
            os.remove(cmake_cache_path)
        ensure_dir_exists(build_dir)

    def _configure(self, src_dir, build_dir, build_params, cmake_configuration):
        build_tool = self.platform_config[self._system].build_tool
        src_full_path = os.path.abspath(src_dir)
        configure_args = [
            '-DCMAKE_BUILD_TYPE=%s' % cmake_configuration,
            '-DcloudGroup=%s' % build_params.cloud_group,
            '-Dcustomization=%s' % build_params.customization,
            '-DbuildNumber=%d' % build_params.build_num,
            '-Dbeta=%s' % ('TRUE' if build_params.is_beta else 'FALSE'),
            '-G',
            build_tool,
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

    @property
    def _env(self):
        return dict(os.environ, environment=self._working_dir)


def test_me():
    setup_logging(logging.DEBUG)
    cmake = CMake('3.9.6')
    cmake.ensure_required_cmake_operational()

    sys.path.append(os.path.expanduser('~/proj/devtools/ci/junk_shop'))
    from junk_shop import BuildParameters, store_output_and_exit_code

    build_params = BuildParameters(
        cloud_group='test',
        customization='default',
        build_num=1000,
        configuration='release',
        )
    builder = CMakeBuilder(cmake)
    builder.build('nx_vms', 'build', build_params)


if __name__ == '__main__':
    test_me()
