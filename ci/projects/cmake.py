import logging
import os.path
import datetime
import re
from collections import namedtuple
import platform
import shutil
import tarfile
import zipfile
from utils import setup_logging, add_env_element, save_url_to_file
from host import LocalHost

log = logging.getLogger(__name__)


CMAKE_ROOT_DIR = 'cmake'
CMAKE_DIST_URL = 'https://cmake.org/files'
CMAKE_CHECK_TIMEOUT = datetime.timedelta(minutes=1)


class CMake(object):

    PlatformConfig = namedtuple('PlatformConfig', 'dist_suffix bin_dir')

    platform_config = dict(
        Linux=PlatformConfig('Linux-x86_64', 'bin'),
        Darwin=PlatformConfig('Darwin-x86_64', 'CMake.app/Contents/bin'),
        Windows=PlatformConfig('win64-x64', 'bin'),
        )

    def __init__(self, cmake_version):
        self._host = LocalHost()
        self._cmake_version = cmake_version
        self._system = platform.system()
        self._is_unix = self._system != 'Windows'

    def ensure_required_cmake_operational(self):
        if self._is_required_cmake_operational():
            return
        self._setup_cmake()
        assert self._is_required_cmake_operational(), 'CMake version %s is still not operational after it has been setup' % self._cmake_version

    def run_cmake(self, cmake_args, env=None, cwd=None, check_retcode=True, timeout=None):
        cmake_bin_dir = os.path.join(
            os.getcwd(), CMAKE_ROOT_DIR, self._cmake_base_name, self.platform_config[self._system].bin_dir)
        env = add_env_element(env or os.environ, 'PATH', cmake_bin_dir)
        log.debug('cmake path: %r', env['PATH'])
        args = ['cmake'] + cmake_args
        return self._host.run_command(args, cwd=cwd, env=env, check_retcode=check_retcode, timeout=timeout, merge_stderr=True)

    @property
    def _cmake_base_name(self):
        return 'cmake-%s-%s' % (self._cmake_version, self.platform_config[self._system].dist_suffix)

    def _is_required_cmake_operational(self):
        log.info('Checking if cmake version %s is ready', self._cmake_version)
        try:
            result = self.run_cmake(['--version'], check_retcode=False, timeout=CMAKE_CHECK_TIMEOUT)
        except OSError as x:
            log.debug('Failed: %s', x)
            return False
        log.debug('cmake version check reult: %r', result)
        if result.exit_code != 0:
            return False
        mo = re.match(r'cmake version (\d+\.\d+\.\d+)', result.stdout)
        if not mo:
            return False
        found_version = mo.group(1)
        is_matching = found_version == self._cmake_version
        log.info('Found cmake version: %s, matched: %s', found_version, is_matching)
        return is_matching

    def _setup_cmake(self):
        if os.path.exists(CMAKE_ROOT_DIR):
            log.info('Removing previous cmake installation at %s', CMAKE_ROOT_DIR)
            shutil.rmtree(CMAKE_ROOT_DIR)
        dist_name = '%s.%s' % (self._cmake_base_name, 'tar.gz' if self._is_unix else 'zip')
        version_dir =  '.'.join(self._cmake_version.split('.')[:2])  # first two digits are used as version part in url
        url = '%s/v%s/%s' % (CMAKE_DIST_URL, version_dir, dist_name)
        dist_path = os.path.join(CMAKE_ROOT_DIR, dist_name)
        save_url_to_file(url, dist_path)
        log.info('Unpacking %s', dist_path)
        if self._is_unix:
            with tarfile.open(dist_path) as tar:
                tar.extractall(CMAKE_ROOT_DIR)
        else:
            with zipfile.ZipFile(dist_path) as zip:
                zip.extractall(CMAKE_ROOT_DIR)


def test_me():
    setup_logging(logging.DEBUG)
    cmake = CMake('3.9.6')
    cmake.ensure_required_cmake_operational()


if __name__ == '__main__':
    test_me()
