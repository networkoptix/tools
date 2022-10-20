#!/usr/bin/env python

from __future__ import print_function
from pathlib import Path
import argparse
import os
import shutil
import sys
import uuid
import subprocess

WINDOWS = sys.platform in ("win32", "cygwin")
SERVER_EXECUTABLE = "mediaserver.exe" if WINDOWS else "./mediaserver"

config_path = Path(os.path.expandvars(
    "%LOCALAPPDATA%\\nx_server" if WINDOWS else "$HOME/.config/nx_server"))
config_extension = ".conf"
runtime_config_suffix = "-runtime"

config_template = """[General]
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
"""


def config_file(config):
    return config_path / f"{config}{config_extension}"


def runtime_config_file(config):
    return config_path / f"{config}{runtime_config_suffix}{config_extension}"


def list_configs():
    for config in config_path.glob("*" + config_extension):
        if runtime_config_suffix not in config.name:
            yield config.name.replace(config_extension, "")


def delete_config(config):
    print(f"Delete config {config}")

    with config_file(config) as cfg:
        if cfg.exists():
            cfg.unlink()

    with runtime_config_file(config) as cfg:
        if cfg.exists():
            cfg.unlink()

    with Path(config_path) / config as data:
        if data.exists():
            shutil.rmtree(data)


def check_config(config):
    config_file_path = config_file(config)
    print(f"Using config {config_file_path}")
    if config_file_path.is_file():
        return

    if not config_path.exists():
        os.makedirs(config_path)

    posix_path = config_path.as_posix()
    id = str(uuid.uuid4())
    with open(config_file_path, "w") as conf:
        conf.write(config_template.format(id, posix_path, config))


def run_server(config, verbose, *args):
    command = [
        SERVER_EXECUTABLE,
        "-e",
        "--conf-file", config_file(config).as_posix(),
        "--runtime-conf-file", runtime_config_file(config).as_posix()
    ]
    command += args
    if verbose:
        print(" ".join(command))

    kwargs = {"creationflags": subprocess.CREATE_NEW_CONSOLE} if WINDOWS else {}
    subprocess.run(command, **kwargs)
    subprocess.run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config", nargs='?', help="Server config. Use 'list' to list existing configs")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    parser.add_argument("--delete", action="store_true", help="Delete target config.")
    args, unknown = parser.parse_known_args()

    config = None
    existing = list(list_configs())
    if not args.config:
        if len(existing) == 1:
            config = existing[0]
            print(f"Using default config {config}")
        elif len(existing) == 0:
            config = Path().absolute().parent.parent.name
            print(f"Create default config {config}")
        else:
            parser.print_help()
            return

    if not config:
        config = args.config[0]

    if config == "list":
        for config in existing:
            print(config)
        return

    if args.delete:
        delete_config(config)
        return

    check_config(config)
    run_server(config, args.verbose, *unknown)


if __name__ == "__main__":
    main()
