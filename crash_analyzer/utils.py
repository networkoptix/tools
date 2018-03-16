#!/usr/bin/python

import argparse
import logging
import os
import string
import sys
import unittest

from pprint import pformat, pprint

LOG_FORMAT='%(asctime)s %(levelname)-8s %(name)s: %(message)s'

def is_ascii_printable(s):
    try:
        s.encode('ascii')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return False
    else:
        return all(c in string.printable for c in s)

def file_content(path):
    with open(path, 'r') as f:
        return f.read().replace('\r', '')

def resource_path(name):
    return os.path.join(os.path.dirname(__file__), 'resources', name)

def resource_content(name):
    return file_content(resource_path(name))

def assert_eq(expected, actual, name=''):
    assert expected == actual, 'mismatch: {}\nExpected:\n{}\nActual:\n{}'.format(
        name, pformat(expected), pformat(actual))

def setup_logging(level=0):
    logging.basicConfig(level=level, format=LOG_FORMAT, stream=sys.stdout)
    logging.info('Log is configured for level: {}'.format(level))

class TestCase(unittest.TestCase):
    def setUp(self):
        print('-' * 70)
        print('{}.{}'.format(type(self).__name__, self._testMethodName))

def run_ut():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', type=str, default="info")
    parser.add_argument('module', nargs='?', help="TestCase[.test]")

    args = parser.parse_args()
    setup_logging(
        getattr(logging, args.log_level.upper(), None) or int(args.log_level))

    sys.argv = sys.argv[:1]
    if args.module:
        sys.argv.append(args.module)

    unittest.main(verbosity=0)
