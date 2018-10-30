# Yaml configuration file.
# Adds ability to store all or some options in yaml file instead of passing them via command-line.

import os.path
import collections

import yaml


class Config(object):

    @classmethod
    def create_empty(cls):
        return cls()

    @classmethod
    def from_yaml_file(cls, path):
        with open(os.path.expanduser(path)) as f:
            return cls(yaml.load(f))

    @classmethod
    def merge(cls, config_list):  # type: List[Config] -> Config
        def merge_dict(x, y):
            result = dict(x)
            for key, value in y.items():
                if isinstance(value, collections.Mapping):
                    result[key] = merge_dict(x.get(key, {}), value)
                else:
                    result[key] = value
            return result
        dict_data = reduce(merge_dict, [config._config for config in config_list or []], {})
        return cls(dict_data)
        
    def __init__(self, dict_data=None):
        self._config = dict_data or {}

    def get_pytest_option(self, pytest_config, option_name, constructor=None):
        option = pytest_config.getoption(option_name)
        if option is not None:
            return option
        else:
            name = self._option_to_name(option_name)
            return self._get_option(name, constructor)

    def get_args_option(self, args, name, constructor=None):
        option = getattr(args, name)
        if option is not None:
            return option
        else:
            return self._get_option(name, constructor)

    def _get_option(self, name, constructor):
        option = self._config.get(name)
        if option is not None and constructor:
            return constructor(option)
        else:
            return option

    @staticmethod
    def _option_to_name(name):
        assert name.startswith('--')
        return name[2:].replace('-', '_')
