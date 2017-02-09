# -*- coding: utf-8 -*-
#/bin/python

from hg_module import get_branches
from datetime import timedelta

tooOld = timedelta(days = 30)

def calculate_color(branch):
    primary = 'ff'
    secondary = '00'
    tertiary = '00'
    if '2.4.0' in branch.name:
        secondary = 'ba'
    elif '2.4.1' in branch.name:
        secondary = '75'
    elif '2.5' in branch.name:
        secondary = '00'
    
    if 'gui' in branch.name:
        tertiary = '84'
    
    if branch.name.startswith('release_'):
        return "#{0}{1}{2}".format(primary, secondary, secondary)
    
    if branch.name.startswith('prod_'):
        return "#{0}{1}{2}".format(secondary, '84', secondary)
    
    if branch.name.startswith('dev_'):
        return "#{0}{1}{2}".format(secondary, tertiary, primary)
        
    return "#BCBCBC"

def process_branches(branches):
    # dev_2.4.0_gui:#0000FF prod_2.4.0:#000000
    
    line = ''
    for branch in branches:
        if branch.age > tooOld:
            continue
        color = calculate_color(branch)
        line = "{0}{1}:{2} ".format(line, branch.name, color)

    print line

def main():           
    branches = get_branches()
    process_branches(branches)

if __name__ == "__main__":
    main()