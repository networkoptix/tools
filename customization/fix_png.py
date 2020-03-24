#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import time

command = ['pngcrush', '-ow', '-rem', 'allb', '-reduce']

Processes = {}
MaxProc = 1
Quantum = 0.1


def check_proc():
    for key, proc in Processes.items():  # not .iteritems() - the dict is modified inside the loop
        if proc.poll() is not None:
            print "'{}' processing finished {}".format(
                key, "OK" if proc.returncode == 0 else "with code {}".format(proc.returncode)
            )
            del Processes[key]


def system_call(filename, cwd="."):
    check_proc()
    while len(Processes) >= MaxProc:
        time.sleep(Quantum)
        check_proc()
    print("Processing '{}' in '{}'".format(filename, cwd))
    Processes[filename] = subprocess.Popen(command + [filename], cwd=cwd)


def fix_image_files(root=os.curdir):
    for dirname, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith('.png'):
                continue
            system_call(filename, dirname)
    while Processes:
        check_proc()


if __name__ == '__main__':
    fix_image_files()
