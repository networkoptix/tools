import pytest
from ..utils import DbConfig
from ..capture_repository import BuildParameters, RunParameters, DbCaptureRepository
from .plugin import DbCapturePlugin


JUNK_SHOP_PLUGIN_NAME = 'junk-shop-db-capture'


def pytest_addoption(parser):
    parser.addoption('--capture-db', type=DbConfig.from_string, metavar='user:password@host',
                     help='Capture postgres database credentials')
    parser.addoption('--project', help='Junk-shop project name')
    parser.addoption('--build-parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                     help='Build parameters')
    parser.addoption('--run-parameters', type=RunParameters.from_string, metavar=RunParameters.example,
                     help='Run parameters')
    parser.addoption('--run-id-file', help='Store root run id into this file')

def pytest_configure(config):
    db_config = config.getoption('--capture-db')
    project = config.getoption('--project')
    build_parameters = config.getoption('--build-parameters')
    run_parameters = config.getoption('--run-parameters')
    run_id_file = config.getoption('--run-id-file')
    if config.getvalue('capturelog') and db_config:
        raise pytest.UsageError('--capture-db and capturelog plugin are mutually exclusive; add --nocapturelog option')
    if db_config:
        repository = DbCaptureRepository(db_config, project, build_parameters, run_parameters)
        config.pluginmanager.register(DbCapturePlugin(config, repository, run_id_file), JUNK_SHOP_PLUGIN_NAME)
