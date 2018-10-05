#!/usr/bin/env python
'''
cameratest.save_results_main
~~~~~~~~~~~~~~~~~~~~~~

It's a script to store camera test results into Junkshop DB.

Sample:
  ./save_results_main.py user:password@junkshop_db_host project=ci,branch=vms,build_num=2739 work_dir

  user:password@junkshop_db_host - Junkshop database credentials
  project=ci,branch=vms,build_num=2739 - build parameters, only project, branch and build_num are required

  `work_dir` is a work directory of the test `nx_vms/func_tests/cameras_integration/test_server.py`:
    ```
        cd nx_vms/func_tests
        pytest [other options] --work-dir=`work_dir` cameras_integration/test_server.py::test_cameras
    ```

  You can use optional `test-name` only if you need to use non-default name for the tests in Junkshop DB.
'''

import logging
import argparse
import oyaml as yaml
import json
import sys
from pony.orm import db_session
from datetime import datetime, timedelta
from pathlib2 import Path
from junk_shop.utils import DbConfig, status2outcome, dir_path
from junk_shop.capture_repository import BuildParameters, DbCaptureRepository
import junk_shop.models as models


_logger = logging.getLogger(__name__)


DEFAULT_UNIT_TEST_NAME = 'cameratest'
MESSAGES_ARTIFACT_NAME = 'messages'
ERRORS_ARTIFACT_NAME = 'errors'
EXCEPTION_ARTIFACT_NAME = 'exceptions'
CAMERA_INFO_ARTIFACT_NAME = 'camera_info'
ZERO_DURATION = timedelta(seconds=0)
TEST_RESULTS_FILE_NAME = 'test_results.yaml'
ALL_CAMERAS_FILENAME = 'all_cameras.yaml'


def status_to_passed(status):
    return status == 'success'


def str_to_timedelta(duration):
    if not duration:
        return ZERO_DURATION
    t = datetime.strptime(duration, "%H:%M:%S.%f")
    return timedelta(
        hours=t.hour,
        minutes=t.minute,
        seconds=t.second,
        microseconds=t.microsecond)


def str_to_datetime(datetime_str):
    if not datetime_str:
        return None
    return datetime.strptime(
        datetime_str, '%Y-%m-%d %H:%M:%S.%f')


class InvalidFieldType(Exception):
    pass


def string_list_from_field(data, field_name):
    v = data.get(field_name)
    if v is None:
        return []
    elif isinstance(v, list):
        return v
    elif isinstance(v, str):
        return [v]
    raise InvalidFieldType(
        "'%s' has unexpected type %s", field_name, type(v))


def file_ext_to_artifact_type(file_ext, artifact_type_factory):
    # type: (str, ArtifactTypeFactory) -> ArtifactType
    if file_ext == '.json':
        return artifact_type_factory.json
    if file_ext == '.cap':
        return artifact_type_factory.cap
    return artifact_type_factory.output


class StageInfo(object):

    @classmethod
    def from_stage_item(cls, stage_item):
        name, data = stage_item
        errors = string_list_from_field(data, 'errors')
        if data['status'] == 'halt':
            errors.append('Stage is aborted')
        return cls(
            name=name,
            start_time=str_to_datetime(data['start_time']),
            duration=str_to_timedelta(data.get('duration')),
            passed=status_to_passed(data['status']),
            messages=string_list_from_field(data, 'message'),
            errors=errors,
            exceptions=string_list_from_field(data, 'exception')
        )

    def __init__(
            self, name, start_time, duration,
            passed, messages, errors, exceptions):
        self.name = name
        self.start_time = start_time
        self.duration = duration
        self.passed = passed
        self.errors = errors
        self.messages = messages
        self.exceptions = exceptions


class CameraTestStorage(object):

    @classmethod
    def from_camera_item(cls, camera_item):
        camera_id, data = camera_item
        return cls(
            camera_id=camera_id,
            start_time=str_to_datetime(data.get('start_time')),
            duration=str_to_timedelta(data.get('duration')),
            passed=status_to_passed(data['status']),
            messages=string_list_from_field(data, 'message'),
            errors=string_list_from_field(data, 'errors'),
            exceptions=string_list_from_field(data, 'exception'),
            stages=map(StageInfo.from_stage_item, data.get('stages', {}).items())
        )

    def __init__(
            self, camera_id, start_time, duration, passed,
            messages, errors, exceptions, stages):
        self.camera_id = camera_id
        self.duration = duration
        self.start_time = start_time
        self.passed = passed
        self.messages = messages
        self.errors = errors
        self.exceptions = exceptions
        self.stages = stages


@db_session
def make_root_run(repository, root_name):
    # type: (DbCaptureRepository, str) -> models.Run
    root_run = repository.produce_test_run(root_run=None, test_path_list=[root_name])
    return root_run


@db_session
def save_camera_root_run(repository, parent_run, test_path_list, camera_tests, camera_info):
    # type: (DbCaptureRepository, models.Run, list, timedelta, bool) -> models.Run
    run = repository.produce_test_run(
        parent_run, test_path_list, is_test=False)
    run.duration = camera_tests.duration
    run.started_at = camera_tests.start_time
    run.outcome = status2outcome(camera_tests.passed)
    save_run_artifacts(
        repository, run, camera_tests.messages,
        camera_tests.errors, camera_tests.exceptions)
    if camera_info:
        repository.add_artifact(
            run,
            CAMERA_INFO_ARTIFACT_NAME,
            '%s-%s' % (run.name, CAMERA_INFO_ARTIFACT_NAME),
            repository.artifact_type.json,
            json.dumps(camera_info, indent=2, ))
    return run


@db_session
def save_root_run_info(repository, root_run, passed, started_at, artifacts):
    # type: (DbCaptureRepository, models.Run, bool, timedelta, dict) -> None
    root_run = models.Run[root_run.id]
    root_run.outcome = status2outcome(passed)
    root_run.started_at = started_at
    for artifact_name, artifact_file in artifacts.items():
        if artifact_name not in [TEST_RESULTS_FILE_NAME, ALL_CAMERAS_FILENAME]:
            _logger.debug("Save root artifact '%s'...", artifact_name)
            repository.add_artifact(
                root_run,
                artifact_name,
                '%s-%s' % (root_run.name, artifact_name),
                file_ext_to_artifact_type(
                    artifact_file.suffix, repository.artifact_type),
                artifact_file.read_bytes())
            _logger.debug("Save root '%s' artifact done.", artifact_name)


def save_run_artifacts(repository, run, messages, errors, exceptions):
    # type: (DbCaptureRepository, models.Run, timedelta, bool, list, list, list) -> None
    repository.add_artifact(
        run,
        MESSAGES_ARTIFACT_NAME,
        '%s-%s' % (run.name, MESSAGES_ARTIFACT_NAME),
        repository.artifact_type.output,
        '\n'.join(messages))
    repository.add_artifact(
        run,
        ERRORS_ARTIFACT_NAME,
        '%s-%s' % (run.name, ERRORS_ARTIFACT_NAME),
        repository.artifact_type.output,
        '\n'.join(errors),
        is_error=True)
    repository.add_artifact(
        run,
        ERRORS_ARTIFACT_NAME,
        '%s-%s' % (run.name, EXCEPTION_ARTIFACT_NAME),
        repository.artifact_type.output,
        '\n'.join(exceptions),
        is_error=True)


def produce_camera_tests(repository, root_run, parent_path_list, camera_tests, all_cameras):
    # type: (DbCaptureRepository, models.Run, list, dict, dict) -> None
    _logger.debug("Process camera '%s' data", camera_tests.camera_id)
    test_path_list = parent_path_list + [camera_tests.camera_id]

    camera_info = all_cameras.get(camera_tests.camera_id)
    camera_run = save_camera_root_run(
        repository, root_run, test_path_list, camera_tests, camera_info)

    for stage in camera_tests.stages:
        with db_session:
            stage_run = repository.produce_test_run(
                camera_run, test_path_list + [stage.name], is_test=True)
            stage_run.duration = stage.duration
            stage_run.started_at = stage.start_time
            stage_run.outcome = status2outcome(stage.passed)
            save_run_artifacts(
                repository, stage_run, stage.messages, stage.errors, stage.exceptions)


def collect_test_artifacts(work_dir):
    # type: (Path) -> dict
    _logger.info("Collect artifacts starting...")
    artifact_exts = ['.log', '.json', '.cap']
    artifacts = dict()
    for f in work_dir.rglob('*'):
        if f.is_file() and (
                f.suffix in artifact_exts or
                f.name in [TEST_RESULTS_FILE_NAME, ALL_CAMERAS_FILENAME]):
            _logger.debug("Artifact '%s' was found.", str(f))
            artifacts[f.name] = f
    _logger.info("Collect artifacts done.")
    return artifacts


def parse_all_cameras_file(all_cameras_file):
    # type: (Optional[Path]) -> dict
    if all_cameras_file is None:
        _logger.warning("Camera information file '%s' not found.", ALL_CAMERAS_FILENAME)
        return dict()
    else:
        with all_cameras_file.open() as f:
            return yaml.load(f)


def parse_and_save_results_to_db(repository, root_run, results_file, cameras_info):
    # type: (DbCaptureRepository, models.Run, Path, dict) -> (bool, timedelta)
    passed = True
    started_at = None

    _logger.info("'%s' processing...", str(results_file))
    with results_file.open() as f:
        camera_tests_list = [
            CameraTestStorage.from_camera_item(camera_item)
            for camera_item in yaml.load(f).items()]
        for camera_tests in camera_tests_list:
            if not produce_camera_tests(
                    repository, root_run, [root_run.name],
                    camera_tests, cameras_info):
                passed = False
            if camera_tests.start_time:
                if started_at:
                    started_at = min(started_at, camera_tests.start_time)
                else:
                    started_at = camera_tests.start_time
    _logger.info("'%s' processing done.", str(results_file))

    return passed, started_at


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
        'test_work_dir',
        type=dir_path,
        help='Test results file path')
    parser.add_argument(
        '--test-name',
        default=DEFAULT_UNIT_TEST_NAME,
        help='Name of test, default=%(default)r')

    args = parser.parse_args()

    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=format)
    repository = DbCaptureRepository(args.db_config, args.build_parameters)

    artifacts = collect_test_artifacts(args.test_work_dir)

    results_file = artifacts.get(TEST_RESULTS_FILE_NAME)
    all_cameras_file = artifacts.get(ALL_CAMERAS_FILENAME)
    if not results_file:
        _logger.error("Can't create test report, '%s' not found.", TEST_RESULTS_FILE_NAME)
        sys.exit(1)

    cameras_info = parse_all_cameras_file(all_cameras_file)

    root_run = make_root_run(repository, args.test_name)
    passed, started_at = parse_and_save_results_to_db(
        repository, root_run, results_file, cameras_info)
    save_root_run_info(repository, root_run, passed, started_at, artifacts)


if __name__ == "__main__":
    main()
