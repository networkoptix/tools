from mercurial import cmdutil, commands, revset
from mercurial.i18n import _

import sys, os
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from mercurial_utils import CommitMessageChecker

cmdtable = {}
command = cmdutil.command(cmdtable)

command_options = [
    ('', 'amend', None, _('amend the parent of the working directory')),
    ('u', 'user', '', _('record the specified user as committer'), _('USER')),
    ('e', 'edit', None, _('invoke editor on commit messages'))
]
@command('merge-commit', command_options, _('[OPTIONS]'))
def merge_commit(ui, repo, *pats, **opts):
    ctx = repo[None]

    parents = ctx.parents()
    if len(parents) < 2:
        ui.write_err("Current head has only one parent. This command is for merge commits only.\n")
        return
    elif len(parents) > 2:
        ui.write_err("Current head has too many parents. This command handles only simple merges.\n")
        return

    branch = ctx.branch()

    other = None

    for i in [0, 1]:
        if parents[i].branch() != branch:
            other = parents[i]

    if not other:
        ui.write_err("Both parent revisions are from the same branch. To merge heads use 'commit'.")
        return

    message = "Merge: {0} -> {1}\n".format(other.branch(), branch)
    message_checker = CommitMessageChecker()
    match = revset.match(ui, "(::{0} - ::{1})".format(other.branch(), branch), repo)
    for rev in match(repo, set(range(len(repo)))):
        description = repo[rev].description()
        if description:
            summary = description.split('\n')[0].strip()
            if message_checker.is_commit_message_accepted(summary):
                message += summary + "\n"

    options = opts
    options["message"] = message
    commands.commit(ui, repo, *pats, **options)
