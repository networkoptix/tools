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

LOGGING_FORMAT = '%(asctime)s %(levelname)-8s %(name)s:%(lineno)d: %(message)s'


class Error(Exception):
    pass


class KeyboardInterruptError(Error):
    pass


def stream_log_handler(name: str = 'stdout'):
    supported = dict(stdout=sys.stdout, stderr=sys.stderr)
    return logging.StreamHandler(supported[name])


def rotating_log_handler(base_name: str, max_size: int = 1, backup_count: str = 1):
    File(base_name).directory().make()
    return logging.handlers.RotatingFileHandler(
        base_name, 'a', Size(max_size).bytes, backup_count)


def graylog_log_handler(service_name: str, host: str, port: int):
    import graypy

    class ServiceNameFilter(logging.Filter):
        @staticmethod
        def filter(record):
            record.service_name = service_name
            return True
    handler = graypy.GELFTCPHandler(host, port, level_names=True)
    handler.setFormatter(logging.Formatter())
    if service_name:
        handler.addFilter(ServiceNameFilter())
    return handler


def cloud_watch_log_handler(**kwargs):
    import watchtower
    return watchtower.CloudWatchLogHandler(**kwargs)


def setup_logging(level: str = 'debug', title: str = '', botocore_level='warning', service_name: str = None,
                  stream: dict = {}, graylog: dict = {}, rotating_file: dict = {}, cloud_watch: dict = {}):
    """Sets up application log :level and :path.
    """
    details = ['level: {}'.format(level)]

    def create_handler(handler_maker, level=None, **args):
        handler = handler_maker(**args)
        # container.append(handler)
        args['level'] = level
        details.append('{}: {}'.format(
            handler_maker.__name__,
            ', '.join('{}="{}"'.format(*i) for i in args.items())))
        if level:
            handler.setLevel(getattr(logging, level.upper()))
        return handler

    main_handlers = []
    extra_handlers = []
    if stream:
        main_handlers.append(create_handler(stream_log_handler, **stream))
    if rotating_file:
        main_handlers.append(create_handler(rotating_log_handler, **rotating_file))
    if graylog:
        main_handlers.append(create_handler(graylog_log_handler, service_name=service_name, **graylog))
    if cloud_watch:
        extra_handlers.append(create_handler(cloud_watch_log_handler, **cloud_watch))

    logging.basicConfig(
        level=getattr(logging, level.upper(), None) or int(level),
        format=LOGGING_FORMAT, handlers=(main_handlers + extra_handlers))

    # Avoid infinit recursion: botocore -> logger -> CloudWatchLogHandler -> botocore
    botocore_logger = logging.getLogger('botocore')
    botocore_logger.handlers = main_handlers
    botocore_logger.propagate = False
    botocore_logger.setLevel(
        getattr(logging, botocore_level.upper(), None) or int(botocore_level))

    logging.info('=' * 80)
    if title:
        print(title)
        logging.info(title)
    for detail in details:
        logging.info(detail)


def is_ascii_printable(s: str):
    try:
        s.encode('ascii')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return False
    else:
        return all(c in string.printable for c in s)


def format_error(error: Exception, include_stack: bool = False):
    cls = type(error)
    exception = '{}.{}: {}'.format(cls.__module__, cls.__name__, str(error))
    if include_stack:
        stack = '\n'.join(traceback.format_exc().splitlines()[:-1])
        return 'Exception: {}\n{}'.format(stack, exception)
    else:
        return exception


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


def mixed_merge(list_of_lists: List[List[Any]], limit: int = None):
    result = []
    while list_of_lists and len(result) != limit:
        current_list = list_of_lists.pop(0)
        if current_list:
            result.append(current_list.pop(0))
            list_of_lists.append(current_list)

    return result


class BufferedStream:
    def __init__(self):
        self.buffers = []

    def write(self, data):
        self.buffers.append(data)

    def lines(self):
        data = ''.join(self.buffers)
        self.buffers = []
        return data.splitlines()


def _concurrent_main(task):
    log_stream = getattr(_concurrent_main, 'log_stream', BufferedStream())
    _concurrent_main.log_stream = log_stream
    if not task['debug']:
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
        if type(exception).__name__ in task['debug']:
            import pdb
            pdb.set_trace()

        result = exception
        logging.debug(format_error(exception, include_stack=True))

    return {'result': result, 'logs': log_stream.lines()}


def _concurrent_setup():
    if not getattr(run_concurrent, 'debug', None):
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')


def run_concurrent(action: Callable, tasks: list, thread_count: int, **kwargs):
    results = []
    log_level = logger.getEffectiveLevel()

    def save_result(result, logs):
        results.append(result)
        for line in logs:
            try:
                date, time, level, message = line.split(maxsplit=3)
                if level == 'INFO':
                    level = 'DEBUG'
                resolved_level = int(getattr(logging, level))
                logger.log(resolved_level, time + '    ' + message)
            except (AttributeError, TypeError, ValueError):
                logger.log(resolved_level, line)   # < Not a beginning of the log line.

    def wrap_task(task, debug=''):
        return {'action': action, 'argument': task, 'kwargs': kwargs,
                'log_level': log_level, 'debug': debug}

    debug = getattr(run_concurrent, 'debug', None)
    if debug:
        # Single thread implementation with break on exceptions.
        for task in tasks:
            save_result(**_concurrent_main(wrap_task(task, debug=debug)))
    else:
        with multiprocessing.Pool(thread_count, initializer=_concurrent_setup) as pool:
            for result in pool.map(_concurrent_main, (wrap_task(t) for t in tasks)):
                save_result(**result)

    return results


def test_concurrent(action: Callable, argument: Any, thread_count: int):
    results = [run_concurrent(action, [argument] * thread_count, thread_count)]
    assert [repr(r) for r in results if isinstance(r, Exception)] == []


class Size:
    step = 1024
    suffixes = ('', 'K', 'M', 'G', 'T')

    def __init__(self, value: Union[int, str] = 0):
        if isinstance(value, int):
            self.bytes = value
        elif isinstance(value, str):
            self.bytes = self.str_to_int(value)
        elif isinstance(value, Size):
            self.bytes = self.bytes
        else:
            raise TypeError('Unexpected type: ' + type(value).__name__)

    def __eq__(self, other):
        return self.bytes == other.bytes

    def __lt__(self, other):
        return self.bytes < other.bytes

    def __add__(self, other):
        return Size(self.bytes + other.bytes)

    def __sub__(self, other):
        return Size(self.bytes - other.bytes)

    def __mul__(self, scalar):
        return Size(int(self.bytes * scalar))

    def __truediv__(self, scalar):
        return Size(int(self.bytes / scalar))

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

    def size(self) -> Size:
        return Size(os.path.getsize(self.path))

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
            if default is None:
                raise
            logger.warning('Read "{}" for non-existing file: {}'.format(default, self.path))
            return default
        except UnicodeDecodeError as error:
            error.reason += ' in file: {}'.format(self.path)
            raise

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
        return self.read(lambda f: yaml.safe_load(f), default)

    def serialize(self, data):
        if self.extension == 'json':
            return self.write_json(data)
        if self.extension == 'yaml':
            return self.write_yaml(data)
        raise NotImplementedError('Unsupported format "{}" file: {}'.format(
            self.extension, self.path))

    def parse(self, *args, **kwargs):
        if self.extension == 'json':
            return self.read_json(*args, **kwargs)
        if self.extension == 'yaml':
            return self.read_yaml(*args, **kwargs)
        raise NotImplementedError('Unsupported format "{}" file: {}'.format(
            self.extension, self.path))


class Directory:
    def __init__(self, *path):
        self.path = os.path.join(*path)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.path))

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    def file(self, name: str) -> File:
        return File(self.path, name)

    def files(self, mask: str = '*') -> List[File]:
        return [File(f) for f in glob(os.path.join(self.path, mask))]

    def directory(self, *path) -> 'Directory':
        return Directory(self.path, *path)

    def directories(self, mask: str = '*') -> List['Directory']:
        return [Directory(d) for d in glob(os.path.join(self.path, mask))]

    def content(self, mask: str = '*'):
        return [Directory(p) if os.path.isdir(p) else File(p)
                for p in glob(os.path.join(self.path, mask))]

    def make(self):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

    def size(self) -> Size:
        total_size = 0
        for path, _, filenames in os.walk(self.path):
            for f in filenames:
                total_size += os.path.getsize(os.path.join(path, f))
        return Size(total_size)

    def remove(self):
        shutil.rmtree(self.path)


class MultiDirectory:
    """Emulates a single directory interface for multiple directories. Useful when there is
    several directories for single type of objects.
    The first directory is considered to by primary so :path and :name are bound to it.
    """
    def __init__(self, *directories):
        self._directories = [d if isinstance(d, Directory) else Directory(d) for d in directories]
        if not self._directories:
            raise ValueError('At least 1 directory should be provided')

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, ', '.join(
            repr(d.path) for d in self._directories))

    @property
    def path(self):
        return self._directories[0].path

    @property
    def name(self):
        return self._directories[0].name

    def file(self, *args, **kwargs):
        return self._one_result('file', *args, **kwargs)

    def files(self, *args, **kwargs):
        return self._sum_result('files', [], *args, **kwargs)

    def directory(self, *args, **kwargs):
        return self._one_result('directory', *args, **kwargs)

    def directories(self, *args, **kwargs):
        return self._sum_result('directories', [], *args, **kwargs)

    def content(self, *args, **kwargs):
        return self._sum_result('content', [], *args, **kwargs)

    def make(self):
        return [d.make() for d in self._directories]

    def size(self, *args, **kwargs):
        return self._sum_result('size', Size(), *args, **kwargs)

    def remove(self):
        return [d.remove() for d in self._directories]

    def _one_result(self, method, *args, **kwargs):
        return getattr(self._directories[0], method)(*args, **kwargs)

    def _sum_result(self, method, init, *args, **kwargs):
        return sum([getattr(d, method)(*args, **kwargs) for d in self._directories], init)


class TemporaryDirectory(Directory):
    def __init__(self):
        name = 'ca_test_{0:0>5}'.format(random.randint(0, 99999))
        super().__init__(os.path.join(os.environ['TMP'], name))

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
