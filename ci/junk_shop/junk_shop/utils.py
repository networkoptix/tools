import os
import re
import pytz
from dateutil.tz import tzlocal
import datetime
from argparse import ArgumentTypeError

from pony.orm import sql_debug


class SimpleNamespace:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def datetime_utc_now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

def datetime_local_now():
    return datetime.datetime.now(tzlocal())

def as_local_tz(dt):
    return dt.astimezone(tzlocal())


TIMEDELTA_REGEXP = re.compile(
    r'^'
    r'((?P<days>\d+?)d)?'
    r'((?P<hours>\d+?)h)?'
    r'((?P<minutes>\d+?)m)?'
    r'((?P<seconds>[\d.]+)s)?'
    r'((?P<milliseconds>[\d.]+?)ms)?'
    r'((?P<microseconds>\d+?)usec)?'
    r'$')

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
    '''
    match = TIMEDELTA_REGEXP.match(duration_str)
    if not match: return datetime.timedelta(seconds=int(duration_str))
    timedelta_params = {k: float(v)
                        for (k, v) in match.groupdict().iteritems() if v}
    try:
        if not timedelta_params:
            return datetime.timedelta(seconds=int(duration_str))
        return datetime.timedelta(**timedelta_params)
    except ValueError:
        assert False, 'Invalid timedelta: %r' % duration_str


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


class DbConfig(object):

    @classmethod
    def from_string(cls, value):
        mo = re.match(r'^([^:]+):([^@]+)@([^:]+)(:(\d+))?$', value)
        if not mo:
            raise ArgumentTypeError('Expected postgres database credentials in form "user:password@host[:port]", but got: %r' % value)
        user, password, host, _, port = mo.groups()
        return cls(host, user, password, port)

    def __init__(self, host, user, password, port=None):
        self.host = host
        self.user = user
        self.password = password
        self.port = port

    def __repr__(self):
        if self.port:
            return '%s:%s' % (self.host, self.port)
        else:
            return self.host

    def bind(self, db):
        if 'SQL_DEBUG' in os.environ:
            sql_debug(True)
        db.bind('postgres', host=self.host, user=self.user,
                    password=self.password, port=self.port)
        db.generate_mapping(create_tables=True)
