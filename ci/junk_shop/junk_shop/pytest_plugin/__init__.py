import pytest
from ..utils import DbConfig
from ..capture_repository import Parameters
from .plugin import DbCapturePlugin


def pytest_addoption(parser):
    parser.addoption('--capture-db', type=DbConfig.from_string, metavar='user:password@host',
                     help='Capture postgres database credentials')
    parser.addoption('--parameters', type=Parameters.from_string, metavar=Parameters.example,
                     help='Run parameters')

def pytest_configure(config):
    db_config = config.getoption('--capture-db')
    parameters = config.getoption('--parameters')
    if config.getvalue('capturelog') and db_config:
        raise pytest.UsageError('--capture-db and capturelog plugin are mutually exclusive; add --nocapturelog option')
    if db_config:
        config.pluginmanager.register(DbCapturePlugin(config, db_config, parameters))


