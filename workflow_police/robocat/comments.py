_wip_url = ("https://docs.gitlab.com/ee/user/project/merge_requests/work_in_progress_merge_requests.html"
            "#removing-the-draft-flag-from-a-merge-request")

merged_message = "Merge request was successfully merged into `{branch}` branch."
run_pipeline_message = "Running pipeline {pipeline}."

conflicts_message = f"""Merge request returned to development.
Please, do manual rebase and [remove WIP]({_wip_url}) to continue merging process."""

failed_pipeline_message = f"""Merge request returned to development.
Please, fix the errors and [remove WIP]({_wip_url}) to continue merging process.\n
You may rebase or run new pipeline manually if errors are resolved outside MR."""

template = """### {emoji} {title}

{message}

---

###### Robocat @ [Workflow Police :robot_face:](https://networkoptix.atlassian.net/wiki/spaces/SD/pages/1486749741/Automation+Workflow+Police+bot)
"""  # noqa
