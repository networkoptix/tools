import logging

from pony.orm import db_session, flush

from ..utils import status2outcome, outcome2status

log = logging.getLogger(__name__)


# do not store core files larger than this to not pullute db
CORE_FILE_SIZE_LIMIT = 100 * 1024*1024


def add_output_artifact(repository, run, name, data, is_error=False):
    full_name = '%s-%s' % (run.name, name.replace(' ', '-'))
    type = repository.artifact_type.output
    repository.add_artifact(run, name, full_name, type, data, is_error)

def produce_test_run(repository, parent_run, parent_path_list, test_name, results):
    test_path_list = parent_path_list + [test_name]
    run = repository.produce_test_run(
        parent_run, test_path_list, is_test=results.is_leaf if results else False)
    run.outcome = status2outcome(results.passed if results else False)
    if not results:
        return run
    run.duration = results.duration
    run.started_at = None
    for name, artifact in results.lines_artifacts.items():
        data = artifact.data
        if artifact.is_truncated:
            data = ('[ produced %d lines, truncated to %d lines ]\n'
                        % (artifact.line_count, artifact.line_count_limit) + data)
        add_output_artifact(repository, run, name, data, artifact.is_error)

    for child_results in results.children:
        produce_test_run(repository, run, test_path_list, child_results.test_name, child_results)

    return run

@db_session
def save_test_results(repository, test_record_list):
    root_run = repository.produce_test_run(root_run=None, test_path_list=['unit'])
    flush()  # acquire root_run.id
    print 'Root run: id=%r' % root_run.id
    passed = True
    for test_record in test_record_list:
        run = produce_test_run(repository, root_run, ['unit'], test_record.test_name, test_record.test_results)
        run.started_at = test_record.test_info.started_at
        run.duration = test_record.test_info.duration
        error_list = test_record.test_info.errors
        if test_record.test_info.exit_code != 0:
            error_list.append('exit code: %d' % test_record.test_info.exit_code)
            passed = False
        add_output_artifact(repository, run, 'errors', '\n'.join(error_list), is_error=True)
        add_output_artifact(repository, run, 'command line', test_record.test_info.command_line)
        add_output_artifact(repository, run, 'full output', test_record.output_file_path.read_text())
        # core and backtraces
        for core_file_path in test_record.core_file_list:
            size = core_file_path.stat().st_size
            if size <= CORE_FILE_SIZE_LIMIT:
                name = core_file_path.name
                repository.add_artifact(run, name, name, repository.artifact_type.core, core_file_path.read_bytes(), is_error=True)
            else:
                log.info('Core file "%s" is too large (%rB); will not store', core_file_path, size)
        for backtrace_path in test_record.backtrace_file_list:
            name = backtrace_path.name
            repository.add_artifact(run, name, name, repository.artifact_type.traceback, backtrace_path.read_bytes(), is_error=True)
        # outcome
        if not outcome2status(run.outcome):
            passed = False
    root_run.outcome = status2outcome(passed)
    return passed
