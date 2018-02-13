# copy artifact files to daily-build directory, creating directory structure required by depcon

import logging
import os.path

from host import RemoteSshHost

log = logging.getLogger(__name__)


def deploy_artifacts(
        config,
        artifacts_stored_in_different_customization_dirs,
        ssh_key_file,
        build_num,
        branch,
        customization_list,
        platform_list,
        platform_build_info_map,
        ):
    host = RemoteSshHost.from_path('deploy', config.services.deployment_path, key_file_path=ssh_key_file)
    target_root_dir = config.services.deployment_path.split(':')[1]
    target_dir = os.path.join(
        target_root_dir,
        '{}-{}'.format(build_num, branch),
        )
    src_root_dir = 'dist'
    for customization in customization_list:
        if artifacts_stored_in_different_customization_dirs:
            src_dir = os.path.join(src_root_dir, customization)
        else:
            src_dir = src_root_dir
        for platform in platform_list:
            platform_config = config.platforms[platform]
            platform_build_info = platform_build_info_map[(customization, platform)]
            deploy_platform_artifacts(host, platform_config, build_num, customization, platform_build_info, src_dir, target_dir)

def deploy_platform_artifacts(host, platform_config, build_num, customization, platform_build_info, src_dir, target_dir):
    dist_dir = os.path.join(target_dir, customization, platform_config.publish_dir)
    dist_dir_created = False
    for name in platform_build_info.typed_artifact_list.get('distributive', []):
        src_path = os.path.join(src_dir, name)
        if os.path.isfile(src_path):
            log.info('Deploying %s to %s:%s', name, host.host, dist_dir)
            if not dist_dir_created:
                host.mk_dir(dist_dir)
                dist_dir_created = True
            host.put_file(src_path, os.path.join(dist_dir, name))
        else:
            log.warning('Artifact %r is missing; unable to publish', src_path)
    updates_dir = os.path.join(target_dir, customization, 'updates', str(build_num))
    updates_dir_created = False
    for name in platform_build_info.typed_artifact_list.get('update', []):
        src_path = os.path.join(src_dir, name)
        if os.path.isfile(src_path):
            log.info('Deploying %s to %s:%s', name, host.host, updates_dir)
            if not updates_dir_created:
                host.mk_dir(updates_dir)
                updates_dir_created = True
            host.put_file(src_path, os.path.join(updates_dir, name))
        else:
            log.warning('Artifact %r is missing; unable to publish', src_path)
