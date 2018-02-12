import logging
import datetime
import re
import os.path
import os
import sys
import shutil

from pyvalid.validators import Validator
import requests

log = logging.getLogger(__name__)


class SimpleNamespace:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def setup_logging(level=None):
    #format = '%(asctime)-15s %(name)-10s %(levelname)-7s %(message)s'
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=level or logging.INFO, format=format)


class NxValidator(Validator):

    @property
    def __name__(self):
        return repr(self)

    @staticmethod
    def _is_instance_of(value, t):
        if isinstance(t, Validator):
            return t(value)
        else:
            return isinstance(value, t)


class list_inst(NxValidator):

    def __init__(self, value_type):
        self._value_type = value_type

    def __repr__(self):
        return 'list(%s)' % self._value_type.__name__

    def __call__(self, value):
        if type(value) is not list:
            return False
        for v in value:
            if not self._is_instance_of(v, self._value_type):
                return False
        return True


def is_list_inst(value, value_type):
    return list_inst(value_type)(value)


class dict_inst(NxValidator):

    def __init__(self, key_type, value_type):
        self._key_type = key_type
        self._value_type = value_type

    def __repr__(self):
        return 'dict(%s -> %s)' % (self._key_type.__name__, self._value_type.__name__)

    def __call__(self, value):
        if type(value) is not dict:
            return False
        for key, value in value.items():
            if not self._is_instance_of(key, self._key_type):
                return False
            if not self._is_instance_of(value, self._value_type):
                return False
        return True


def is_dict_inst(value, key_type, value_type):
    return dict_inst(key_type, value_type)(value)


def quote(s, char='"'):
    return '%c%s%c' % (char, s, char)

def prepend_env_element(env, name, value):
    old_value = env.get(name)
    if old_value:
        old_list = old_value.split(os.pathsep)
    else:
        old_list = []
    env = env.copy()
    env[name] = os.pathsep.join([value] + old_list)
    return env

def save_url_to_file(source_url, dest_path):
    has_sni = sys.version_info[:3] >= (2, 7, 9)  # no SNI for older python, "hostname doesn't match" if verify=True
    log.info('Downloading %s to %s', source_url, dest_path)
    response = requests.get(source_url, stream=True, verify=has_sni)
    dest_dir = os.path.dirname(dest_path)
    ensure_dir_exists(dest_dir)
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=None):
            f.write(chunk)

def ensure_dir_exists(path):
    if not os.path.isdir(path):
        log.info('Creating directory: %s', path)
        os.makedirs(path)

def ensure_dir_missing(path):
    if os.path.isdir(path):
        log.info('Removing directory: %s', path)
        shutil.rmtree(path)

def prepare_empty_dir(path):
    ensure_dir_missing(path)
    ensure_dir_exists(path)


TIMEDELTA_REGEXP = re.compile(r'^((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?$')

def str_to_timedelta(duration_str):
    '''Create datetime from it's string representation
    >>> str_to_timedelta('1d2h3m4s')
    datetime.timedelta(1, 7384)
    >>> str_to_timedelta('61')
    datetime.timedelta(0, 61)
    '''
    match = TIMEDELTA_REGEXP.match(duration_str)
    try:
        if not match: return datetime.timedelta(seconds=int(duration_str))
        timedelta_params = {k: int(v)
                            for (k, v) in match.groupdict().iteritems() if v}
        if not timedelta_params:
            return datetime.timedelta(seconds=int(duration_str))
        return datetime.timedelta(**timedelta_params)
    except ValueError:
        assert False, 'Invalid timedelta: %r' % duration_str


def timedelta_to_str(d):
    '''Create human-readable string from timedelta, inverse for str_time_delta
    >>> timedelta_to_str(str_to_timedelta('1d2h3m4s'))
    '1d2h3m4s'
    >>> timedelta_to_str(str_to_timedelta('62'))
    '1m2s'
    '''
    rem, sec = divmod(d.seconds, 60)
    hour, min = divmod(rem, 60)
    s = ''
    if d.days:
        s += '%dd' % d.days
    if hour:
        s += '%dh' % hour
    if min:
        s += '%dm' % min
    if sec or not s:
        s += '%ds' % sec
    return s
