import re
import pytz
import tzlocal
from datetime import datetime
from argparse import ArgumentTypeError


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
    return datetime.utcnow().replace(tzinfo=pytz.utc)

def as_local_tz(dt):
    tz = tzlocal.get_localzone()
    return dt.astimezone(tz)

def status2outcome(passed):
    if passed:
        return 'passed'
    else:
        return 'failed'

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

    def __init__(self, host, user, password, port):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
