# Load mercurial diff for a revision range, parse it to find added and removed lines

import re
import sys

from host import LocalHost


ADDED_FILE_REGEXP = r'^--- /dev/null.+\n\+{3} b/(\S+).+$'
REMOVED_FILE_REGEXP = r'^--- a/(\S+).+\n\+{3} /dev/null.+$'
CHANGED_FILE_REGEXP = r'^--- a/(?P<path>\S+).+\n\+{3} b/(?P=path).+$'


class HgChanges(object):

    def __init__(self, added_file_list, removed_file_list, changed_file_list):
        self.added_file_list = added_file_list
        self.removed_file_list = removed_file_list
        self.changed_file_list = changed_file_list


def load_hg_changes(repository_dir, prev_revision, current_revision):
    host = LocalHost()
    diff_text = host.get_command_output(
        ['hg', 'diff', '--rev', prev_revision, '--rev', current_revision],
        cwd=repository_dir, log_output=False)
    return parse_diff(diff_text)
    
def parse_diff(diff_text):
    return HgChanges(
        added_file_list=re.findall(ADDED_FILE_REGEXP, diff_text, re.MULTILINE),
        removed_file_list=re.findall(REMOVED_FILE_REGEXP, diff_text, re.MULTILINE),
        changed_file_list=re.findall(CHANGED_FILE_REGEXP, diff_text, re.MULTILINE))


def test_me():
    if sys.argv[1] == 'diff':
        changes = parse_diff(sys.stdin.read())
    elif sys.argv[1] == 'revset':
        repository_dir = sys.argv[2]
        prev_revision = sys.argv[3]
        current_revision = sys.argv[4]
        changes = load_hg_changes(repository_dir, prev_revision, current_revision)
    else:
        print >> sys.stderr, 'Usage: %s (diff < some.diff)|(revset <repository-dir> <prev-revision> <current-revision>)' % sys.argv[0]
        sys.exit(1)
    print '%d added files:' % len(changes.added_file_list)
    for path in changes.added_file_list:
        print '\t%s' % path
    print '%d removed files:' % len(changes.removed_file_list)
    for path in changes.removed_file_list:
        print '\t%s' % path
    print '%d changed files:' % len(changes.changed_file_list)
    for path in changes.changed_file_list:
        print '\t%s' % path


if __name__ == '__main__':
    test_me()
