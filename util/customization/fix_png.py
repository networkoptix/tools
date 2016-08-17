# -*- coding: utf-8 -*-
#/bin/python

import os
import subprocess

def system_call(args, cwd="."):
    print("Running '{}' in '{}'".format(str(args), cwd))
    subprocess.call(args, cwd=cwd)
    pass

def fix_image_files(root=os.curdir):
    for dirname, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith('.png'):
                continue
            system_call("pngcrush -ow -rem allb -reduce {}".format(filename), dirname)

fix_image_files()