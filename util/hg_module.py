# -*- coding: utf-8 -*-
#/bin/python

from subprocess import check_output
from datetime import datetime

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
        
def get_branches(detailed = True):
    output = check_output("hg branches", shell=True)
    result = []
    curDate = datetime.now()

    for row in output.split('\n'):
        if ':' in row:
            key, hash = row.split(':')
            name, rev = key.split()
            if name == 'default':
                continue
            branch = Branch(name, rev, hash, True)
            if '(' in hash:
                branch.hash = hash.split('(')[0].strip()
                branch.active = False
            result.append(branch)
            
    if not detailed:
        return result
            
    curDate = datetime.now()
   
    for branch in result:
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
                age = curDate - date
                branch.date = date
                branch.age = age
    
    return result         
