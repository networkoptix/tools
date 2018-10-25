from argparse import ArgumentTypeError
import os
import re

from pony.orm import sql_debug


class DbConfig(object):

    @classmethod
    def from_string(cls, value):
        if value is None:
            return None
        mo = re.match(r'^([^:]+):([^@]+)@([^:]+)(:(\d+))?$', value)
        if not mo:
            raise ArgumentTypeError('Expected postgres database credentials in form "user:password@host[:port]", but got: %r' % value)
        user, password, host, _, port = mo.groups()
        return cls(host, user, password, port)

    @classmethod
    def from_dict(cls, d):
        return cls(
            host=d['host'],
            user=d['user'],
            password=d['password'],
            )

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
