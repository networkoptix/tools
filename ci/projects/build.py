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
import faulthandler

from utils import setup_logging, ensure_dir_exists, ensure_dir_missing, is_list_inst
from config import PlatformConfig, Config, PlatformBranchConfig, BranchConfig
from host import ProcessTimeoutError, CommandResults, LocalHost
from cmake import CMake
from junk_shop import DbConfig, models, BuildParameters, DbCaptureRepository, store_output_and_error, datetime_utc_now
from junk_shop import utils as junk_shop_utils

log = logging.getLogger(__name__)


GENERATE_TIMEOUT = datetime.timedelta(hours=2)
BUILD_TIMEOUT = datetime.timedelta(hours=4)
BUILD_SAVE_TIMEOUT = datetime.timedelta(hours=1)  # kill job if saving to junk-shop db timed out
DEFAULT_GENERATOR = 'Ninja'
LOGS_DIR = 'build_logs'
PARALLEL_JOB_COUNT = 20


class BuildInfo(namedtuple(
    'BuildInfo', [
        'is_succeeded',
        'artifacts_dir',
        'current_config_path',
        'version',
        'unit_tests_bin_dir',
        'run_id',
        ])):

    @classmethod
    def from_dict(cls, data):
        return cls(
            is_succeeded=data['is_succeeded'],
            artifacts_dir=data['artifacts_dir'],
            current_config_path=data['current_config_path'],
            version=data['version'],
            unit_tests_bin_dir=data['unit_tests_bin_dir'],
            run_id=data['run_id'],
            )

    def __init__(self, is_succeeded, artifacts_dir, current_config_path, version, unit_tests_bin_dir, run_id):
        assert isinstance(is_succeeded, bool), repr(is_succeeded)
        assert isinstance(artifacts_dir, basestring), repr(artifacts_dir)
        assert isinstance(current_config_path, basestring), repr(current_config_path)
        assert version is None or isinstance(version, basestring), repr(version)
        assert isinstance(unit_tests_bin_dir, basestring), repr(unit_tests_bin_dir)
        assert isinstance(run_id, int), repr(run_id)
        super(BuildInfo, self).__init__(
            is_succeeded=is_succeeded,
            artifacts_dir=artifacts_dir,
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
        return 'ON'
    else:
        return 'OFF'


class CMakeBuilder(object):

    PlatformConfig = namedtuple('PlatformConfig', 'is_unix')
    CommandLog = namedtuple('CommandLog', 'file_name contents')

    _system_platform_config = dict(
        Linux=PlatformConfig(is_unix=True),
        Darwin=PlatformConfig(is_unix=True),
        Windows=PlatformConfig(is_unix=False),
        )

    def __init__(self, executor_number, platform_config, branch_config, junk_shop_repository, cmake):
        assert isinstance(executor_number, int), repr(executor_number)
        assert isinstance(platform_config, PlatformConfig), repr(platform_config)
        assert branch_config is None or isinstance(branch_config, PlatformBranchConfig), repr(branch_config)
        assert isinstance(junk_shop_repository, DbCaptureRepository), repr(junk_shop_repository)
        assert isinstance(cmake, CMake), repr(cmake)
        self._executor_number = executor_number
        self._platform_config = platform_config
        self._branch_config = branch_config
        self._junk_shop_repository = junk_shop_repository
        self._cmake = cmake
        self._host = LocalHost()
        self._system = platform.system()
        self._working_dir = os.getcwd()  # python steps are run in working dir
        self._command_logs = []  # CommandLog list

    @property
    def _is_unix(self):
        return self._system_platform_config[self._system].is_unix

    def build(
            self,
            src_dir,
            build_dir,
            webadmin_external_dir,
            custom_cmake_args,
            build_tests,
            signing,
            hardware_signing,
            use_trusted_timestamping,
            clean_build,
            ):
        build_params = self._junk_shop_repository.build_parameters
        self._prepare_build_dir(build_dir, clean_build)
        cmake_configuration = build_params.configuration.capitalize()
        generate_results = self._generate(
            src_dir,
            build_dir,
            webadmin_external_dir,
            build_params,
            custom_cmake_args,
            build_tests,
            signing,
            hardware_signing,
            use_trusted_timestamping,
            cmake_configuration,
            )
        succeeded = generate_results.succeeded
        error_message = generate_results.error_message
        output = generate_results.output
        if generate_results.succeeded:
            self._run_post_generate_cleaning(build_dir)
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

        output_path = os.path.join(self._working_dir, 'build-output.log')
        log.info('Storing build output to %r...', output_path)
        with open(output_path, 'w') as f:
            f.write(output)
        log.info('Storing output to junk-shop db...')
        if getattr(faulthandler, 'dump_traceback_later', None):
            faulthandler.dump_traceback_later(int(BUILD_SAVE_TIMEOUT.total_seconds()), exit=True)
        build_info = store_output_and_error(self._junk_shop_repository, output, succeeded, error_message)
        if getattr(faulthandler, 'cancel_dump_traceback_later', None):
            faulthandler.cancel_dump_traceback_later()

        log.info('Storing log artifacts to junk-shop db...')
        self._store_log_artifacts(build_dir, build_info)
        log.info('Reading build info file...')
        cmake_build_info = self._read_cmake_build_info_file(build_dir)
        log.info('Build results are stored to junk-shop database at %r: outcome=%r, run.id=%r',
                     self._junk_shop_repository.db_config, build_info.outcome, build_info.run_id)
        return BuildInfo(
            is_succeeded=build_info.passed,
            artifacts_dir=os.path.join(build_dir, 'distrib'),
            current_config_path=os.path.join(build_dir, 'current_config.py'),
            version=cmake_build_info.get('version'),
            unit_tests_bin_dir=os.path.join(build_dir, 'bin'),
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
            output = self._host.get_command_output(['python', cleaner, '--build-dir', build_dir])
            file_name = os.path.splitext(os.path.split(cleaner)[1])[0]
            self._add_command_log(file_name, output)
        else:
            ensure_dir_missing(os.path.join(build_dir, 'distrib'))  # todo: remove when cleaner is merged to all branches

    def _run_post_generate_cleaning(self, build_dir):
        if self._generator == 'Ninja':
            cleaner = 'devtools/ninja_clean/ninja_clean.py'
            if os.path.isfile(cleaner):
                log.info('Cleaning using %s', cleaner)
                output = self._host.get_command_output(['python', cleaner, '--build-dir', build_dir])
                self._add_command_log('ninja_clean', output)

    def _generate(
            self,
            src_dir,
            build_dir,
            webadmin_external_dir,
            build_params,
            custom_cmake_args,
            build_tests,
            signing,
            hardware_signing,
            use_trusted_timestamping,
            cmake_configuration,
            ):
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
            '-DcustomWebAdminPackageDirectory=%s' % webadmin_external_dir,
            '-DbuildNumber=%d' % build_params.build_num,
            '-Dbeta=%s' % bool_to_cmake_param(build_params.is_beta),
            ]
        if not build_tests:
            generate_args += ['-DwithTests=%s' % bool_to_cmake_param(False)]
        if build_params.add_qt_pdb is not None:
            generate_args += ['-DaddQtPdb=%s' % bool_to_cmake_param(build_params.add_qt_pdb)]
        if hardware_signing:
            generate_args += ['-DhardwareSigning=ON']
        if signing:
            generate_args += ['-DtrustedTimestamping=%s' % bool_to_cmake_param(use_trusted_timestamping)]
        else:
            generate_args += ['-DcodeSigning=OFF']
        generate_args += platform_args
        if custom_cmake_args:
            generate_args += custom_cmake_args.split(' ')
        generate_args += ['-G', self._generator]
        if self._platform_config.toolset:
            generate_args += ['-T', self._platform_config.toolset]
        generate_args += [src_full_path]
        # if build_params.target_device:
        #     generate_args.append('-DtargetDevice=%s' % build_params.target_device)
        log.info('Generating with cmake: %s', self._host.args2cmdline(generate_args))
        return self._run_and_decorate_cmake(
            'Generation', generate_args, env=self._env, cwd=build_dir, check_retcode=False, timeout=GENERATE_TIMEOUT)

    def _build(self, build_dir, cmake_configuration):
        build_args = [
            '--build', '.',
            '--config', cmake_configuration,
            ]
        if self._generator == 'Ninja':
            build_args += [
            '--',
            '-j', str(PARALLEL_JOB_COUNT),
            ]
        log.info('Building with cmake: %s', self._host.args2cmdline(build_args))
        return self._run_and_decorate_cmake(
            'Build', build_args, env=self._env, cwd=build_dir, check_retcode=False, timeout=BUILD_TIMEOUT)

    @property
    def _generator(self):
        return self._platform_config.generator or DEFAULT_GENERATOR

    def _run_and_decorate_cmake(self, stage_name, cmake_args, **kw):
        start_time = datetime_utc_now()
        results = self._run_cmake(cmake_args, **kw)
        duration = datetime_utc_now() - start_time
        cmdline_info = '-- command line: %s' % self._cmake.get_cmake_cmdline(cmake_args)
        duration_info = '-- %s duration: %s\n' % (stage_name, junk_shop_utils.timedelta_to_str(duration))
        results.output = '\n'.join([cmdline_info, results.output, duration_info])
        return results

    def _run_cmake(self, cmake_args, **kw):
        try:
            command_results = self._cmake.run_cmake(cmake_args, **kw)
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

    def _add_command_log(self, file_name, contents):
        self._command_logs.append(self.CommandLog(file_name, contents.strip()))

    @db_session
    def _store_log_artifacts(self, build_dir, build_info):
        run = models.Run[build_info.run_id]
        for path in glob.glob(os.path.join(build_dir, LOGS_DIR, '*.log')):
            with open(path) as f:
                data = f.read()
            if not data.strip(): continue
            file_name, ext = os.path.splitext(os.path.basename(path))
            self._junk_shop_repository.add_artifact(
                run, file_name, file_name, self._junk_shop_repository.artifact_type.log, data)
            log.info('build log %r is stored to junk-shop database', path)
        for command_log in self._command_logs:
            self._junk_shop_repository.add_artifact(
                run, command_log.file_name, command_log.file_name, self._junk_shop_repository.artifact_type.log, command_log.contents)
            log.info('log %r is stored to junk-shop database', command_log.file_name)

    @db_session
    def _add_log_artifact(self, build_info, file_name, contents):
        run = models.Run[build_info.run_id]
        self._junk_shop_repository.add_artifact(run, file_name, file_name, self._junk_shop_repository.artifact_type.log, contents)
        log.info('log %r is stored to junk-shop database', file_name)


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
    if len(sys.argv) >= 6 and sys.argv[5]:
        branch_config = BranchConfig.from_dict(yaml.load(open(sys.argv[5])))
        platform_branch_config = branch_config.platforms.get(platform)
    else:
        platform_branch_config = None
    if len(sys.argv) >= 7 and sys.argv[6]:
        custom_cmake_args = sys.argv[6]
    else:
        custom_cmake_args = ''
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
    builder = CMakeBuilder(1, config.platforms[platform], platform_branch_config, repository, cmake)
    build_dir = 'build-{}'.format(platform)
    build_info = builder.build('nx_vms', build_dir, 'webadmin-external', custom_cmake_args, build_tests=True, clean_build=False)
    log.info('Build info: %r', build_info)


if __name__ == '__main__':
    test_me()
