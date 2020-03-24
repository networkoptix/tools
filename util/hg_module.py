#!/usr/bin/env python

from subprocess import check_output
import _strptime    #workaround multithreading bug
from datetime import datetime
import threading


class Branch():
    def __init__(self, name, rev, hash, active):
        self.name = name
        self.rev = rev
        self.hash = hash
        self.active = active
        self.user = ''
        self.date = datetime.now()
        self.age = self.date - self.date

    def __str__(self):
        return self.name


def get_branch_details(branch):
    log = "hg log -r " + branch.rev + ' --template "date:{date|shortdate}\\nuser:{author}"'
    info = check_output(log, shell=True)
    for row in info.split('\n'):
        if 'user:' in row:
            key, value = row.split(':')
            user = value.strip()
            if '<' in user:
                user = user.split('<')[0].strip()
            branch.user = user
        if 'date:' in row:
            dateStr = row[5:].strip()
            date = datetime.strptime(dateStr, "%Y-%m-%d")
            age = datetime.now() - date
            branch.date = date
            branch.age = age


def get_branch_details_threaded(branch):
    thread = threading.Thread(None, get_branch_details, args=(branch,))
    thread.start()
    return thread


def get_branches(detailed=True):
    output = check_output("hg branches", shell=True)
    result = []

    for row in output.split('\n'):
        if ':' in row:
            key, hash = row.split(':')
            name, rev = key.rsplit(' ', 1)
            if name == 'default':
                continue
            branch = Branch(name, rev, hash, True)
            if '(' in hash:
                branch.hash = hash.split('(')[0].strip()
                branch.active = False
            result.append(branch)

    if not detailed:
        return result

    threads = []
    for branch in result:
        threads.append(get_branch_details_threaded(branch))

    for thread in threads:
        thread.join()

    return result
