import logging
import os.path
import os
import sys
import glob
from collections import namedtuple
import datetime
import shutil
import platform
import yaml

from pony.orm import db_session

from utils import setup_logging, ensure_dir_exists, ensure_dir_missing, is_list_inst
from config import PlatformConfig, Config, PlatformBranchConfig, BranchConfig
from host import ProcessTimeoutError, CommandResults, LocalHost
from cmake import CMake
from junk_shop import DbConfig, models, BuildParameters, DbCaptureRepository, store_output_and_error, datetime_utc_now
from junk_shop import utils as junk_shop_utils

log = logging.getLogger(__name__)


GENERATE_TIMEOUT = datetime.timedelta(hours=2)
BUILD_TIMEOUT = datetime.timedelta(hours=4)
DEFAULT_GENERATOR = 'Ninja'
LOGS_DIR = 'build_logs'
PARALLEL_JOB_COUNT = 20


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


class CMakeResults(object):

    @classmethod
    def from_command_results(cls, results):
        if results.exit_code != 0:
            error_message = 'Exit code: %d' % results.exit_code
        else:
            error_message = None
        return cls(results.stdout, error_message, succeeded=results.exit_code==0)

    def __init__(self, output, error_message, succeeded):
        self.output = output
        self.error_message = error_message
        self.succeeded = succeeded


def bool_to_cmake_param(value):
    assert isinstance(value, bool), repr(value)
    if value:
        return 'TRUE'
    else:
        return 'FALSE'


class CMakeBuilder(object):

    PlatformConfig = namedtuple('PlatformConfig', 'is_unix')

    _system_platform_config = dict(
        Linux=PlatformConfig(is_unix=True),
        Darwin=PlatformConfig(is_unix=True),
        Windows=PlatformConfig(is_unix=False),
        )

    def __init__(self, executor_number, platform_config, branch_config, cmake):
        assert isinstance(executor_number, int), repr(executor_number)
        assert isinstance(platform_config, PlatformConfig), repr(platform_config)
        assert branch_config is None or isinstance(branch_config, PlatformBranchConfig), repr(branch_config)
        assert isinstance(cmake, CMake), repr(cmake)
        self._executor_number = executor_number
        self._platform_config = platform_config
        self._branch_config = branch_config
        self._cmake = cmake
        self._host = LocalHost()
        self._system = platform.system()
        self._working_dir = os.getcwd()  # python steps are run in working dir

    @property
    def _is_unix(self):
        return self._system_platform_config[self._system].is_unix

    def build(self, junk_shop_repository, src_dir, build_dir, clean_build):
        assert isinstance(junk_shop_repository, DbCaptureRepository), repr(junk_shop_repository)
        build_params = junk_shop_repository.build_parameters
        self._prepare_build_dir(build_dir, clean_build)
        cmake_configuration = build_params.configuration.capitalize()
        generate_results = self._generate(src_dir, build_dir, build_params, cmake_configuration)
        succeeded = generate_results.succeeded
        error_message = generate_results.error_message
        output = generate_results.output
        if generate_results.succeeded:
            build_results = self._build(build_dir, cmake_configuration)
            output += '\n' + build_results.output
            if build_results.succeeded:
                log.info('Building with cmake succeeded')
            else:
                succeeded = False
                error_message = build_results.error_message
                log.info('Building with cmake failed: %s', build_results.error_message)
        else:
            log.info('Generating with cmake failed: %s', generate_results.error_message)
        build_info = store_output_and_error(junk_shop_repository, output, succeeded, error_message)
        self._store_log_artifacts(junk_shop_repository, build_dir, build_info)
        cmake_build_info = self._read_cmake_build_info_file(build_dir)
        log.info('Build results are stored to junk-shop database at %r: outcome=%r, run.id=%r',
                     junk_shop_repository.db_config, build_info.outcome, build_info.run_id)
        if self._is_unix:
            unit_tests_bin_dir = os.path.join(build_dir, 'bin')
        else:
            # Visual studio uses multi-config setup
            unit_tests_bin_dir = os.path.join(build_dir, cmake_configuration, 'bin')
        return BuildInfo(
            is_succeeded=build_info.passed,
            artifact_mask_list=[os.path.join(build_dir, mask) for mask in self._platform_config.artifact_mask_list],
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

    def _generate(self, src_dir, build_dir, build_params, cmake_configuration):
        src_full_path = os.path.abspath(src_dir)
        target_device = self._platform2target_device(build_params.platform)
        platform_args = []
        if target_device:
            platform_args += ['-DtargetDevice={}'.format(target_device)]
        if self._branch_config and self._branch_config.c_compiler:
            platform_args += ['-DCMAKE_C_COMPILER={}'.format(self._branch_config.c_compiler)]
        if self._branch_config and self._branch_config.cxx_compiler:
            platform_args += ['-DCMAKE_CXX_COMPILER={}'.format(self._branch_config.cxx_compiler)]
        generate_args = [
            '-DdeveloperBuild=OFF',
            '-DCMAKE_BUILD_TYPE=%s' % cmake_configuration,
            '-DcloudGroup=%s' % build_params.cloud_group,
            '-Dcustomization=%s' % build_params.customization,
            '-DbuildNumber=%d' % build_params.build_num,
            '-Dbeta=%s' % bool_to_cmake_param(build_params.is_beta),
            ]
        if build_params.add_qt_pdb is not None:
            generate_args += ['-DaddQtPdb=%s' % bool_to_cmake_param(build_params.add_qt_pdb)]
        generate_args += platform_args + [
            '-G', self._build_tool,
            src_full_path,
            ]
        # if build_params.target_device:
        #     generate_args.append('-DtargetDevice=%s' % build_params.target_device)
        log.info('Generating with cmake: %s', self._host.args2cmdline(generate_args))
        return self._run_timed_cmake(
            'Generation', generate_args, env=self._env, cwd=build_dir, check_retcode=False, timeout=GENERATE_TIMEOUT)

    def _build(self, build_dir, cmake_configuration):
        build_args = [
            '--build', '.',
            '--config', cmake_configuration,
            ]
        if self._build_tool == 'Ninja':
            build_args += [
            '--',
            '-j', str(PARALLEL_JOB_COUNT),
            ]
        log.info('Building with cmake: %s', self._host.args2cmdline(build_args))
        return self._run_timed_cmake(
            'Build', build_args, env=self._env, cwd=build_dir, check_retcode=False, timeout=BUILD_TIMEOUT)

    @property
    def _build_tool(self):
        return self._platform_config.generator or DEFAULT_GENERATOR

    def _run_timed_cmake(self, stage_name, *args, **kw):
        start_time = datetime_utc_now()
        results = self._run_cmake(*args, **kw)
        duration = datetime_utc_now() - start_time
        results.output += '\n' + '-- %s duration: %s\n' % (stage_name, junk_shop_utils.timedelta_to_str(duration))
        return results

    def _run_cmake(self, *args, **kw):
        try:
            command_results = self._cmake.run_cmake(*args, **kw)
            return CMakeResults.from_command_results(command_results)
        except ProcessTimeoutError as x:
            error_message = 'Timed out after %s' % x.timeout
            return CMakeResults(x.output, error_message, succeeded=False)

    def _platform2target_device(self, platform):
        if platform in ['linux-x64', 'win-x64', 'win-x86', 'mac']:
            return None  # targetDevice is not specified for them
        return platform

    @property
    def _env(self):
        return dict(os.environ,
                    environment=self._working_dir,
                    NINJA_STATUS='[%s/%t] %es  ',
                    _MSPDBSRV_ENDPOINT_='executor_%s' % self._executor_number,
                    )

    def _read_cmake_build_info_file(self, build_dir):
        path = os.path.join(build_dir, 'build_info.txt')
        if not os.path.isfile(path):
            return {}
        with open(path) as f:
            return dict([line.split('=') for line in f.read().splitlines()])

    @db_session
    def _store_log_artifacts(self, repository, build_dir, build_info):
        run = models.Run[build_info.run_id]
        for path in glob.glob(os.path.join(build_dir, LOGS_DIR, '*.log')):
            with open(path) as f:
                data = f.read()
            if not data.strip(): continue
            file_name, ext = os.path.splitext(os.path.basename(path))
            repository.add_artifact(run, file_name, file_name, repository.artifact_type.log, data)
            log.info('build log %r is stored to junk-shop database', path)


def test_me():
    setup_logging(logging.DEBUG)
    cmake = CMake('3.9.6')
    cmake.ensure_required_cmake_operational()

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
        add_qt_pdb=True,
        build_num=1000,
        configuration='release',
        )
    repository = DbCaptureRepository(db_config, build_params)
    builder = CMakeBuilder(1, config.platforms[platform], platform_branch_config, cmake)
    build_dir = 'build-{}'.format(platform)
    build_info = builder.build(repository, 'nx_vms', build_dir, clean_build=False)
    log.info('Build info: %r', build_info)


if __name__ == '__main__':
    test_me()
