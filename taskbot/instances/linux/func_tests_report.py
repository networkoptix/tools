#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Functional tests report

import sys, os
pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../../../pycommons')
sys.path.insert(0, pycommons)
from Report import Report

class FTReport(Report):

  def __init__(self, config):
    Report.__init__(self, config)

  def __generate__( self ):
    return 0

if __name__ == "__main__":
  sys.exit(FTReport(sys.argv[1]).generate())




