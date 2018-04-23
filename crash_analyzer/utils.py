#!/usr/bin/env python3

import logging
import logging.handlers
import os
import string
import sys
import json
import multiprocessing
import random
import shutil
import traceback
from glob import glob
from typing import Callable, Any, Union, List

import yaml

logger = logging.getLogger(__name__)

LOGGING_FORMAT = '%(asctime)s %(levelname)-8s %(name)s: %(message)s'
POWER_SUFFIXES = dict(
    k=1000, m=1000**2, g=1000**3, t=1000*4,
    K=1024, M=1024**2, G=1024**3, T=1024*4,
)


class Error(Exception):
    pass


class KeyboardInterruptError(Error):
    pass


def stream_log_handler(stream_name: str = 'stdout'):
    streams = dict(stdout=sys.stdout, stderr=sys.stderr)
    return logging.StreamHandler(streams[stream_name])


def rotating_log_handler(base_name: str, max_size: int = 1, backup_count: str = 1):
    File(base_name).directory().make()
    return logging.handlers.RotatingFileHandler(
        base_name, 'a', Size(max_size).bytes, backup_count)


def setup_logging(level: str = 'debug', title: str = '', stream: str = '', rotating_file: dict = {}):
    """Sets up application log :level and :path.
    """
    handlers = []
    details = 'Level: {}'.format(level)
    if stream:
        handlers.append(stream_log_handler(stream))
        details += ', stream: {}'.format(stream)
    if rotating_file:
        handlers.append(rotating_log_handler(**rotating_file))
        details += ', ' + ', '.join('{}: {}'.format(*i) for i in rotating_file.items())

    logging.basicConfig(
        level=getattr(logging, level.upper(), None) or int(level),
        format=LOGGING_FORMAT, handlers=handlers)

    logging.info('=' * 80)
    if title:
        print(title)
        logging.info(title)

    logging.info(details)


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


def update_dict(dictionary: dict, request: str):
    """Updates dictionary values, by string syntax in request:
        s1.v1=abc   -> dictionary['s1']['v1'] = 'abc'
        s2.s3.v2=3  -> dictionary['s2']['s3']['v2'] = 3
        v3=[1,2,3]  -> dictionary['v3'] = [1, 2, 3]
    """
    key, value = request.split('=')
    *path, name = key.split('.')
    for item in path:
        dictionary = dictionary.setdefault(item, {})
    dictionary[name] = yaml.load(value)


class BufferedStream:
    def __init__(self):
        self.buffers = []

    def write(self, data):
        self.buffers.append(data)

    def lines(self):
        return ''.join(self.buffers).splitlines()


def _concurrent_main(task):
    log_stream = BufferedStream()
    debug = getattr(run_concurrent, 'debug', None)
    if not debug:
        logging.basicConfig(level=task['log_level'], stream=log_stream, format=LOGGING_FORMAT)

    action, argument, kwargs = task['action'], task['argument'], task['kwargs']
    try:
        logging.debug('Do {}.{} with {}'.format(action.__module__, action.__name__, argument))
        result = action(argument, **kwargs)
        logging.debug('Result: {}'.format(result))

    except KeyboardInterrupt:
        # This is a Python bug. When waiting for a condition in threading.Condition.wait(),
        # KeyboardInterrupt is never sent.
        # For some reasons, only exceptions inherited from the base Exception class are
        # handled normally.
        raise KeyboardInterruptError

    except Exception as exception:
        result = exception
        logging.debug('Exception: {}'.format(traceback.format_exc()))
        if debug == 'raise':
            raise

    return {'result': result, 'logs': log_stream.lines()}

	
def _concurent_setup():
	if not getattr(run_concurrent, 'debug', None):
		sys.stdout = open(os.devnull, 'w')
		sys.stderr = open(os.devnull, 'w')
	

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
        with multiprocessing.Pool(thread_count, initializer=_concurent_setup) as pool:
            for result in pool.map(_concurrent_main, (wrap_task(t) for t in tasks)):
                save_result(**result)
    else:
        for task in tasks:
            save_result(**_concurrent_main(wrap_task(task)))

    return results


def test_concurrent(action: Callable, argument: Any, thread_count: int):
    results = [run_concurrent(action, [argument] * thread_count, thread_count)]
    assert [repr(r) for r in results if isinstance(r, Exception)] == []


class Size:
    step = 1024
    suffixes = ('', 'K', 'M', 'G', 'T')

    def __init__(self, value: Union[int, str]):
        if isinstance(value, int):
            self.bytes = value
        elif isinstance(value, str):
            self.bytes = self.str_to_int(value)
        else:
            raise TypeError('Unexpected type: ' + type(value).__name__)

    def __eq__(self, other):
        return self.bytes == other.bytes

    def __lt__(self, other):
        return self.bytes < other.bytes

    def __str__(self):
        return self.int_to_str(self.bytes)

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, repr(str(self)))

    @classmethod
    def str_to_int(cls, value):
        value = value.upper()
        for i, suffix in enumerate(cls.suffixes, 0):
            if suffix and value.endswith(suffix):
                return int(float(value[:-len(suffix)]) * (cls.step ** i))
        return int(value)

    @classmethod
    def int_to_str(cls, value):
        exponent = 0
        while value >= cls.step and exponent < len(cls.suffixes) - 1:
            value /= cls.step
            exponent += 1
        return '{:g}{}'.format(value, cls.suffixes[exponent])


# TODO: Consider to reimplement by pathlib.
class File:
    def __init__(self, *path):
        self.path = os.path.join(*path)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.path))

    def directory(self):
        return Directory(os.path.dirname(self.path))

    def remove(self):
        if os.path.isfile(self.path):
            os.remove(self.path)

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
        self.write(lambda f: json.dump(data, f, indent=4))

    def read_json(self, default=None):
        return self.read(lambda f: json.load(f), default)

    def write_yaml(self, data):
        self.write(lambda f: yaml.dump(data, f, default_flow_style=False))

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

    def file(self, name: str) -> File:
        return File(self.path, name)

    def files(self, mask: str = '*') -> List[File]:
        return [File(f) for f in glob(os.path.join(self.path, mask))]

    def directory(self, *path) -> 'Directory':
        return Directory(self.path, *path)

    def directories(self, mask: str = '*') -> List['Directory']:
        return [Directory(d) for d in glob(os.path.join(self.path, mask))]

    def make(self):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

    def size(self) -> Size:
        return Size(os.stat(self.path).st_size)

    def remove(self):
        shutil.rmtree(self.path)


class TemporaryDirectory(Directory):
    def __init__(self):
        super().__init__('./_tmp_directory_' + '{0:0>5}'.format(random.randint(0, 99999)))

    def __enter__(self):
        logging.info('+++ New temporary directory: ' + self.path)
        self.make()
        return self

    def __exit__(self, *args):
        logging.info('--- Remove temporary directory: ' + self.path)
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
