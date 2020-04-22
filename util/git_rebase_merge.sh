#!/bin/bash

if [[ ! "$1" ]] || [[ "$1" == -h ]] || [[ "$1" == --help ]]; then cat <<END
Rebases merge commit resolving only new conflicts if they appear.
Usage:
    git checkout x/vms_merge_from_4.1
    $0 origin/vms
    # If there are no conflict, you're done, otherwise resolve them and continue.
    git add .
    $0 --continue
END
exit 0; fi

set -e -x

if [[ $1 != -c]] && [[ $1 != --continue ]]; then
    SOURCE=$(git rev-parse --abbrev-ref HEAD)
    TARGET=$1
    [ ! $TARGET ] && exit 1

    # Prepare history.
    git fetch
    git checkout -b tmp_history
    git rebase -s ours -p $TARGET

    # Prepare correct index.
    git checkout $SOURCE
    git merge $TARGET
else
    # Finalize branch.
    git merge --continue || true
fi

# Transfer changes.
git reset --soft tmp_history
git commit --amend
git branch -D tmp_history

