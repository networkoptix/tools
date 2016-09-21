#!/usr/bin/env python
# $Id$
# Artem V. Nikitin

import sys
sys.path.insert(0, '../../pycommons')
from Report import Report

class BuildReport(Report):

  def __init__(self, config):
    Report.__init__(self, config)

  def __generate__( self ):
    build_tasks = self.find_task('Build product > %build.taskbot% > %')

    if len(build_tasks) == 0:
      # Add absent error report
      report.add_history('"RED"', "There is no build")
      print >> sys.stderr, "Cannot create build report (build task absent)" 
      return 1

    build = build_tasks[-1]
    failed = self.find_failed(build);

    color = '"GREEN"';
    desc = build.description
    task_href = self.task_href(build)
    result = "OK"
    if failed:
      color = '"RED"'
      task_href = self.task_href(failed)
      result = "FAILED"

    history = "Media server<br>%s<br>" % desc
    history += "<a href=\"%s\">%s</a>" % (task_href, result)

    self.add_history(color, history)

    # eMail notification

    if failed:
      import EmailNotify
      prev_run = self.get_previous_run()
      prev_build = None
      while prev_run:
        prev_builds = self.find_task('Build product > %build.taskbot% > %', [prev_run])
        if prev_builds:
          prev_build = prev_builds[-1]
          break
        prev_run = self.get_previous_run(prev_run)

      print prev_build, prev_run
      if (prev_build and not self.find_failed(prev_build)):
        EmailNotify.notify(
          self, prev_run, "build failed",
          "The product is no longer builded.", debug=True)
    
    return 0


if __name__ == "__main__":
  sys.exit(BuildReport(sys.argv[1]).generate())

