import logging
import os.path
import os
import sys
import requests

log = logging.getLogger(__name__)


class SimpleNamespace:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def setup_logging(level=None):
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=level or logging.INFO, format=format)


def is_list_inst(l, cls):
    if type(l) is not list:
        return False
    for value in l:
        if not isinstance(value, cls):
            return False
    return True

def is_dict_inst(d, key_cls, value_cls):
    if type(d) is not dict:
        return False
    for key, value in d.items():
        if not isinstance(key, key_cls):
            return False
        if not isinstance(value, value_cls):
            return False
    return True


def quote(s, char='"'):
    return '%c%s%c' % (char, s, char)

def add_env_element(env, name, value):
    old_value = env.get(name)
    if old_value:
        old_list = old_value.split(os.pathsep)
    else:
        old_list = []
    env = env.copy()
    env[name] = os.pathsep.join(old_list + [value])
    return env

def save_url_to_file(source_url, dest_path):
    has_sni = sys.version_info[:3] >= (2, 7, 9)  # no SNI for older python, "hostname doesn't match" if verify=True
    log.info('Downloading %s to %s', source_url, dest_path)
    response = requests.get(source_url, stream=True, verify=has_sni)
    dest_dir = os.path.dirname(dest_path)
    ensure_dir_exists(dest_dir)
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=None):
            f.write(chunk)

def ensure_dir_exists(path):
    if not os.path.isdir(path):
        log.debug('Creating directory: %s', path)
        os.makedirs(path)
