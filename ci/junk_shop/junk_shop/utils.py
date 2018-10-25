import re
import pytz
import argparse
from dateutil.tz import tzlocal
import datetime
from argparse import ArgumentTypeError
from pathlib2 import Path


class SimpleNamespace:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def compose(fn1, fn2):
    def inner(*args, **kw):
        return fn1(fn2(*args, **kw))
    return inner


def datetime_utc_now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def datetime_local_now():
    return datetime.datetime.now(tzlocal())


def as_local_tz(dt):
    return dt.astimezone(tzlocal())


TIMEDELTA_REGEXP_LIST = [
    re.compile(
        r'^'
        r'((?P<days>\d+?)d)?'
        r'((?P<hours>\d+?)h)?'
        r'((?P<minutes>\d+?)m)?'
        r'((?P<seconds>[\d.]+)s)?'
        r'((?P<milliseconds>[\d.]+?)ms)?'
        r'((?P<microseconds>\d+?)usec)?'
        r'$'),
    # 100 days, 0:03:20.000300
    re.compile(
        r'^'
        r'(?P<days>\d+) days?, '
        r'(?P<hours>\d+):'
        r'(?P<minutes>\d+):'
        r'(?P<seconds>\d+)\.'
        r'(?P<microseconds>\d{6})'
        r'$'),
    # 100 days, 0:03:20.030
    re.compile(
        r'^'
        r'(?P<days>\d+) days?, '
        r'(?P<hours>\d+):'
        r'(?P<minutes>\d+):'
        r'(?P<seconds>\d+)'
        r'(\.(?P<milliseconds>\d{3}))?'
        r'$'),
    # just seconds
    re.compile(
        r'^'
        r'(?P<seconds>\d+)'
        r'$'),
    ]


class InvalidTimeDeltaString(RuntimeError):
    pass


def str_to_timedelta(duration_str):
    '''Create datetime from it's string representation
    >>> str_to_timedelta('1d2h3m4s')
    datetime.timedelta(1, 7384)
    >>> str_to_timedelta('61')
    datetime.timedelta(0, 61)
    >>> str_to_timedelta('4.056s')
    datetime.timedelta(0, 4, 56000)
    >>> str_to_timedelta('6.453ms')
    datetime.timedelta(0, 0, 6453)
    >>> str_to_timedelta('1 day, 0:00:02.000003')
    datetime.timedelta(1, 2, 3)
    >>> str_to_timedelta('100 days, 0:03:20.000300')
    datetime.timedelta(100, 200, 300)
    >>> str_to_timedelta('100 days, 0:03:20.003')
    datetime.timedelta(100, 200, 3000)
    >>> str_to_timedelta('10 days, 0:00:20')
    datetime.timedelta(10, 20)
    '''
    for pattern in TIMEDELTA_REGEXP_LIST:
        match = pattern.match(duration_str)
        if match:
            break
    else:
        raise InvalidTimeDeltaString('Invalid timedelta: %r' % duration_str)
    timedelta_params = {k: float(v)
                        for (k, v) in match.groupdict().iteritems() if v}
    try:
        return datetime.timedelta(**timedelta_params)
    except ValueError:
        raise InvalidTimeDeltaString('Invalid timedelta: %r' % duration_str)


def timedelta_to_str(d):
    '''Create human-readable string from timedelta, inverse for str_time_delta
    >>> timedelta_to_str(str_to_timedelta('1d2h3m4s'))
    '1d2h3m4s'
    >>> timedelta_to_str(str_to_timedelta('4s325ms'))
    '4.325s'
    >>> timedelta_to_str(str_to_timedelta('3m4s325ms'))
    '3m4s'
    >>> timedelta_to_str(str_to_timedelta('4s56189usec'))
    '4.056s'
    >>> timedelta_to_str(str_to_timedelta('4.056s'))
    '4.056s'
    >>> timedelta_to_str(str_to_timedelta('6453usec'))
    '6.453ms'
    >>> timedelta_to_str(str_to_timedelta('53usec'))
    '53usec'
    >>> timedelta_to_str(str_to_timedelta('62'))
    '1m2s'
    >>> timedelta_to_str(str_to_timedelta('0'))
    '0'
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
    if sec and d.microseconds and not s:
        s += ('%.3f' % (sec + d.microseconds/1000./1000)).rstrip('0') + 's'
    elif sec:
        s += '%ds' % sec
    elif not s:
        ms, usec = divmod(d.microseconds, 1000)
        if ms and usec:
            s += ('%f' % (d.microseconds/1000.)).rstrip('0') + 'ms'
        elif usec:
            s += '%dusec' % d.microseconds
        elif ms:
            s += '%dms' % ms
    if not s:
        s = '0'
    return s


def dir_path(value):
    path = Path(value).expanduser()
    if not path.is_dir():
        raise argparse.ArgumentTypeError('%s is not an existing directory' % path)
    return path


def file_path(value):
    path = Path(value).expanduser()
    if not path.is_file():
        raise argparse.ArgumentTypeError('%s is not an existing file' % path)
    return path


def status2outcome(passed):
    if passed:
        return 'passed'
    else:
        return 'failed'


def outcome2status(outcome):
    assert outcome in ['failed', 'passed'], repr(outcome)
    return outcome == 'passed'


def param_to_bool(value):
    if value in ['true', 'yes']:
        return True
    if value in ['false', 'no']:
        return False
    assert False, "Invalid bool value: %r; Expected one of 'true', 'false', 'yes', 'no'" % value

def bool_to_param(value):
    if value:
        return 'true'
    else:
        return 'false'
