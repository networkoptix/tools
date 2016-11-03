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
from cStringIO import StringIO

MAX_OUTPUT_LINES = 500
FILE_IMAGE='/commons/images/file-icon.png'
ERROR_IMAGE='/commons/images/red.gif'
WARNING_IMAGE='/commons/images/yellow.gif'

class BuildReport(Report):

  OUTPUT_CLASS = [
    # Linux
    ( r':\d+:\d+:\s+(\S+\s+)?error:', 'error'),
    ( r':\d+:\d+:\s+warning:', 'warning'),
    # Windows
    ( r':\s+error\s[A-Z]+\d+\s:', 'error'),
    ( r':\s+warning\s[A-Z]+\d+\s:', 'warning'),
    # Common
    ( r'\[ERROR\]', 'error'),
    ( r'FAILURE', 'error'),
    ( r'\[WARNING\]', 'warning'),
    ( r'SKIPPED', 'warning'),
    ( r'SUCCESS', 'success') ]
      

  def __init__(self, config):
    Report.__init__(self, config)

  def __add_build_report(self, report_id, reports, report_html):
    html = """<div class="container">\n"""
    html+= """<header><h1>Build report</h1></header>"""
    html+= """<nav><ul>"""
    for name, image, ref in reports:
      html+= """<li><a href="%s"><img src="%s">%s</a></li>""" % (ref, image, name)
    html+= """</ul></nav>"""
    html+= """<div class="content">%s</div>""" % report_html
    html+= """</div>"""
    self.add_to_report(report_id, html)

  def __build_report( self, task ):
    full_log_link = "?stdout=%s&type=%s&raw" % (task.id, "text/plain")
    colored_report_id = self.add_report(views = {'css': ['/reports/styles/build_report.css']})
    errors_report_id = self.add_report(views = {'css': ['/reports/styles/build_report.css']})
    warnings_report_id = self.add_report(views = {'css': ['/reports/styles/build_report.css']})

    build_reports = [
      ('Full output', FILE_IMAGE, full_log_link),
      ('Parsed output', FILE_IMAGE, self.report_href(colored_report_id)),
      ('Errors', ERROR_IMAGE,  self.report_href(errors_report_id)),
      ('Warnings', WARNING_IMAGE,  self.report_href(warnings_report_id)) ]

    lines = self.get_stdout(task).split("\n")
    line_count=len(lines)
    line_number=last_warning=last_error=0
    colored_report = errors_report = warnings_report = ''
    colored_report = StringIO()

    def get_color_class(line):
      for exp, c in self.OUTPUT_CLASS:
        if re.search(exp, line):
          return c
      return None

    def append_colored_report(buffer, line, color_class):
      if line and not colored_report.tell():
        print >> buffer, "...<br>\n"
      if color_class and color_class == 'error':
        print >> buffer, line
        if line_number < line_count - MAX_OUTPUT_LINES:
          print >> buffer, "...<br>"
      elif line_number >= line_count - MAX_OUTPUT_LINES:
        print >> buffer, line
    
    for line in lines:
      color_class = get_color_class(line)
      rpt_line = "%s<br>\n" % line
      if color_class:
        rpt_line = """<span class="%s">%s</span><br>\n""" % (color_class, line)
        if color_class == 'error':
          if last_error and line_number - last_error > 1:
            errors_report  += """<span class="%s">...</span><br>\n""" % color_class
          errors_report  += rpt_line
          last_error = line_number
        elif color_class == 'warning':
          if last_warning and line_number - last_warning > 1:
            warnings_report += """<span class="%s">...</span><br>\n""" % color_class
          warnings_report += rpt_line
          last_warning = line_number
      append_colored_report(colored_report,
                            rpt_line, color_class)
      line_number+=1
    self.__add_build_report(colored_report_id, build_reports, colored_report.getvalue())
    self.__add_build_report(errors_report_id, build_reports, errors_report)
    self.__add_build_report(warnings_report_id, build_reports, warnings_report)
    colored_report.close()
    return self.report_href(colored_report_id)

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
      mvn_task = self.find_task('%mvn package%', [build])
      if mvn_task:
        task_href = self.__build_report(mvn_task[0])
      

    history = "<br>%s<br>" % desc
    history += "<a href=\"%s\">%s</a>" % (task_href, result)

    self.add_history(color, history)

    # eMail notification
    import EmailNotify
    prev_run = self.get_previous_run()
    prev_build = None
    while prev_run:
      prev_builds = self.find_task('Build product > %build.taskbot% > %', [prev_run])
      if prev_builds:
        prev_build = prev_builds[-1]
        break
      prev_run = self.get_previous_run(prev_run)
    if failed:
      error_msg = "The product is still failed to build."
      if not prev_build or \
         (prev_build and not self.find_failed(prev_build)):
       error_msg = "The product is no longer being built."
      EmailNotify.notify(
        self, prev_run, "build failed", error_msg)
    elif prev_build and self.find_failed(prev_build):
          EmailNotify.notify(
          self, prev_run, "success build",
          "The product built successfully.")
    
    return 0


if __name__ == "__main__":
  sys.exit(BuildReport(sys.argv[1]).generate())

