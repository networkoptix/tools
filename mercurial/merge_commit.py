#!/usr/bin/env python


import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from mercurial_utils import HgContext, CommitMessageChecker


def merge_commit(edit=False, user=None):
    hg = HgContext()

    parents = hg.execute("parents", "--template", "{node}\n").split()
    if len(parents) < 2:
        print("Current head has only one parent. This command is for merge commits only.")
        exit(1)
    elif len(parents) > 2:
        exit(1)

    branch = hg.branch()

    other = None
    other_branch = None

    for parent in parents:
        b = hg.branch(parent)
        if b != branch:
            other = parent
            other_branch = b

    if not other:
        print("Both parent revisions are from the same branch. To merge heads use 'commit'.")
        return

    message = "Merge: {0} -> {1}\n\n".format(other_branch, branch)
    message_checker = CommitMessageChecker()

    description = hg.log(
        rev="only('{0}', '{1}')".format(other_branch, branch),
        template="{desc|firstline}\n")
    message += "\n".join([
        msg for msg in description if message_checker.is_commit_message_accepted(msg)])

    hg.commit(message=message, edit=edit, user=user)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-e", "--edit", action="store_true",
        help="Invoke editor on commit messages")
    parser.add_argument(
        "-u", "--user",
        help="Record the specified user as committer")

    args = parser.parse_args()

    merge_commit(edit=args.edit, user=args.user)
