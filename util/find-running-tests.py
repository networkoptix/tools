#!/bin/env python

import argparse
from collections import namedtuple

def read_test_actions(log_path):
    for line in open(log_path):
        line = line[32:].strip()
        if 'is started' in line:
            yield line.split(' ')[0], 'started'
        elif 'ended with exit code' in line:
            yield line.split(' ')[0], 'stopped'


def find_running(log_path, target_test, skip_binary=False):
    running = set()
    finished = []
    for test, state in read_test_actions(log_path):
        if skip_binary:
            test = '.'.join(test.split('.')[1:])
        if test == target_test:
            return running, finished

        if state == 'started':
            running.add(test)
        elif state == 'stopped':
            running.remove(test)
            finished.append(test)

    raise ValueError(f'Test not found: {target_test}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', help='Log file path')
    parser.add_argument('target_test', help='Target test')
    parser.add_argument('-m', '--mode', default='r', help='(r)unning or (f)inished')
    parser.add_argument('-d', '--delimitor', default='\n', help='output delimitor')
    parser.add_argument('-s', '--skip-binary', action='store_true', help='skip binary name')

    args = parser.parse_args()
    running, finished = find_running(args.log_path, args.target_test, args.skip_binary)
    if 'r' in args.mode: print(args.delimitor.join(running))
    if 'f' in args.mode: print(args.delimitor.join(finished))


if __name__ == '__main__':
    main()
