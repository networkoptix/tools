#!/usr/bin/env python
# $Id$
# Artem V. Nikitin
# Build report

import sys, re, os

pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../../../pycommons')
sys.path.insert(0, pycommons)
from Report import Report

MAX_OUTPUT_LINES = 500

class BuildReport(Report):

  OUTPUT_CLASS = [
    ( r'\[ERROR\]', 'error'),
    ( r'FAILURE', 'error'),
    ( r':\d+:\d+:\s+error:', 'error'),
    ( r':\s+error\s[A-Z]+\d+\s:', 'error'),
    ( r'\[WARNING\]', 'warning'),
    ( r':\d+:\d+:\s+warning:', 'warning'),
    ( r':\s+warning\s[A-Z]+\d+\s:', 'warning'),
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
    import EmailNotify
    if failed:
      prev_run = self.get_previous_run()
      prev_build = None
      while prev_run:
        prev_builds = self.find_task('Build product > %build.taskbot% > %', [prev_run])
        if prev_builds:
          prev_build = prev_builds[-1]
          break
        prev_run = self.get_previous_run(prev_run)

      error_msg = "The product is still failed to build."
      if not prev_build or \
         (prev_build and not self.find_failed(prev_build)):
       error_msg = "The product is no longer being built."
      EmailNotify.notify(
        self, prev_run, "build failed", error_msg)
    elif prev_build and self.find_failed(prev_build)):
          EmailNotify.notify(
          self, prev_run, "success build",
          "The product built successfully.")
    
    return 0


if __name__ == "__main__":
  sys.exit(BuildReport(sys.argv[1]).generate())

