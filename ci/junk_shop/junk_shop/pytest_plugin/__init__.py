import os
import pytest

from ..db_config import DbConfig
from ..capture_repository import DbCaptureRepository
from ..utils import compose
from ..config import Config
from ..parameters import (
    build_parameters_from_value_list,
    run_parameters_from_value_list,
    enum_db_arguments,
    )
from .plugin import DbCapturePlugin


JUNK_SHOP_PLUGIN_NAME = 'junk-shop-db-capture'


def pytest_addoption(parser):
    for args, kw in enum_db_arguments():
        parser.addoption(*args, **kw)
    parser.addoption('--run-name', help='Run name (by default is root test name)')
    parser.addoption('--run-id-file', help='Store root run id into this file')

def pytest_configure(config):
    file_config = Config.merge(config.getoption('--config'))
    db_config = (
        file_config.get_pytest_option(config, '--junk-shop-db', DbConfig.from_dict)
        or DbConfig.from_string(os.environ.get('JUNK_SHOP_CAPTURE_DB'))
        )
    build_parameters = dict(
        file_config.get_pytest_option(
            config, '--build-parameters', compose(list, build_parameters_from_value_list)))
    run_name = file_config.get_pytest_option(config, '--run-name')
    run_parameters = dict(
        file_config.get_pytest_option(
            config, '--run-parameters', compose(list, run_parameters_from_value_list)))
    run_id_file = file_config.get_pytest_option(config, '--run-id-file')
    if db_config:
        repository = DbCaptureRepository(db_config, build_parameters, run_parameters)
        config.pluginmanager.register(DbCapturePlugin(config, repository, run_id_file, run_name), JUNK_SHOP_PLUGIN_NAME)
