#!/usr/bin/env python3

import logging
import os
import string
import sys
import json
import multiprocessing
import random
import shutil
import traceback
from glob import glob
from typing import Callable, Any

import yaml

logger = logging.getLogger(__name__)

LOGGING_FORMAT = '%(asctime)s %(levelname)-8s %(name)s: %(message)s'
POWER_SUFFIXES = dict(
    k=1000, m=1000**2, g=1000**3, t=1000*4,
    K=1024, M=1024**2, G=1024**3, T=1024*4,
)


def setup_logging(level: str = 'debug', path: str = '-'):
    """Sets up application log :level and :path.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), None) or int(level),
        stream=sys.stdout if path == '-' else open(path, 'w'),
        format=LOGGING_FORMAT)

    logging.info('Log is configured with level: {}, file: {}'.format(level, path))


def is_ascii_printable(s: str):
    try:
        s.encode('ascii')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return False
    else:
        return all(c in string.printable for c in s)


def parse_number(number: str):
    for s in POWER_SUFFIXES:
        if number.endswith(s):
            return int(number[:-len(s)]) * POWER_SUFFIXES[s]

    return int(s)


class BufferedStream:
    def __init__(self):
        self.buffers = []

    def write(self, data):
        self.buffers.append(data)

    def lines(self):
        return ''.join(self.buffers).splitlines()


def _concurrent_main(task):
    log_stream = BufferedStream()
    logging.basicConfig(level=task['log_level'], stream=log_stream, format=LOGGING_FORMAT)
    action, argument, kwargs = task['action'], task['argument'], task['kwargs']
    try:
        logging.debug('Do {}.{} with {}'.format(action.__module__, action.__name__, argument))
        result = action(argument, **kwargs)
        logging.debug('Result: {}'.format(result))
    except Exception as exception:
        result = exception
        logging.debug('Exception: {}'.format(traceback.format_exc()))
        if getattr(run_concurrent, 'debug', None) == 'raise':
            raise

    return {'result': result, 'logs': log_stream.lines()}


def run_concurrent(action: Callable, tasks: list, thread_count: int, **kwargs):
    results = []
    log_level = logger.getEffectiveLevel()

    def save_result(result, logs):
        results.append(result)
        for line in logs:
            logger.info(line)

    def wrap_task(t):
        return {'action': action, 'argument': t, 'kwargs': kwargs, 'log_level': log_level}

    if not hasattr(run_concurrent, 'debug'):
        with multiprocessing.Pool(thread_count) as pool:
            for result in pool.map(_concurrent_main, (wrap_task(t) for t in tasks)):
                save_result(**result)
    else:
        for task in tasks:
            save_result(**_concurrent_main(wrap_task(task)))

    return results


def test_concurrent(action: Callable, argument: Any, thread_count: int):
    results = [run_concurrent(action, [argument] * thread_count, thread_count)]
    assert [repr(r) for r in results if isinstance(r, Exception)] == []


class File:
    def __init__(self, *path):
        self.path = os.path.join(*path)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.path))

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def extension(self) -> str:
        return self.path.split('.')[-1]

    def write(self, action, mode=''):
        """Executes an :action on a file, opened for writing.
        """
        with open(self.path, 'w' + mode) as f:
            action(f)

    def read(self, action, default=None, mode=''):
        """Executes an :action on a file, opened for writing.
        If file does not exist and default provided, it will be returned instead of an exception.
        """
        try:
            with open(self.path, 'r' + mode) as f:
                return action(f)
        except FileNotFoundError:
            if default is None: raise
            logger.warning('Read "{}" for non-existing file: {}'.format(default, self.path))
            return default

    def write_string(self, data):
        self.write(lambda f: f.write(data))

    def read_string(self, default=None):
        return self.read(lambda f: f.read(), default)

    def write_bytes(self, data):
        self.write(lambda f: f.write(data), 'b')

    def read_bytes(self, default=None):
        return self.read(lambda f: f.read(), default, 'b')

    def write_json(self, data):
        self.write(lambda f: json.dump(data, f))

    def read_json(self, default=None):
        return self.read(lambda f: json.load(f), default)

    def write_yaml(self, data):
        self.write(lambda f: yaml.dump(data, f))

    def read_yaml(self, default=None):
        return self.read(lambda f: yaml.load(f), default)

    def write_container(self, generator, brackets='{}'):
        opener, closer = brackets
        with open(self.path, 'w') as f:
            f.write(opener)
            try:
                f.write('\n' + next(generator))
                while True:
                    f.write(',\n' + next(generator))
            except StopIteration:
                f.write('\n' + closer)

    def serialize(self, data):
        if self.extension == 'json':
            return self.write_json(data)
        if self.extension == 'yaml':
            return self.write_yaml(data)
        raise NotImplemented('Unsupported format "{}" file: {}'.format(f, self.path))

    def parse(self, *args, **kwargs):
        if self.extension == 'json':
            return self.read_json(*args, **kwargs)
        if self.extension == 'yaml':
            return self.read_yaml(*args, **kwargs)
        raise NotImplemented('Unsupported format "{}" file: {}'.format(f, self.path))


class Directory:
    def __init__(self, *path):
        self.path = os.path.join(*path)

    def file(self, name):
        return File(self.path, name)

    def files(self, mask: str = '*'):
        return [File(f) for f in glob(os.path.join(self.path, mask))]

    def directory(self, *path):
        return Directory(self.path, *path)

    def make(self):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

    def remove(self):
        shutil.rmtree(self.path)


class TemporaryDirectory(Directory):
    def __init__(self):
        super().__init__('./_tmp_directory_' + '{0:0>5}'.format(random.randint(0, 99999)))

    def __enter__(self):
        logging.info('New temporary directory: ' + self.path)
        self.make()
        return self

    def __exit__(self, *args):
        logging.info('Remove temporary directory: ' + self.path)
        self.remove()


class Resource(File):
    def __init__(self, *path):
        if not os.path.isabs(path[0]):
            path = [os.path.dirname(os.path.abspath(__file__)), 'resources'] + list(path)

        super().__init__(*path)

    def directory(self, *path):
        return Directory(self.path, *path)

    def glob(self, *path):
        return [Resource(p) for p in glob(os.path.join(self.path, *path))]
