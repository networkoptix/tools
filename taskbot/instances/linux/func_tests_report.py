#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Functional tests report

import sys, os, re, cgi
pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../../pycommons')
sys.path.insert(0, pycommons)
from Report import Report

TEST_START_MARKERS = [
  r'^(FAIL|ERROR):\s+(\w+)\s+\(([^\)]+)\)$']

TEST_STOP_MARKERS = [ r'^-+$', r'^=+$' ]

def get_failed_text(tests):
  if tests:
    return "\n\nFailed tests:\n  " + "\n  ".join(map(lambda t: t.name, tests))
  else:
    return ""

class FTReport(Report):

  class TestResult:

    def __init__(self, name, etype, error = ''):
      self.name = name
      self.error = error
      self.etype = etype

    def __str__(self):
      return "%s:\n  %s" % (self.name, self.error)
    
    def __repr__(self):
      return self.__str__()

  def __init__(self, config):
    Report.__init__(self, config)

  def _parse_output(self, output):
    results = []
    stop_marker = 0
    result = None
    for line in output.split("\n"):
      if result:
        result.error+="\n" + line
        for exp in TEST_STOP_MARKERS:
          if re.search(exp, line):
            stop_marker += 1
          if stop_marker == 2:
            stop_marker = 0
            results.append(result)
            result = None
      for exp in TEST_START_MARKERS:
        m = re.search(exp, line)
        if m:
          etype, case, test = m.group(1,2,3)
          result = self.TestResult("%s.%s" % (test, case), etype, line)
          break
    return results

  def _error(self, error):
    error_report = '<br>\n'.join(map(cgi.escape, error.split("\n")))
    return self.report_href(self.add_report(error_report))
           
  def __generate__( self ):
    prev_run = self.get_previous_run()
    tasks = self.find_task('Run functional test > %run_func_tests.taskbot%')
    if not tasks:
      print >> sys.stderr, "Cannot create func-tests report (func-tests task absent)" 
      return 1      
    tests = self.find_task('Run tests > % > FuncTests > %', tasks)
    history = 'Func tests'
    tests_report = "<h1>Func test results</h1>"
    results = []
    failed = self.find_failed(tasks[-1])
    log_name = "FuncTests"
    if failed:
      log_href = self.task_href(failed)
      parent_task = self.find_non_command_parent(failed)
      print parent_task
      if not parent_task.is_command:
        log_name = parent_task.description
    if tests:
      if not failed:    
        log_href = self.task_href(tests[-1])
      output = self.get_stdout(tests)
      results = self._parse_output(output)
    
    tests_report += """<br>Full output: <a href="%s">%s</a><br>\n<br>\n""" % \
      (log_href, log_name)
      
    if results:
      tests_report += """<table class="tests_table">
      <tr>
      <th>Test name</th>
      <th>Status</th>
      <th>Error</th>
      </tr>"""
      for t in results:
        error_report_id = self.add_report(t.error)
        tests_report += """<tr>
          <td class="test_name">%s</td>
          <td class="test_status" bgcolor="RED">%s</td>
          <td><a href="%s">error</a></td>
          </tr>""" % (t.name, t.etype, self._error(t.error))
      tests_report += "</table>"
    tests_report_id = self.add_report(tests_report)

    if results or failed:
      color = '"RED"'
      history += """<br>FAIL: <a href="%s">%d</a>""" % \
        (self.report_href(tests_report_id), len(results))
    else:
      color = '"GREEN"'
      history += """<br><a href="%s">PASS</a>""" % \
        (self.report_href(tests_report_id))

    self.add_history(color, history)
    
    import EmailNotify
    if results or failed:
      EmailNotify.notify(
        self, prev_run, "func-tests failed",
        "Fails detected in the func-tests.%s" %
        get_failed_text(results))
      
      
      
if __name__ == "__main__":
  sys.exit(FTReport(sys.argv[1]).generate())
