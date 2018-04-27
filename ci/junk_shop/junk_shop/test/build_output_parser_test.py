'''Use 'build_output_parser.py eswn <output-file>' to generate *.output files for this test'''

import os.path
import logging

import pytest
from junk_shop.build_output_parser import SKIPPED_LINES_FORMAT, parse_output_lines


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_EXT = '.output'


def list_test_files():
    for name in os.listdir(TEST_DIR):
        base, ext = os.path.splitext(name)
        if ext == TEST_FILE_EXT:
            yield base

@pytest.mark.parametrize('test_file', list_test_files())
def test_parser(test_file):
    logging.basicConfig(level=logging.DEBUG, format='| %(message)s')
    logging.getLogger('junk_shop.build_output_parser').setLevel(logging.DEBUG)
    with open(os.path.join(TEST_DIR, test_file + TEST_FILE_EXT)) as f:
        test_line_list = f.read().splitlines()
    print
    expected_severity_list, line_list = zip(*(
        test_line.split('\t', 1) for test_line in test_line_list))
    match_gen = parse_output_lines(line_list)
    skipped_count = 0
    for line_num, (expected_severity, line) in enumerate(zip(expected_severity_list, line_list)):
        if expected_severity == 'skip':
            skipped_count += 1
            continue
        if expected_severity == 'ignore':
            continue
        match = next(match_gen)
        if skipped_count:
            expected_skip_line = SKIPPED_LINES_FORMAT % skipped_count
            assert match.line == expected_skip_line
            skipped_count = 0
            match = next(match_gen)
        severity = match.severity or 'none'
        print line_num, expected_severity, severity, repr(match.line[:200])
        if match.pattern_idx is None:
            rule = '-'
        else:
            rule = 'pattern#%d' % match.pattern_idx
        assert expected_severity == severity, (
            '%s:%s: Got severity %r, but expected is %r (rule %s), line: %r' % (
                test_file, line_num + 1, severity, expected_severity, rule, match.line))
    assert line_num + 1 == len(line_list)
