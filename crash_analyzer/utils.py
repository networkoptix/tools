#!/usr/bin/env python3

import argparse
import logging
import os
import string
import sys
import unittest
from pprint import pformat

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


def resource_path(name: str) -> str:
    return os.path.join(os.path.dirname(__file__), 'resources', name)


def resource_content(name: str) -> str:
    return file_content(resource_path(name))


def resource_parse(name: str):
    return yaml.load(resource_content(name))


def assert_eq(expected, actual, name: str = ''):
    assert expected == actual, 'mismatch: {}\nExpected:\n{}\nActual:\n{}'.format(
        name, pformat(expected), pformat(actual))


class TestCase(unittest.TestCase):
    MAX_DIFF = 1000

    def setUp(self):
        self.maxDiff = self.MAX_DIFF
        print('-' * 70)
        print('{}.{}'.format(type(self).__name__, self._testMethodName))


def run_unit_tests():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help='more output and logs')
    parser.add_argument('-l', '--log-level', type=str, default="error")
    parser.add_argument('module', nargs='?', help="TestCase[.test]")

    arguments = parser.parse_args()
    if arguments.verbose:
        arguments.log_level = 'debug'
        TestCase.MAX_DIFF = None

    sys.argv = sys.argv[:1]
    if arguments.module:
        sys.argv.append(arguments.module)

    setup_logging(arguments.log_level)
    unittest.main(verbosity=0)
