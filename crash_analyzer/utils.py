#!/usr/bin/env python3

import logging
import os
import string
import sys
from typing import Any

import yaml


def setup_logging(level: str = 'debug', path: str = '-'):
    """Sets up application log :level and :path.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), None) or int(args.level),
        stream=sys.stdout if path == '-' else open(path, 'w'),
        format='%(asctime)s %(levelname)-8s %(name)s: %(message)s')

    logging.info('Log is configured for level: {}, file: {}'.format(level, path))


def is_ascii_printable(s: str):
    try:
        s.encode('ascii')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return False
    else:
        return all(c in string.printable for c in s)


def file_content(path: str) -> str:
    with open(path, 'r') as f:
        return f.read().replace('\r', '')


def file_parse(path: str):
    return yaml.load(file_content(path))


def file_serialize(value: Any, path: str):
    with open(path, 'w') as f:
        f.write(yaml.dump(value, default_flow_style=False))


def resource_path(name: str) -> str:
    return os.path.join(os.path.dirname(__file__), 'resources', name)


def resource_content(name: str) -> str:
    return file_content(resource_path(name))


def resource_parse(name: str):
    return yaml.load(resource_content(name))
