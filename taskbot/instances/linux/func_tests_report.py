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

FAILURE_REGEXP=r'\s+Failures:\s+\d+'
SKIPPED_REGEXP=r'\s+Skipped\scases:\s+\d+'
TESTCASE_COUNT_REGEXP=r'\[(\w+)\]\s+\w+\s+Total\stests\srun:\s(\d+)'
TESTCASE_REGEXP=r'(\w+)\.(\w+)'

def get_failed_text(tests):
  if tests:
    return "\n\nFailed tests:\n  " + "\n  ".join(map(lambda t: t.name, tests))
  else:
    return ""

def get_test_color(test):
  errs  = len(test.errors)
  skips = len(test.skipped)
  suite_stat = '(%d/%d/%d)' % (test.case_count, errs, skips)
  if test.failed or errs:
    return 'RED', 'FAIL %s' % suite_stat
  if len(test.skipped):
    return '#C4A000', 'SKIP %s' % suite_stat
  return 'GREEN', 'PASS %s' % suite_stat

def cases_to_table(cases, color, status):
  buff = ''
  for c in cases:
    buff += """<tr class="Linked">
      <td>%s</td>
      <td bgcolor="%s" align="center">%s</td>
      <td></td>
      <td></td>
      <td></td>
      </tr>""" % (c, color, status)
  return buff

def get_summary_row(title, total, errors, skipped):
  return """<tr>
      <td>%s</td>
      <td class="total">%d</td>
      <td class="pass">%d</td>
      <td class ="error">%d</td>
      <td class="skip">%d</td></tr>""" % (
         title, total,
         total - errors - skipped,
         errors, skipped)

class FTReport(Report):

  class TestResult:

    def __init__(self, name, task, logfile, failed, output):
      self.name = name
      self.task = task
      self.logfile = logfile and logfile[0] or None
      self.failed = failed
      self.skipped = []
      self.errors = []
      self.case_count = 0
      self.current_suite = None
      self.__parse_output(output)

    def __get_full_casename(self, casename):
      if self.current_suite:
        return "%s.%s" % (self.current_suite, casename)
      return casename
    

    def __append_errors(self, casename):
      name = self.__get_full_casename(casename)
      self.errors.append(name)

    def __append_skipped(self, casename):
      name = self.__get_full_casename(casename)
      self.skipped.append(name)

    def __parse_output(self, output):
      append_fn = None
      for line in output.split("\n"):
        if re.search(FAILURE_REGEXP, line):
          append_fn = self.__append_errors
        elif re.search(SKIPPED_REGEXP, line):
          append_fn = self.__append_skipped
        else:
          m = re.search(TESTCASE_REGEXP, line)
          if append_fn and m:
            suite, case = m.group(1,2)
            append_fn(case)
          else:
            m = re.search(TESTCASE_COUNT_REGEXP, line)
            if m:
              self.current_suite=m.group(1)
              self.case_count += int(m.group(2)) 

    def __str__(self):
      return "%s:\n  %s, %s" % (
        self.name,
        self.failed and 'FAIL' or 'PASS',
        self.logfile or 'Logfile not found')
    
    def __repr__(self):
      return self.__str__()

    def exec_time(self):
      return self.task.finish - self.task.start

  def __init__(self, config):
    Report.__init__(self, config)

  def _log(self, logfile):
    if logfile:
      return """<a href="%s">log</a>""" % self.file_href(logfile)
    return "-"
           
  def __generate__( self ):
    prev_run = self.get_previous_run()
    tasks = self.find_task('Run functional test > %run_func_tests.taskbot%')
    tests = self.find_task('Run tests > %while % > %', tasks)
    if not tests:
      print >> sys.stderr, "Cannot create func-tests report (func-tests task absent)" 
      return 1      
   
    history = 'Func tests'
    files = self.find_task('Store results > %file.py%', tasks)
    results = []
    for test in tests:
      testname = test.description
      log_filename = "%s.log" % testname
      ftest_run = self.find_task('%functest.py%', [test])
      results.append(
        self.TestResult(
          testname,
          ftest_run[0],
          self.find_files_by_name(files[0], log_filename),
          bool(self.find_failed(test)),
          self.get_stdout(ftest_run)))

      
    tests_report = "<h1>Func test results</h1>"

    # Summary table
    tests_report += """<table>
      <thead><tr>
      <th></th>
      <th>TOTAL</th>
      <th>PASS</th>
      <th>FAIL</th>
      <th>SKIP</th>
      </tr></thead><tbody>"""
    
    # Test units
    tests_report += get_summary_row(
      "Test units",
      len(results),
      len(filter(lambda x: x.failed, results)), 0)

    # Test cases
    tests_report += get_summary_row(
      "Test cases",
      sum(map(lambda x: x.case_count, results)),
      sum(map(lambda x: len(x.errors), results)),
      sum(map(lambda x: len(x.skipped), results)))

    tests_report += "</tbody></table>"

    # Test results
    if results:
      tests_report += "<br><br>"
      tests_report += """<table class="UTTable Expandable Zebra">
      <thead><tr>
      <th>Test name</th>
      <th>Status (TOTAL/FAIL/SKIP)</th>
      <th>Execution time</th>
      <th>Log</th>
      <th>Out</th>
      </tr></thead><tbody>"""
      for t in results:
        color, status = get_test_color(t)
        tests_report += """<tr>
          <td>%s</td>
          <td bgcolor="%s" align="center">%s</td>
          <td>%s</td>
          <td>%s</td>
          <td><a href="%s">out</a></td>
          </tr>""" % (t.name, color, status,
                      t.exec_time(),
                      self._log(t.logfile),
                      self.task_href(t.task))
        tests_report += cases_to_table(t.errors, 'RED', 'FAIL')
        tests_report += cases_to_table(t.skipped, '#C4A000', 'SKIP')
      tests_report += "</tbody></table>"
    tests_report_id = self.add_report(tests_report,
      views = {
        'css': ['/reports/styles/func_tests_report.css'],
        'js': ['/commons/scripts/ExpandableTable.js',
             '/commons/scripts/ZebraTable.js']})

    failures = filter(lambda t: t.failed or t.errors, results)

    if failures:
      color = '"RED"'
      history += """<br>FAIL: <a href="%s">%s</a>""" % \
        (self.report_href(tests_report_id), len(failures))
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
        get_failed_text(failures))
      
      
      
if __name__ == "__main__":
  sys.exit(FTReport(sys.argv[1]).generate())
