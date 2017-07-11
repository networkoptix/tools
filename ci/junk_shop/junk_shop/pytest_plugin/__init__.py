import pytest
from ..utils import DbConfig
from ..capture_repository import BuildParameters, RunParameters
from .plugin import DbCapturePlugin


JUNK_SHOP_PLUGIN_NAME = 'junk-shop-db-capture'


def pytest_addoption(parser):
    parser.addoption('--capture-db', type=DbConfig.from_string, metavar='user:password@host',
                     help='Capture postgres database credentials')
    parser.addoption('--build-parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                     help='Build parameters')
    parser.addoption('--run-parameters', type=RunParameters.from_string, metavar=RunParameters.example,
                     help='Run parameters')

def pytest_configure(config):
    db_config = config.getoption('--capture-db')
    build_parameters = config.getoption('--build-parameters')
    run_parameters = config.getoption('--run-parameters')
    if config.getvalue('capturelog') and db_config:
        raise pytest.UsageError('--capture-db and capturelog plugin are mutually exclusive; add --nocapturelog option')
    if db_config:
        config.pluginmanager.register(DbCapturePlugin(config, db_config, build_parameters, run_parameters), JUNK_SHOP_PLUGIN_NAME)
