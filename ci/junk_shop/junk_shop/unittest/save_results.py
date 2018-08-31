import logging

from pony.orm import db_session

from ..utils import status2outcome, outcome2status
from .. import models

log = logging.getLogger(__name__)


def add_output_artifact(repository, run, name, data, is_error=False):
    full_name = '%s-%s' % (run.name, name.replace(' ', '-'))
    type = repository.artifact_type.output
    repository.add_artifact(run, name, full_name, type, data, is_error)


def produce_test_run(repository, parent_run, parent_path_list, test_name, results):
    test_path_list = parent_path_list + [test_name]
    with db_session:
        run = repository.produce_test_run(
            parent_run, test_path_list, is_test=results.is_leaf if results else False)
        run.outcome = status2outcome(results.passed if results else False)

        if results.test_artifacts:
            error_list = results.test_artifacts.test_info.errors
            if results.test_artifacts.test_info.exit_code != 0:
                # do not add exit code error if it is caused by failed gtest (which set it to 1 then)
                # and it is already caused run.outcome to be failed
                if outcome2status(run.outcome) or results.test_artifacts.test_info.exit_code != 1:
                    error_list.append('exit code: %d' % results.test_artifacts.test_info.exit_code)
            add_output_artifact(repository, run, 'errors', '\n'.join(error_list), is_error=True)
            add_output_artifact(repository, run, 'command line', results.test_artifacts.test_info.command_line)
            add_output_artifact(repository, run, 'full output', results.test_artifacts.output_file_path.read_bytes())
            for backtrace_path in results.test_artifacts.backtrace_file_list:
                name = backtrace_path.name
                repository.add_artifact(run, name, name, repository.artifact_type.traceback,
                                        backtrace_path.read_bytes(), is_error=True)
        for name, artifact in results.lines_artifacts.items():
            data = artifact.data
            if artifact.is_truncated:
                data = ('[ produced %d lines, truncated to %d lines ]\n' %
                        (artifact.line_count, artifact.line_count_limit) + data)
            add_output_artifact(repository, run, name, data, artifact.is_error)

        run.duration = results.duration
        run.started_at = None

        if not results:
            return run

    for child_results in results.children:
        produce_test_run(repository, run, test_path_list, child_results.test_name, child_results)

    return run


@db_session
def make_root_run(repository, run_info, root_name):
    root_run = repository.produce_test_run(root_run=None, test_path_list=[root_name])
    root_run.duration = run_info.duration
    add_output_artifact(repository, root_run, 'errors', '\n'.join(run_info.errors), is_error=True)
    return root_run


@db_session
def save_root_test_info(repository, run, test_record):
    run = models.Run[run.id]
    run.started_at = test_record.test_results.started_at
    run.duration = test_record.test_results.duration
    # outcome
    run.outcome = status2outcome(test_record.test_results.passed)
    return test_record.test_results.passed


def save_test_results(repository, root_name, run_info, test_record_list):
    root_run = make_root_run(repository, run_info, root_name)
    log.info('Root run: id=%r', root_run.id)
    passed = True
    for test_record in test_record_list:
        run = produce_test_run(repository, root_run, [root_name], test_record.test_name, test_record.test_results)
        test_passed = save_root_test_info(repository, run, test_record)
        if not test_passed:
            passed = False
    with db_session:
        root_run = models.Run[root_run.id]
        root_run.outcome = status2outcome(passed)
    return passed
