'''Use 'build_output_parser.py eswn <output-file>' to generate *.output files for this test'''

import os.path
import pytest
from junk_shop.build_output_parser import parse_output_lines


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_EXT = '.output'


def list_test_files():
    for name in os.listdir(TEST_DIR):
        base, ext = os.path.splitext(name)
        if ext == TEST_FILE_EXT:
            yield base

@pytest.mark.parametrize('test_file', list_test_files())
def test_parser(test_file):
    with open(os.path.join(TEST_DIR, test_file + TEST_FILE_EXT)) as f:
        test_line_list = f.read().splitlines()
    print
    expected_severity_list, line_list = zip(*(
        test_line.split('\t', 1) for test_line in test_line_list))
    for line_num, (expected_severity, (severity, rule_idx, line)) in enumerate(
            zip(expected_severity_list, parse_output_lines(line_list))):
        if severity is None:
            severity = 'none'
        print expected_severity, severity, repr(line[:200])
        if rule_idx is None:
            rule = '-'
        else:
            rule = 'rule#%d' % rule_idx
        assert expected_severity == severity, (
            '%s:%s: Got severity %r, but expected is %r (rule %s), line: %r' % (
                test_file, line_num + 1, severity, expected_severity, rule, line))
