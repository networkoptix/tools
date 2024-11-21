# Nx Submodules

// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

## General information

Nx Submodules is a Network Optix in-house substitution for standard git submodules. Nx submodule is
a directory ("submodule directory") inside a repository ("main repo"), containing a snapshot of a
directory from some other repository ("subrepo") and Nx submodule configuration file
`_nx_submodule`. This configuration file contains the following information:

- `subrepo-url`: Subrepo URL.
- `subrepo-dir`: A directory in the subrepo, which content is mirrored in the submodule directory.
- `git-ref`: Git reference in the subrepo, to which we want to "bind" the subrepo state. Can be
either a commit SHA, or a branch name.
- `commit-sha`: SHA of the commit in the subrepo, determining the content of the directory.
Contains the resolved reference from the `git-ref` field, i.e. it is either the same that `git-ref`
(if `git-ref` is a commit SHA), or the commit SHA corresponding to the branch/tag name stated in
the `git-ref` field.

This configuration file should be used to check consistency of the directory in the subrepo and
submodule directory. Files in the submodule directory, excluding the configuration file itself,
must be byte-to-byte identical in content and have the same permissions as the files in the subrepo
directory when the subrepo is checked out to the commit specified in the configuration file. Such
check can be performed by script triggered by git hook, performed as a job in the pipeline, or
using any other method you like.

## Working with Nx Submodules

There is a **tool** for managing Nx submodules called `nx_submodule.py`. Currently it can create an
Nx submodule (create a directory for it, get contents of the subrepo directory corresponding to
the specified git reference, copy it to the created directory and create the configuration file in
this directory) and update the Nx submodule (get contents of the subrepo directory corresponding to
the specified commit SHA/git reference, copy it to the submodule directory and update the
configuration file). To get more information on usage of this utility, run it with `--help`.

Also it is possible to create/update Nx submodules manually (create a directory with the
appropriate contents and edit `_nx_submodule` file), though this approach can be error-prone.

Unlike git submodules, Nx submodules allow to "mount" any inner directory of the subrepo, not only
its root. The corresponding option in `nx_submodule.py` is `--subrepo-dir`; its default value is
`.` which means the subrepo root.

## Typical workflow

If you need to update a repository that is included in the main repo as one or more Nx submodules,
you should perform the following steps:

1. Make necessary changes to the subrepo, create a Merge Request for them, go through a normal
review process, and push your changes to the `master` branch of the subrepo.

2. (optional) Get the commit SHA of your changes:
```
cd <subrepo_directory>
git pull fetch origin
git log origin/master -1 --format=format:"%H %s"
```

3. Go to the VMS repository directory.

4. Update the Nx submodule(s) in the main repository, referring to this subrepo. This can be done
in one of the following ways:

    - If there is only one Nx submodule using this subrepo, it can be updated by specifying the
    directory of the Nx submodule:
```
./nx_submodule.py update \
    --submodule-local-dir <nx_submodule_dir> \
    --git-ref master
```

    or, if you want to "stick" the submodule state to this specific commit,
```
./nx_submodule.py update \
    --submodule-local-dir <nx_submodule_dir> \
    --git-ref <commit_sha>
```

    Note that if the submodule references the needed branch name (`master` in this case), i.e., its
    descriptor contains the `git-ref` parameter with the value equal to this branch name, you can
    omit the `--git-ref` parameter:
```
./nx_submodule.py update --submodule-local-dir <nx_submodule_dir>
```

    - If there are more than one Nx submodule, created from same subrepo, it is possible to update
    them all at once to the actual state referenced by values of theirs `--git-ref` fields:
```
./nx_submodule.py update --subrepo-url <url_of_subrepo>
```

    Note that the `--subrepo-url` parameter here is used to select only those submodules in the
    main repo, that correspond to the needed `subrepo`. If the `subrepo` is already cloned to a
    local drive, you can use `--subrepo-working-dir <directory_where_subrepo_is_cloned>` instead.
    Also it is possible to use `--git-ref` to specify the new commit SHA/branch/tag name to which
    the state of the submodule must be updated.

5. Commit the changes to the main repository and verify that the submodule check passes using your
preferred method.

NOTE: It is also possible to update all the submodules in the main repo at once, using the
command:
```
./nx_submodule.py update --main-repo-dir <main_repo_directory>
```

This command will iterate over all the submodules, resolve `git-ref` field in the submodule
descriptor to the commit SHA, and update the submodule state to the one determined by it.
