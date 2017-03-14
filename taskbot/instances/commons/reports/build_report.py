#!/usr/bin/env python
# $Id$
# Artem V. Nikitin
# Build report

import sys, re, os, string

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
    ( r':\s+error:', 'error'),
    ( r':\s+undefined reference to', 'error'),
    ( r'\s+Error\s+\d+', 'error'),
    ( r':\d+:\d+:\s+warning:', 'warning'),
    # Windows
    ( r':\s+(fatal\s)?error\s[A-Z]+\d+\s*:', 'error'),
    ( r':\s+warning\s[A-Z]+\d+\s*:', 'warning'),
    # Mac
    ( r'ERROR:', 'error'),
    # Common
    ( r'\[ERROR\]', 'error'),
    ( r'FAILURE', 'error'),
    ( r'\[WARNING\]', 'warning'),
    ( r'SKIPPED', 'warning'),
    ( r'SUCCESS', 'success') ]
      

  def __init__(self, config):
    Report.__init__(self, config, report_watchers='build_watchers')

  def __add_build_report(self, report_id, reports, report_html):
    html = """<div class="container">\n"""
    html+= """<header><h1>Build report</h1></header>"""
    html+= """<h3>Branch: {0}</h3>""".format(self.branch)
    html+= """<h3>Platform: {0}</h3>""".format(self.platform.desc())
    html+= """</header><br><br>"""
    html+= """<nav><ul>"""
    for name, image, ref in reports:
      html+= """<li><a href="{0}"><img src="{1}">{2}</a></li>""".format(ref, image, name)
    html+= """</ul></nav>"""
    html+= """<div class="content">{0}</div>""".format(report_html)
    html+= """</div>"""
    self.add_to_report(report_id, html)

  def __build_report( self, task ):
    full_log_link = "?stdout={0}&type={1}&raw".format(task.id, "text/plain")
    colored_report_id = self.add_root_report(views = {'css': ['/reports/styles/build_report.css']})
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
    errors_report = warnings_report = errors_text = ''
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
      rpt_line = "{0}<br>\n".format(line)
      if color_class:
        rpt_line = """<span class="{0}">{1}</span><br>\n""".format(color_class, line)
        if color_class == 'error':
          if last_error and line_number - last_error > 1:
            errors_report  += """<span class="{0}">...</span><br>\n""".format(color_class)
            errors_text += "...\n"
          errors_report  += rpt_line
          errors_text += "{0}\n".format(line)
          last_error = line_number
        elif color_class == 'warning':
          if last_warning and line_number - last_warning > 1:
            warnings_report += """<span class="{0}">...</span><br>\n""".format(color_class)
          warnings_report += rpt_line
          last_warning = line_number
      append_colored_report(colored_report,
                            rpt_line, color_class)
      line_number+=1
    self.__add_build_report(colored_report_id, build_reports, colored_report.getvalue())
    self.__add_build_report(errors_report_id, build_reports, errors_report)
    self.__add_build_report(warnings_report_id, build_reports, warnings_report)
    colored_report.close()
    return errors_text

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
    result = "OK"
    errors = ''
    if failed:
      color = '"RED"'
      errors = self.__build_report(failed)
      result = "FAILED"
    else:
      # Get mvn task
      mvn_task = self.find_task('%mvn package%', [build])
      if mvn_task:
        self.__build_report(mvn_task[0])
      else:
        # Add absent error report
        self.add_history('"RED"', "There is no build")
        print >> sys.stderr, "Cannot create build report (build task absent)" 
        return 1
      

    history = "<br>{0}<br>".format(desc)
    history += "<a href=\"{0}\">{1}</a>".format(self.href(), result)

    self.add_history(color, history)

    # eMail notification
    import EmailNotify
    prev_run = self.get_previous_run()
    prev_build = None
    def check_commit(commit):
      return commit.repo.name != 'devtools'
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
      if errors:
        error_msg += """\n\n{0}""".format(errors)
      EmailNotify.notify(
        self, prev_run, "build failed", error_msg,
        notify_filter = check_commit)
    elif prev_build and self.find_failed(prev_build):
          EmailNotify.notify(
          self, prev_run, "success build",
          "The product built successfully.",
          notify_filter = check_commit)
    
    return 0


if __name__ == "__main__":
  sys.exit(BuildReport(sys.argv[1]).generate())
