import yaml

from pathlib2 import Path

from ..utils import timedelta_to_str, str_to_timedelta


RUN_INFO_FILE_NAME = 'run_info.yaml'


class InfoBase(object):

    @classmethod
    def load_from_file(cls, path):
        with path.open() as f:
            return cls.from_dict(yaml.load(f))

    def save_to_file(self, path):
        with path.open('w') as f:
            yaml.dump(self.as_dict(), f)


class TestInfo(InfoBase):

    @classmethod
    def from_dict(cls, data):
        return cls(
            binary_path=Path(data['binary_path']),
            command_line=data['command_line'],
            errors=data['errors'],
            started_at=data['started_at'],
            duration=str_to_timedelta(data['duration']),
            exit_code=data['exit_code'],
            timed_out=data['timed_out'],
            pid=data['pid']
            )

    def __init__(self, binary_path, command_line=None, errors=None,
                 started_at=None, duration=None, exit_code=None,
                 timed_out=False, pid = None):
        self.binary_path = binary_path
        self.command_line = command_line
        self.errors = errors or []
        self.started_at = started_at  # datetime
        self.duration = duration  # timedelta
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.pid = pid

    def as_dict(self):
        return dict(
            binary_path=str(self.binary_path),
            command_line=self.command_line,
            errors=self.errors,
            started_at=self.started_at,
            duration=timedelta_to_str(self.duration),
            exit_code=self.exit_code,
            timed_out=self.timed_out,
            pid=self.pid
            )


class RunInfo(InfoBase):

    @classmethod
    def load_from_dir(cls, path):
        return cls.load_from_file(path / RUN_INFO_FILE_NAME)

    @classmethod
    def from_dict(cls, data):
        return cls(
            test_list=data['test_list'],
            errors=data['errors'],
            started_at=data['started_at'],
            duration=str_to_timedelta(data['duration']),
            )

    def __init__(self, test_list, errors=None, started_at=None, duration=None):
        self.test_list = test_list
        self.errors = errors or []
        self.started_at = started_at  # datetime
        self.duration = duration  # timedelta

    def as_dict(self):
        return dict(
            test_list=self.test_list,
            errors=self.errors,
            started_at=self.started_at,
            duration=timedelta_to_str(self.duration),
            )

    def save_to_dir(self, path):
        return self.save_to_file(path / RUN_INFO_FILE_NAME)
