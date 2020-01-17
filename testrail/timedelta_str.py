import datetime
import re


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
    """Create datetime from it's string representation
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
    """
    for pattern in TIMEDELTA_REGEXP_LIST:
        try:
            match = pattern.match(duration_str)
        except TypeError:
            raise InvalidTimeDeltaString('Invalid timedelta: %r' % duration_str)
        if match:
            break
    else:
        raise InvalidTimeDeltaString('Invalid timedelta: %r' % duration_str)
    timedelta_params = {k: float(v)
                        for (k, v) in match.groupdict().items() if v}
    try:
        return datetime.timedelta(**timedelta_params)
    except ValueError:
        raise InvalidTimeDeltaString('Invalid timedelta: %r' % duration_str)


def timedelta_to_str(d):
    """Create human-readable string from timedelta, inverse for str_time_delta
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
    """
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
        s += ('%.3f' % (sec + d.microseconds / 1000. / 1000)).rstrip('0') + 's'
    elif sec:
        s += '%ds' % sec
    elif not s:
        ms, usec = divmod(d.microseconds, 1000)
        if ms and usec:
            s += ('%f' % (d.microseconds / 1000.)).rstrip('0') + 'ms'
        elif usec:
            s += '%dusec' % d.microseconds
        elif ms:
            s += '%dms' % ms
    if not s:
        s = '0'
    return s
