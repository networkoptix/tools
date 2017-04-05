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

class EmptyReport(Report):

  def __init__(self, config, task_id):
    Report.__init__(self, config, link_task_id=task_id)

  def __generate__( self ):
      self.add_history(None, '')

if __name__ == "__main__":
  sys.exit(EmptyReport(sys.argv[1], int(sys.argv[2])).generate())
