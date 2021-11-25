#!/usr/bin/env python

import argparse
from pathlib import Path
import sys
from typing import Optional

import nx_submodule_lib


# Last "\t" is for leaving an empty line after the usage text.
USAGE = """

To create Nx submodule:
    nx_submodule.py create \\
        --submodule-local-dir <dir_inside_main_repo> \\
        (--subrepo-working-dir <cloned_subrepo_dir> | --subrepo-url <subrepo_url>) \\
        [--subrepo-dir <path_relative_to_subrepo>] \\
        --commit-sha <commit_sha>

To update Nx submodule:
    
    Update all Nx submodules in the current or specified main repo:

        nx_submodule.py update \\
            [--main-repo-dir <main_repository_dir] \\
            (--subrepo-working-dir <cloned_subrepo_dir> | --subrepo-url <subrepo_url>) \\
            --commit-sha <commit_sha>

    Update Nx submodule in the main repo containing the specified local submodule dir:

    nx_submodule.py update \\
        --submodule-local-dir <dir_inside_main_repo> \\
        --commit-sha <commit_sha>
\t
"""

config_file_name = nx_submodule_lib.NxSubmoduleConfig.CONFIG_FILE_NAME
DESCRIPTION = f"""
This is a tool for managing "Nx submodules" - a substitution for standard git submodules.
Nx submodule is a directory inside the repository ("main repo") mirroring contents of some
directory inside another repository ("sub-repo"). URL of the sub-repo, its directory and SHA of the
commit determining the state of the sub-repo are saved in the configuration file "{config_file_name}"
which is stored in the submodule directory in the main repo.
"""

def _create_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=DESCRIPTION,
        usage=USAGE)

    parser.add_argument(
        "--commit-sha",
        type=str,
        required=True,
        help="Commit SHA of the sub-repository.")
    parser.add_argument(
        "--subrepo-dir",
        default=".",
        type=str,
        help=(
          "Directory inside the sub-repository to add to the main repository as Nx submodule."
          'Default value is "." which means the root directory.'))

    main_repo_dir = parser.add_mutually_exclusive_group()
    main_repo_dir.add_argument("--main-repo-dir", type=Path, help="Main repository directory.")
    main_repo_dir.add_argument(
        "--submodule-local-dir",
        type=Path,
        help="Directory inside the main repository where the Nx submodule resides.")

    repo_location = parser.add_mutually_exclusive_group()
    repo_location.add_argument(
        "--subrepo-working-dir",
        type=Path,
        help="Directory where the repository to add as a Nx submodule is cloned.")
    repo_location.add_argument(
        "--subrepo-url",
        type=str,
        help="URL of the sub-repository.")

    parser.add_argument(
        "action",
        choices=['create', 'update'],
        help="Action to perform with Nx submodule.")

    return parser


def _get_repo_url(args) -> Optional[str]:
    try:
        if args.subrepo_working_dir:
            return nx_submodule_lib.get_repo_url_by_local_dir(args.subrepo_working_dir.resolve())
    except nx_submodule_lib.NxSubmoduleMultipleRemotesError as exc:
        sys.exit(
            f"ERROR: Multiple remotes in {args.subrepo_working_dir.as_posix()!r} directory: "
            f'{exc.remote_urls!r}. Use "--subrepo-url" to specify the right one.')

    if args.subrepo_url:
        return nx_submodule_lib.normalize_git_repo_url(args.subrepo_url)

    return None


def _exit(message: str, parser: argparse.ArgumentParser):
    parser.print_usage(file=sys.stderr)
    print(f"{Path(__file__).name}: error: {message}", file=sys.stderr)    
    exit(1)


def main():
    parser = _create_arg_parser()
    args = parser.parse_args()

    if args.action == "create":
        if not args.submodule_local_dir:
            _exit(
                '"--submodule-local-dir" parameter is mandatory when creating Nx submodule',
                parser)

        if Path(args.subrepo_dir).is_absolute():
            _exit('"--subrepo-dir" parameter must not be an absolute path', parser)
     
        if (repo_url := _get_repo_url(args)) is None:
            _exit(
                'One of "--subrepo-working-dir" or "--subrepo-url" must be set when creating Nx '
                'submodule',
                parser)

        nx_submodule_lib.create_submodule(
            dir=args.submodule_local_dir.resolve(),
            repo_url=repo_url,
            repo_dir=args.subrepo_dir,
            commit_sha=args.commit_sha)

    else:  # args.action == "update"       
        if args.submodule_local_dir:
            nx_submodule_lib.update_submodule(
                dir=args.submodule_local_dir.resolve(), commit_sha=args.commit_sha)
        elif repo_url :=  _get_repo_url(args):
            main_repo_dir = (args.main_repo_dir or Path.cwd()).resolve()
            nx_submodule_lib.find_and_update_submodules(
                main_repo_dir=main_repo_dir, commit_sha=args.commit_sha, repo_url=repo_url)
        else:
            _exit(
                'Either "--submodule-dir" parameter or one of "--subrepo-local-dir" or '
                '"--subrepo-url" must be set when updating Nx submodule',
                parser)


if __name__ == "__main__":
  try:
    main()
  except nx_submodule_lib.NxSubmoduleError as err:
    sys.exit(str(err))
