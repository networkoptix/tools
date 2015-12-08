#!/bin/python3

import argparse
import os
import subprocess
import re

ignored_modules = [
    'hdwitness',
    'build_variables',
    'build_environment',
    'nx_sdk',
    'nx_storage_sdk'
]

def ignored(module):
    return module in ignored_modules or module.endswith('-deb')

def normalized(module):
    return module.replace('.', '_')

def get_dep_tree(mvn_args):
    command = [ 'mvn' ]
    if mvn_args:
        command += mvn_args
    command += [ 'dependency:tree' ]
    p = subprocess.Popen(command, stdout=subprocess.PIPE)

    root_re = re.compile(b'\[INFO\] --- maven-dependency-plugin:.*:tree .* @ (.+) ---.*')
    dep_re = re.compile(b'\[INFO\] [+\\\\]{1}- .*:(.+):pom.*')

    dep_tree = {}

    module = None
    deps = []

    for line in p.stdout:
        m = root_re.match(line)
        if m:
            if module:
                dep_tree[module] = deps
                deps = []
                module = None

            mod = m.group(1).decode('utf-8')
            if not ignored(mod):
                module = mod
        else:
            m = dep_re.match(line)
            if m:
                dep = m.group(1).decode('utf-8')
                if not ignored(dep):
                    deps.append(dep)

    if module:
        dep_tree[module] = deps
        deps = []

    return dep_tree

def find_pro(module):
    command = ['find', '.', '-name', module + '.pro']
    output = subprocess.check_output(command)
    lines = output.splitlines()
    if len(lines) > 1:
        print('Multiple .pro files found for {0}:'.format(module))
        for line in lines:
            print(line.decode('utf-8'))
        print('Make sure you cleared your workspace before reconfiguration.')
        return None
    if not lines:
        print('Could not find .pro file for {0}.'.format(module))
        print('Run mvn compile first.')
        return None

    path = lines[0].decode('utf-8').strip()
    if path.startswith('./'):
        path = path[2:]
    return path

def get_pro_files(modules):
    result = {}

    for module in modules:
        pro = find_pro(module)
        if pro:
            result[module] = pro
        else:
            return None

    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path-suffix', type=str, help="Relative path to module .pro file (now it's processor arch name).", default="x64")
    parser.add_argument('-o', '--output', type=str, help="Output .pro file name.", default="vms.pro")

    args, mvnargs = parser.parse_known_args()

    dep_tree = get_dep_tree(mvnargs)
    pro_files = get_pro_files(list(dep_tree.keys()))
    print(pro_files)
    return

    with open(args.output, 'w') as pro_file:
        pro_file.write('TEMPLATE = subdirs\n\n')
        pro_file.write('SUBDIRS = \\\n')

        for module in dep_tree:
            pro_file.write('    {0} \\\n'.format(normalized(module)))

        pro_file.write('\n')

        for module in dep_tree:
            deps = dep_tree[module]
            if deps:
                pro_file.write('{0}.depends = {1}\n'.format(
                        normalized(module), ' '.join(normalized(mod) for mod in deps)))

        pro_file.write('\n')

        for module in dep_tree:
            pro_file.write('{0}.file = {1}\n'.format(normalized(module), pro_files[module]))

        pro_file.write('\n')
    print('Output is written to {0}'.format(args.output))

if __name__ == "__main__":
    main()
