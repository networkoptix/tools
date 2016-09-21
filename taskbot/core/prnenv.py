#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Set taskbot environment

import sys, os
pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../pycommons')
sys.path.insert(0, pycommons)

from Utils import *

def usage():
  print "usage %s CONFIG" % os.path.basename(sys.argv[0])

def main():

  if len(sys.argv) != 2:
    usage()
    exit(1)

  config = read_config(sys.argv[1])
  environment = config.get('environment', {})
  for var, value in environment.items():
    print "%s=%s" % (var, value)



if __name__ == "__main__":
  main()
