# copy artifact files to daily-build directory, creating directory structure required by depcon

import logging
import os.path

from host import RemoteSshHost

log = logging.getLogger(__name__)


class Deployer(object):

    def __init__(self, config, artifacts_stored_in_different_customization_dirs, ssh_key_file, build_num, branch):
        self._config = config
        self._artifacts_stored_in_different_customization_dirs = artifacts_stored_in_different_customization_dirs
        self._build_num = build_num
        self._branch = branch
        self._host = RemoteSshHost.from_path('deploy', self._config.services.deployment_path, key_file_path=ssh_key_file)
        self._created_target_dirs = set()

    def deploy_artifacts(self, customization_list, platform_list, build_info_path, platform_build_info_map):
        target_root_dir = self._config.services.deployment_path.split(':')[1]
        target_dir = os.path.join(
            target_root_dir,
            '{}-{}'.format(self._build_num, self._branch),
            )
        src_root_dir = 'dist'
        self._deploy_build_info(build_info_path, target_dir)
        for customization in customization_list:
            if self._artifacts_stored_in_different_customization_dirs:
                src_dir = os.path.join(src_root_dir, customization)
            else:
                src_dir = src_root_dir
            for platform in platform_list:
                platform_config = self._config.platforms[platform]
                platform_build_info = platform_build_info_map[(customization, platform)]
                self._deploy_platform_artifacts(platform_config, customization, platform, platform_build_info, src_dir, target_dir)

    def _deploy_build_info(self, build_info_path, target_dir):
        src_dir, name = os.path.split(build_info_path)
        self._put_file(src_dir, target_dir, name)

    def _deploy_platform_artifacts(self, platform_config, customization, platform, platform_build_info, src_dir, target_dir):
        self._deploy_distributives(platform_config, customization, platform_build_info, src_dir, target_dir)
        self._deploy_updates(platform_config, customization, platform_build_info, src_dir, target_dir)
        self._deploy_qtpdb(platform_config, customization, platform, platform_build_info, src_dir, target_dir)
        self._deploy_misc(platform_config, customization, platform, platform_build_info, src_dir, target_dir)

    def _deploy_distributives(self, platform_config, customization, platform_build_info, src_dir, target_root_dir):
        # to <build-num>-<branch>/<customization>/<platform-publish-dir>/
        target_dir = os.path.join(target_root_dir, customization, platform_config.publish_dir)
        for name in platform_build_info.typed_artifact_list.get('distributive', []):
            self._put_file(src_dir, target_dir, name)

    def _deploy_updates(self, platform_config, customization, platform_build_info, src_dir, target_root_dir):
        # to <build-num>-<branch>/<customization>/updates/<build-num>/
        target_dir = os.path.join(target_root_dir, customization, 'updates', str(self._build_num))
        for name in platform_build_info.typed_artifact_list.get('update', []):
            self._put_file(src_dir, target_dir, name)

    def _deploy_qtpdb(self, platform_config, customization, platform, platform_build_info, src_dir, target_root_dir):
        # to <build-num>-<branch>/qtpdb/<platform>
        target_dir = os.path.join(target_root_dir, 'qtpdb', platform)
        for name in platform_build_info.typed_artifact_list.get('qtpdb', []):
            self._put_file(src_dir, target_dir, name)

    def _deploy_misc(self, platform_config, customization, platform, platform_build_info, src_dir, target_root_dir):
        # to <build-num>-<branch>/<customization>/misc/<platform>
        target_dir = os.path.join(target_root_dir, customization, 'misc', platform)
        for name in platform_build_info.typed_artifact_list.get('misc', []):
            self._put_file(src_dir, target_dir, name)

    def _put_file(self, src_dir, target_dir, name):
        src_path = os.path.join(src_dir, name)
        if not os.path.isfile(src_path):
            log.warning('Artifact %r is missing; unable to publish', src_path)
            return
        log.info('Deploying %s to %s:%s', name, self._host.host, target_dir)
        if not target_dir in self._created_target_dirs:
            self._host.mk_dir(target_dir)
            self._created_target_dirs.add(target_dir)
        self._host.put_file(src_path, os.path.join(target_dir, name))
