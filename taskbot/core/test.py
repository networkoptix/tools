#!/usr/bin/env python

# $Id$
# Artem V. Nikitin

import os, subprocess

r, w = os.pipe()


def before_exec():
  os.close(r)


p = subprocess.Popen(
  ['/bin/bash'],
  preexec_fn = before_exec,
  shell = False,
  stdin  = subprocess.PIPE,
  stdout = subprocess.PIPE,
  stderr = subprocess.PIPE)

os.close(w)
r = os.fdopen(r, 'r')

p.stdin.write("ls -l\n")

print p.stdout.read()



