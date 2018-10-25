import abc
from argparse import ArgumentTypeError
from collections import namedtuple
import datetime
import os
import re

from .utils import InvalidTimeDeltaString, str_to_timedelta, bool_to_param, compose
from .config import Config
from .db_config import DbConfig
from .capture_repository import DbCaptureRepository


class ParameterType(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def from_str(self, name, value_str):
        pass

    def from_value(self, name, value):
        if isinstance(value, (str, unicode)):
            return self.from_str(name, value)
        else:
            return value


class StrParameterType(ParameterType):

    def from_str(self, name, value_str):
        return value_str


class StrChoicesParameterType(ParameterType):

    def __init__(self, allowed_values):
        self._allowed_values = allowed_values

    def from_str(self, name, value_str):
        if not value_str in self._allowed_values:
            raise ArgumentTypeError(
                'Invalid %s: %r; allowed are: %s' % (name, value_str, ', '.join(self._allowed_values)))
        return value_str


class IntParameterType(ParameterType):

    def from_str(self, name, value_str):
        if not re.match(r'^\d+$', value_str):
            raise ArgumentTypeError('Invalid int for %s: %r' % (name, value_str))
        return int(value_str)


class BoolParameterType(ParameterType):

    def from_str(self, name, value_str):
        if value_str.lower() in ['true', 'yes', 'on']:
            return True
        if value_str.lower() in ['false', 'no', 'off']:
            return False
        raise ArgumentTypeError(
            'Invalid bool for %s: %r; expected one of: true/false/yes/no/on/off' % (name, value_str))


class TimeDeltaParameterType(ParameterType):

    def from_value(self, name, value):
        if not isinstance(value, datetime.timedelta):
            return self.from_str(name, str(value))
        else:
            return value

    def from_str(self, name, value_str):
        try:
            return str_to_timedelta(value_str)
        except InvalidTimeDeltaString as x:
            raise ArgumentTypeError('Invalid timedelta format for %s: %r' % (name, value_str))


class VersionParameterType(ParameterType):

    VERSION_REGEX = r'^\d+(\.\d+)+$'

    def from_str(self, name, value_str):
        if not re.match(self.VERSION_REGEX, parameters.version):
            raise ArgumentTypeError(
                ('Invalid version format for %s: %r.'
                 ' Expected string in format: 1.2.3.4') % (name, value_str))
        return value_str


_build_parameter_types = {
    'project': StrParameterType(),
    'branch': StrParameterType(),
    'version': VersionParameterType(),
    'build_num': IntParameterType(),
    'release': StrChoicesParameterType(['release', 'beta']),
    'configuration': StrParameterType(),
    'cloud_group': StrParameterType(),
    'customization': StrParameterType(),
    'add_qt_pdb': BoolParameterType(),
    'is_incremental': BoolParameterType(),
    'jenkins_url': StrParameterType(),
    'repository_url': StrParameterType(),
    'revision': StrParameterType(),
    'duration': TimeDeltaParameterType(),
    'platform': StrParameterType(),
    }


def _build_parameters_from_string(parameters_str):
    try:
        name, value_str = parameters_str.split('=')
    except ValueError:
        raise ArgumentTypeError("Invalid option value %r; 'name=value' is expected" % parameters_str)
    t = _build_parameter_types.get(name)
    if not t:
        raise ArgumentTypeError(
            'Unknown build parameter: %r. Known are: %s'
            % (name, ', '.join(_build_parameter_types.keys())))
    return (name, t.from_str(name, value_str))


def _run_parameters_from_string(parameters_str):
    try:
        name, value = parameters_str.split('=')
    except ValueError:
        raise ArgumentTypeError("Invalid option value %r; 'name=value' is expected" % parameters_str)
    return (name, value)


def build_parameters_from_value_list(parameters_dict_list):
    for name, value in parameters_dict_list.iteritems():
        t = _build_parameter_types.get(name)
        if not t:
            raise ArgumentTypeError(
                'Unknown build parameter: %r. Known are: %s'
                % (name, ', '.join(_build_parameter_types.keys())))
        yield (name, t.from_value(name, value))

def run_parameters_from_value_list(parameters_dict_list):
    for name, value in parameters_dict_list.iteritems():
        if type(value) is bool:
            value = bool_to_param(value)
        yield (name, str(value))


def enum_db_arguments():
    yield (('--config',), dict(
        nargs='*', type=Config.from_yaml_file,
        help='Yaml configuration file path with all options and configuration'))
    yield (('--junk-shop-db',), dict(
        type=DbConfig.from_string, metavar='user:password@host',
        help='Capture postgres database credentials'))
    yield (('--build-parameters',), dict(
        nargs='*', type=_build_parameters_from_string,
        help='Build parameters, in form name=value'))
    yield (('--run-parameters',), dict(
        nargs='*', type=_run_parameters_from_string,
        help='Run parameters'))


def add_db_arguments(parser):
    for args, kw in enum_db_arguments():
        parser.add_argument(*args, **kw)


DbParameters = namedtuple('JunkShopDbParameters', 'db_config build_parameters run_parameters')


def create_db_parameters(args):
    file_config = Config.merge(args.config)
    db_config = (
        file_config.get_args_option(args, 'junk_shop_db', DbConfig.from_dict)
        or DbConfig.from_string(os.environ.get('JUNK_SHOP_CAPTURE_DB'))
        )
    build_parameters = dict(
        file_config.get_args_option(
            args, 'build_parameters', compose(list, build_parameters_from_value_list))
        or [])
    run_parameters = dict(
        file_config.get_args_option(
            args, 'run_parameters', compose(list, run_parameters_from_value_list))
        or [])
    return DbParameters(
        db_config=db_config,
        build_parameters=build_parameters,
        run_parameters=run_parameters,
        )


def create_db_repository(args):
    params = create_db_parameters(args)
    return DbCaptureRepository(params.db_config, params.build_parameters, params.run_parameters)
