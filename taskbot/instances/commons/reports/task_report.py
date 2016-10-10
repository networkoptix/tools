#!/usr/bin/env python
# $Id$
# Artem V. Nikitin
# Task report

import os, sys

pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../../../pycommons')
sys.path.insert(0, pycommons)
from Report import Report

class TaskReport(Report):
  
  def __init__(self, config):
    Report.__init__(self, config)

  def __generate__( self ):
    print self.__root_task__.id
    return 0
if __name__ == "__main__":
  sys.exit(TaskReport(sys.argv[1]).generate())

