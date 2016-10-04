#!/usr/bin/env python
# $Id$
# Artem V. Nikitin
# Build report

import sys, re
sys.path.insert(0, '../../pycommons')
from Report import Report

MAX_OUTPUT_LINES = 2000

class BuildReport(Report):

  OUTPUT_CLASS = [
    ( r'\[ERROR\]', 'error'),
    ( r'FAILURE', 'error'),
    ( r'\[WARNING\]', 'warning'),
    ( r'SKIPPED', 'warning'),
    ( r'SUCCESS', 'success') ]
      

  def __init__(self, config):
    Report.__init__(self, config)

  def __build_report( self, task ):
    full_log_link = "?stdout=%s&type=%s&raw" % (task.id, "text/plain")
    build_report = """<a href="%s">Full log</a><br>\n<br>\n""" % full_log_link
    lines = self.get_stdout(task).split("\n")[-MAX_OUTPUT_LINES:]
    def color_line(l):
      for exp, c in self.OUTPUT_CLASS:
        if re.search(exp, l):
          return """<span class="%s">%s</span>""" % (c, l)
      return l
      
    build_report += '<br>\n'.join(map(color_line, lines))
    build_report_id = self.add_report(build_report, {'css': ['/reports/styles/ColoredOutput.css']})
    return self.report_href(build_report_id)

  def __generate__( self ):
    build_tasks = self.find_task('Build product > %build.taskbot% > %')

    if len(build_tasks) == 0:
      # Add absent error report
      self.add_history('"RED"', "There is no build")
      print >> sys.stderr, "Cannot create build report (build task absent)" 
      return 1

    build = build_tasks[-1]
    failed = self.find_failed(build)

    color = '"GREEN"';
    desc = build.description
    task_href = self.task_href(build)
    result = "OK"
    if failed:
      color = '"RED"'
      task_href = self.__build_report(failed)
      result = "FAILED"
    else:
      # Get mvn task
      mvn_task = self.find_task('%mvn package%', build_tasks)
      if mvn_task:
        task_href = self.__build_report(mvn_task[0])
      

    history = "<br>%s<br>" % desc
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

      print prev_build, prev_run, self.find_failed(prev_build)
      if (prev_build and not self.find_failed(prev_build)):
        print "Send email notification!"
        EmailNotify.notify(
          self, prev_run, "build failed",
          "The product is no longer being built.")
    
    return 0


if __name__ == "__main__":
  sys.exit(BuildReport(sys.argv[1]).generate())

