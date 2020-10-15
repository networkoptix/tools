import datetime

from pathlib import Path
from typing import List

import json
import yaml

import git


class Error(Exception):
    pass


class RepoAccessor:
    def __init__(self, path: Path, url: str):
        try:
            self.repo = git.Repo(path)
        except git.exc.NoSuchPathError as e:
            self.repo = git.Repo.clone_from(url, path)

    def update_repository(self):
        self.repo.remotes.origin.fetch()

    def grep_recent_commits(self, substring: str, branch: str) -> List:
        return list(self.repo.iter_commits(f"origin/{branch}", grep=substring, since='18 month ago'))


def parse_config_file(filepath: Path):
    if filepath.suffix == '.json':
        def parse_file(f): return json.load(f)
    if filepath.suffix == '.yaml':
        def parse_file(f): return yaml.safe_load(f)
    else:
        raise NotImplementedError(f'Unsupported file extension: {filepath}')

    with open(filepath, 'r') as f:
        return parse_file(f)


class cached():
    def __init__(self, invalidation_period: datetime.timedelta = None):
        self._invalidation_period = invalidation_period

        self._last_update = None
        self._value = None

    def __call__(self, value_generator):
        def wrapped(*args):
            if self._is_value_valid():
                return self._value

            self._value = value_generator(*args)
            self._last_update = datetime.datetime.now()
            return self._value
        return wrapped

    def _is_value_valid(self):
        if self._last_update is None:
            return False
        if self._invalidation_period is None:
            return True

        return datetime.datetime.now() - self._last_update < self._invalidation_period
