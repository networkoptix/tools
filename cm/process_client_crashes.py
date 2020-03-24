#!/usr/bin/env python

import requests

from jira_auth import AUTH

API_URL = 'https://networkoptix.atlassian.net/rest/api/2/'
SEARCH_URL = API_URL + 'search'
QUERY = (
    'project = VMS '
    'AND issuetype = Crash '
    'AND status = Open '
    'AND fixVersion = 4.0 '
    'AND assignee = sivanov'
)

PROBLEMS = {
    '::create_sys': "Handles overflow",
    'RtlAllocateHeap': "Memory overflow",
    'QByteArray::QByteArray': "Memory overflow",
    '_malloc_base': "Memory overflow",
    'Qt5WebKit!': "Webkit issue",
    'atio6axx': "Graphics driver issue",
    'nvoglv64': "Graphics driver issue",
    'ig75icd64': "Graphics driver issue",
    'FileOpenScreenHook64': "3rd party software issue",
    'glGetString': "OpenGL issue",
    'initializeOpenGLFunctions': "OpenGL issue",
}

PARSE_LINES = 3
PARSING_START_TOKEN = 'Call Site'


def totalCount():
    url = f"{SEARCH_URL}?jql={QUERY}&fields=id,key&startAt=0&maxResults=1"
    with requests.get(url, auth=AUTH) as result:
        data = result.json()
        return data['total']


def issuesFrom(pos):
    url = f"{SEARCH_URL}?jql={QUERY}&fields=id,key&startAt={pos}"
    with requests.get(url, auth=AUTH) as result:
        data = result.json()
        yield from data['issues']


def determineProblem(line):
    for key, value in PROBLEMS.items():
        if key in line:
            return value
    return None


def findProblemInAttachements(attachements):
    for attachement in attachements:
        if '.cdb-bt' not in attachement['filename']:
            continue
        url = attachement['content']
        with requests.get(url, auth=AUTH) as result:
            call_stack = result.text.splitlines()
            parsing_begin = False
            lines_parsed = 0
            for line in call_stack:
                if PARSING_START_TOKEN in line:
                    parsing_begin = True
                    continue
                if not parsing_begin:
                    continue

                lines_parsed += 1
                print(line)
                problem = determineProblem(line)
                if problem:
                    return problem
                if lines_parsed >= PARSE_LINES:
                    return None
        return None


def closeIssue(issue, problem):
    update_json = {
        "update": {
            "comment": [
                {
                    "add": {
                        "body": "Resolved via automated process. Reason: {}".format(problem)
                    }
                }
            ]
        },
        "transition": {
            "id": "71"
        },
        "fields": {
            "resolution": {
                "name": "Rejected"
            }
        }
    }

    url = issue['self'] + '/transitions'
    requests.post(url, json=update_json, auth=AUTH)


def processIssue(issue):
    url = issue['self'] + '?fields=attachment'
    with requests.get(url, auth=AUTH) as result:
        data = result.json()
        fields = data['fields']
        print(data['key'])
        attachements = fields['attachment']
        problem = findProblemInAttachements(attachements)
        if problem:
            closeIssue(issue, problem)
            print("-> {} detected".format(problem))
        print('-----')


def markIssues():
    total = totalCount()
    current = 0
    while current < total:
        for issue in issuesFrom(current):
            processIssue(issue)
            current += 1
    print(f"{current} issues processed")


if __name__ == "__main__":
    markIssues()
