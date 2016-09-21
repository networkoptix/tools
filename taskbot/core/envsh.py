#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Run taskbot script in the configured environment

import sys, subprocess
pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../pycommons')
sys.path.insert(0, pycommons)
from Utils import *

def usage():
  print "usage %s CONFIG SCRIPT" % os.path.basename(sys.argv[0])

def main():

  if len(sys.argv) != 3:
    usage()
    exit(1)

  config = sys.argv[1]
  script = sys.argv[2]

  config = read_config(config)
  init_environment(config)

  shell = config.get('sh'),

  if (shell):
    p = subprocess.Popen(
      [shell, script],
      shell = False,
      stdout = subprocess.PIPE,
      stderr = subprocess.PIPE)

    (out, err) = p.communicate()

    print >> sys.stdout, out
    print >> sys.stderr, err   

    exit(p.returncode)
  else:
    print >> sys.stderr, "Shell configuration 'config.sh' absent"
    exit(1)

if __name__ == "__main__":
  main()


