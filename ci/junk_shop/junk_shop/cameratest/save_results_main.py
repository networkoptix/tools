#!/usr/bin/env python
'''
cameratest.save_results_main
~~~~~~~~~~~~~~~~~~~~~~

It's a script to store camera test results into Junkshop DB.

Sample:
  ./save_results_main.py user:password@junkshop_db_host project=ci,branch=vms,build_num=2739 test_results.yaml

  user:password@junkshop_db_host - Junkshop database credentials
  project=ci,branch=vms,build_num=2739 - build parameters, only project, branch and build_num are required

  `test_results.yaml` is an artifact of `nx_vms/func_tests/cameras_integration/test_server.py`:
    ```
        cd nx_vms/func_tests
        pytest [other options] cameras_integration/test_server.py::test_cameras
    ```

  You can use optional `test-name` only if you need to use non-default name for the tests in Junkshop DB.
'''

import logging
import argparse
import yaml
from pathlib2 import Path
from pony.orm import db_session
from datetime import datetime, timedelta

from junk_shop.utils import DbConfig, status2outcome, file_path
from junk_shop.capture_repository import BuildParameters, DbCaptureRepository
import junk_shop.models as models


log = logging.getLogger(__name__)


DEFAULT_UNIT_TEST_NAME = 'cameratest'
ERRORS_ARTIFACT_NAME = 'errors'
MESSAGES_ARTIFACT_NAME = 'messages'
ZERO_DURATION = timedelta(seconds=0)


def condition_to_passed(condition):
    return condition == 'success'


def str_to_timedelta(duration):
    if not duration:
        return ZERO_DURATION
    t = datetime.strptime(duration, "%H:%M:%S.%f")
    return timedelta(
        hours=t.hour,
        minutes=t.minute,
        seconds=t.second,
        microseconds=t.microsecond)


def string_list_from_field(data, field_name):
    errors = data.get(field_name, [])
    if isinstance(errors, list):
        return errors
    return [str(errors)]


class StageInfo(object):

    @classmethod
    def from_dict(cls, data):
        errors = string_list_from_field(data, 'errors')
        if data['condition'] == 'halt':
            errors.append('Stage is aborted')
        return cls(
            name=data['_'],
            duration=str_to_timedelta(data.get('duration')),
            passed=condition_to_passed(data['condition']),
            errors=errors,
            messages=string_list_from_field(data, 'message')
        )

    def __init__(self, name, duration, passed, errors, messages):
        self.name = name
        self.duration = duration
        self.passed = passed
        self.errors = errors
        self.messages = messages


class CameraTestStorage(object):

    @classmethod
    def from_dict(cls, camera_id, data):
        return cls(
            camera_id=camera_id,
            duration=str_to_timedelta(data.get('duration')),
            passed=condition_to_passed(data['condition']),
            stages=map(StageInfo.from_dict, data['stages'])
        )

    def __init__(self, camera_id, duration, passed, stages):
        self.camera_id = camera_id
        self.duration = duration
        self.passed = passed
        self.stages = stages


@db_session
def make_root_run(repository, root_name):
    root_run = repository.produce_test_run(root_run=None, test_path_list=[root_name])
    return root_run


@db_session
def save_camera_root_run(repository, parent_run, test_path_list, duration, passed):
    run = repository.produce_test_run(
        parent_run, test_path_list, is_test=False)
    run.duration = duration
    run.outcome = status2outcome(passed)
    return run


def produce_camera_tests(repository, root_run, parent_path_list, camera_tests):
    test_path_list = parent_path_list + [camera_tests.camera_id]
    camera_run = save_camera_root_run(
        repository, root_run, test_path_list,
        camera_tests.duration, camera_tests.passed)
    for stage in camera_tests.stages:
        with db_session:
            stage_run = repository.produce_test_run(
                camera_run, test_path_list + [stage.name], is_test=True)
            stage_run.duration = stage.duration
            stage_run.outcome = status2outcome(stage.passed)
            repository.add_artifact(
                stage_run,
                ERRORS_ARTIFACT_NAME,
                '%s-%s' % (stage_run.name, ERRORS_ARTIFACT_NAME),
                repository.artifact_type.output,
                '\n'.join(stage.errors),
                is_error=True)
            repository.add_artifact(
                stage_run,
                MESSAGES_ARTIFACT_NAME,
                '%s-%s' % (stage_run.name, MESSAGES_ARTIFACT_NAME),
                repository.artifact_type.output,
                '\n'.join(stage.messages))


def parse_and_save_results_to_db(results_file_path, repository, root_name):
    passed = True
    total_duration = ZERO_DURATION
    root_run = make_root_run(repository, root_name)

    with results_file_path.open() as f:
        camera_tests_list = [
            CameraTestStorage.from_dict(camera_id, camera_results)
            for camera_id, camera_results in yaml.load(f).items()]
        for camera_tests in camera_tests_list:
            produce_camera_tests(
                repository, root_run, [root_name], camera_tests)
            passed = passed and camera_tests.passed
            total_duration += camera_tests.duration
    with db_session:
        root_run = models.Run[root_run.id]
        root_run.outcome = status2outcome(passed)
        root_run.duration = total_duration


def main():
    parser = argparse.ArgumentParser(
        usage='%(prog)s [options]')
    parser.add_argument(
        'db_config',
        type=DbConfig.from_string,
        metavar='user:password@host',
        help='Capture postgres database credentials')
    parser.add_argument(
        'build_parameters',
        type=BuildParameters.from_string,
        metavar=BuildParameters.example,
        help='Build parameters')
    parser.add_argument(
        'results_file_path',
        type=file_path,
        help='Test results file path')
    parser.add_argument(
        '--test-name',
        default=DEFAULT_UNIT_TEST_NAME,
        help='Name of test, default=%(default)r')

    args = parser.parse_args()

    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=logging.INFO, format=format)
    repository = DbCaptureRepository(args.db_config, args.build_parameters)

    parse_and_save_results_to_db(
        args.results_file_path,
        repository,
        args.test_name)


if __name__ == "__main__":
    main()
