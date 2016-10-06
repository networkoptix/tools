#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Unit tests report

import sys, urllib, os
from collections import OrderedDict
pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../../../pycommons')
sys.path.insert(0, pycommons)
from Report import Report

def get_totals(unit_tests):
  total_fail = len(filter(
    lambda x: x.failed, unit_tests.values()))
  return len(unit_tests) - total_fail, total_fail

def get_diff(current, prev):
  passed = failed = 0
  for name, info in current.items():
    prev_info = prev.get(name)
    passed+=int((prev_info and prev_info.failed and not info.failed) or \
      (not prev_info and not info.failed))
    failed+=int((prev_info and not prev_info.failed and info.failed) or \
      (not prev_info and info.failed))
  return passed, failed

class UTReport(Report):

  class TestInfo:

    def __init__(self, task, failed):
      self.task = task
      self.failed = failed
      self.xml = None

    def status_and_color(self, prev):
      if self.failed:
        if prev and prev.failed:
          return "FAILED", "RED"
        return "NEW FAIL", "#C25A7C"
      else:
        if prev and not prev.failed:
          return "PASSED", "GREEN"
        return "NEW PASS", "LIGHTGREEN"

    def exec_time(self):
      return self.task.finish - self.task.start

  def __init__(self, config):
    Report.__init__(self, config)

  def __get_test_info(self, prev_run = []):
    unit_tests = {}
    tasks = self.find_task('Run unit tests > %run_unit_tests.taskbot%', prev_run)
    if len(tasks) == 0:
      return None
    run_tests = self.find_task('Run tests > %for % > %', tasks)
    test_results = self.find_task('Store results > %for % > %', tasks)
    for test in run_tests:
      unit_tests[test.description] = \
         UTReport.TestInfo(
           self.find_task("%", [test])[0],
           bool(self.find_failed(test)))
    for test in test_results:
      t = unit_tests.get(test.description)
      command = self.find_task('%.xml', [test])
      if t:
        t.xml = """<?xml-stylesheet type='text/xsl' href='\commons\styles\unit_tests.xsl'?>\n""" + \
          "\n".join(self.get_stdout(command).split("\n")[1:])
      else:
        print >> sys.stderr, "Cannot find results for test '%s'" % \
           test.description
    return unit_tests

  def _details(self, info):
    if info.xml:
      xml_report_id = self.add_report(info.xml)
      report_link = "?report=%s&type=%s&raw" % \
         (xml_report_id, urllib.quote("text/xml"))
      return """<a href="%s">details</a>""" % report_link
    else:
      return "-"

  def __generate__( self ):
    
    unit_tests = self.__get_test_info()

    if not unit_tests:
      print >> sys.stderr, "Cannot create unit-tests report (unit-tests task absent)" 
      return 1

    # Get previous tests result
    prev_run = self.get_previous_run()
    unit_tests_prev = {}
    if prev_run:
      unit_tests_prev = self.__get_test_info([prev_run])
    
    history = 'Unit tests'
    
    total_pass, total_fail = get_totals(unit_tests)
    new_pass, new_fail = get_diff(unit_tests, unit_tests_prev)

    tests_report = "<h1>Unit test results</h1>"
    tests_report += """<table class="tests_table">
    <tr>
    <th>Test name</th>
    <th>Status</th>
    <th>Execution time</th>
    <th>Details</th>
    <th>Log</th>
    </tr>"""

    for name, info in OrderedDict(sorted(unit_tests.items())).iteritems():
      status, color = \
         info.status_and_color(unit_tests_prev.get(name))
      tests_report += """<tr>
        <td class="test_name">%s</td>
        <td class="test_status" bgcolor="%s">%s</td>
        <td class="test_exec_time">%s</td>
        <td>%s</td>
        <td><a href="%s">log</a></td>
      </tr>""" % (name,  color, status,
                  info.exec_time(),
                  self._details(info),
                  self.task_href(info.task))
      
    tests_report += "</table>"

    tests_report_id = self.add_report(tests_report);

    color = '"GREEN"'
    if total_fail:
      color = '"RED"'
    history += """<br>PASS/FAIL: 
      <a href="%s">
      %d/%d (%d/%d)
      </a>""" % (self.report_href(tests_report_id),
                 total_pass, total_fail,
                 new_pass,
                 new_fail)
      
    self.add_history(color, history)

    if prev_run and new_fail:
      print "Send email notification!"
      import EmailNotify
      EmailNotify.notify(
        self, prev_run, "unit-tests failed",
        "New fails detected in the unit-tests.")

    return 0
   
if __name__ == "__main__":
  sys.exit(UTReport(sys.argv[1]).generate())
