#!/usr/bin/env python

import argparse
import os
import uuid
import subprocess

config_path = os.path.expandvars('%LOCALAPPDATA%\\nx_server')
config_extension = '.conf'
runtime_config_suffix = '-runtime'

config_template = '''[General]
guidIsHWID=no
publicIPEnabled=1
removeDbOnStartup=0
authKey=@ByteArray(SK_bacb0b7c7ceb0e9b1a8949af6d0c8187)
isConnectedToCloud=no
createFullCrashDump=true
serverGuid={0}
port=7001
dataDir={1}/{2}
logFile={1}/{2}/log/log_file
enableMultipleInstances=1
logLevel=debug
'''


def config_file(config):
    return os.path.join(config_path, config) + config_extension


def runtime_config_file(config):
    return os.path.join(config_path, config) + runtime_config_suffix + config_extension


def check_config(config):
    config_file_path = config_file(config)
    print 'Using config {}'.format(config_file_path)
    if os.path.isfile(config_file_path):
        return

    if not os.path.exists(config_path):
        os.makedirs(config_path)

    posix_path = os.path.normpath(config_path).replace('\\', '/')
    id = str(uuid.uuid4())
    with open(config_file_path, 'w') as conf:
        conf.write(config_template.format(id, posix_path, config))


def run_server(config, verbose):
    command = [
        'mediaserver.exe',
        '-e',
        '--conf-file',
        config_file(config),
        '--runtime-conf-file',
        runtime_config_file(config),
        '--dev-mode-key',
        'razrazraz'
    ]
    if verbose:
        print(' '.join(command))
    subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs=1, help="Server config.")
    parser.add_argument("-v", "--verbose", action='store_true', help="Verbose output.")
    args = parser.parse_args()
    check_config(args.config[0])
    run_server(args.config[0], args.verbose)


if __name__ == "__main__":
    if not main():
        exit(1)
