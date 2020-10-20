_wip_url = ("https://docs.gitlab.com/ee/user/project/merge_requests/work_in_progress_merge_requests.html"
            "#removing-the-draft-flag-from-a-merge-request")

merged_message = "Merge request was successfully merged into `{branch}` branch."
run_pipeline_message = "Running pipeline {pipeline_id}: {reason}."

commits_wait_message = """There are no commits in MR. I won't do anything until commits arrive."""
pipeline_wait_message = """There is already [pipeline {pipeline_id}]({pipeline_url}) in progress.
Lets wait until it finishes."""
approval_wait_message = """Not enough approvals, **{approvals_left}** more required.
I will start merging process once all approvals are collected."""

unresolved_threads_message = f"""Merge request returned to development.
Please, resolve all discussions and [remove WIP]({_wip_url}) to continue merging process."""

conflicts_message = f"""Merge request returned to development.
Please, do manual rebase and [remove WIP]({_wip_url}) to continue merging process."""

failed_pipeline_message = f"""Merge request returned to development.
Please, fix the errors and [remove WIP]({_wip_url}) to continue merging process.\n
You may rebase or run new pipeline manually if errors are resolved outside MR."""

template = """### {emoji} {title}

{message}

---

###### Robocat @ [Workflow Police](https://networkoptix.atlassian.net/wiki/spaces/SD/pages/1486749741/Automation+Workflow+Police+bot)
"""  # noqa
