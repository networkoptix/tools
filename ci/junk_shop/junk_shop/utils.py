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


class DbConfig(object):

    @classmethod
    def from_string(cls, value):
        mo = re.match(r'([^:]+):([^@]+)@(.+)', value)
        if not mo or len(mo.groups()) != 3:
            raise ArgumentTypeError('Expected postgres database credentials in form "user:password@host", but got: %r' % value)
        user, password, host = mo.groups()
        return cls(host, user, password)

    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
