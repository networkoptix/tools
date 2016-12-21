#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Unit tests report

import sys, urllib, os, re
from collections import OrderedDict
pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../../../pycommons')
sys.path.insert(0, pycommons)
from Report import Report

# Colors
FAIL_COLOR = "RED"
NEW_FAIL_COLOR = "#C25A7C"
PASSED_COLOR = "GREEN"
NEW_PASSED_COLOR = "LIGHTGREEN"

# Statuses
FAIL_STATUS = "FAIL"
PASS_STATUS = "PASS"
TERM_STATUS = "TERM"

def get_failed(unit_tests):
  return filter(
    lambda x: x[1].failed, unit_tests.items())

def get_failed_cases(test):
  return filter(
    lambda tc: tc[1].status != PASS_STATUS, test.testcases.items())

def get_totals(unit_tests):
  total_fail = len(get_failed(unit_tests))
  return len(unit_tests) - total_fail, total_fail

def get_diff(current, prev):
  passed = failed = 0
  for name, info in current.items():
    prev_info = None
    if prev:
      prev_info = prev.get(name)
    passed+=int((prev_info and prev_info.failed and not info.failed) or \
      (not prev_info and not info.failed))
    failed+=int((prev_info and not prev_info.failed and info.failed) or \
      (not prev_info and info.failed))
  return passed, failed

def get_failed_text(tests):
  if tests:
    buf = "\n\nFailed tests:"
    for name, info in tests.iteritems():
      buf+="\n  %s" % name
      if info.testcases:
        fails = map(lambda x: x[0], get_failed_cases(info))
        fails.sort()
        buf+="\n    " + "\n    ".join(fails)
    return buf

def get_summary_row(title, total, fails):
  return """<tr>
      <td>%s</td>
      <td class="total">%d</td>
      <td class="pass">%d</td>
      <td class ="error">%d</td></tr>""" % (
         title, total, total - fails, fails)

class UTReport(Report):

  class TestCase:

    def __init__(self, status, error, exec_time):
      self.status = status
      self.error = error
      self.exec_time = exec_time

    def status_and_color(self, prev):
      if self.status != PASS_STATUS :
        if prev and prev.status != PASS_STATUS:
          return self.status, FAIL_COLOR
        return "NEW " + self.status, NEW_FAIL_COLOR
      else:
        if prev and prev.status == PASS_STATUS:
          return self.status, PASSED_COLOR
        return "NEW " + self.status, NEW_PASSED_COLOR

    def get_error(self, report):
      if self.error:
        error_report_id = report.add_report(self.error)
        return """<a href="%s">log</a>""" % report.report_href(error_report_id)
      return "-"

  class TestInfo:

    def __init__(self, task, failed, output):
      self.task = task
      self.failed = failed
      self.testcases = {}
      if output:
        self.__parse_output(output)

    def __add_case(self, m):
      name = "%s.%s" % m.group(1,2)
      self.testcases[name] = UTReport.TestCase(TERM_STATUS, "", 0)
      return self.testcases[name]

    def __set_pass(self, m):
      name = "%s.%s" % m.group(1,2)
      assert self.testcases.get(name)
      self.testcases[name].status = PASS_STATUS
      self.testcases[name].exec_time = float(m.group(3)) / 1000
      return None

    def __set_fail(self, m):
      name = "%s.%s" % m.group(1,2)
      assert self.testcases.get(name)
      self.testcases[name].status = FAIL_STATUS
      self.testcases[name].exec_time = float(m.group(3)) / 1000
      return None
      
    def __parse_output(self, output):
      RE_FN = [
        (r'\[\s+RUN\s+\]\s+(\w+)\.(\w+)', self.__add_case ),
        (r'\[\s+OK\s+\]\s+(\w+)\.(\w+)\s+\((\d+)\s+ms\)', self.__set_pass),
        (r'\[\s+FAILED \s+\]\s+(\w+)\.(\w+)\s+\((\d+)\s+ms\)', self.__set_fail) ]
      
      current_case = None
      for line in output.split("\n"):
        re_matched = False
        for r, fn in RE_FN:
          m = re.search(r, line)
          if m:
            current_case = fn(m)
            re_matched = True
            break
        if current_case and not re_matched and line:
          current_case.error+="%s<br>\n" % line

    def status_and_color(self, prev):
      fails = len(get_failed_cases(self))
      cases = len(self.testcases)
      stats =  " (%d/%d)" % (cases, fails)
      if self.failed:
        status = FAIL_STATUS + stats
        if prev and prev.failed:
          return status, FAIL_COLOR
        return "NEW " + status, NEW_FAIL_COLOR
      else:
        status = PASS_STATUS + stats
        if prev and not prev.failed:
          return status, PASSED_COLOR
        return "NEW " + status, NEW_PASSED_COLOR

    def exec_time(self):
      return self.task.finish - self.task.start

  def __init__(self, config):
    Report.__init__(self, config, report_watchers='ut_watchers')

  def __get_test_info(self, prev_run = []):
    tasks = self.find_task('Run unit tests > %run_unit_tests.taskbot%', prev_run)
    if len(tasks) == 0:
      return {}
    unit_tests = {}
    run_tests = self.find_task('Run tests > %for % > %', tasks)
    for test in run_tests:
      test_task = self.find_task("%", [test])[0]
      if test_task:
        unit_tests[test.description] = \
          UTReport.TestInfo(
            test_task,
            bool(self.find_failed(test)),
            self.get_stdout(test_task))
    return unit_tests

  def __get_cores_cell(self, task, name):
    result = []
    if task:
      cores = self.find_task('% > %Examine core file% > %', [task])
      for core in cores:
        for line in self.get_stdout(core).split("\n"):
          regex = r'Core\swas\sgenerated\sby\W+%s' % name
          if re.search(regex, line):
            result.append(core)
            break
    return " ".join(
      map(lambda c: """<a href="%s">%s</a>""" % \
          (self.task_href(c),
           self.find_non_command_parent(c, 1).description), result))
      
  def __get_cores(self):
    tests = self.find_task('Run unit tests > %run_unit_tests.taskbot%')
    cores_task = self.find_task(
      'Process core files > % > %for %', tests)
    if cores_task:
      cores =  self.find_task('%', cores_task)
      cores_count = len(cores)
      return cores_count, cores_task[0]
    return 0, None

  def __generate__( self ):
    unit_tests = self.__get_test_info()

    if not unit_tests:
      print >> sys.stderr, "Cannot create unit-tests report (unit-tests task absent)" 
      return 1

    cores_count, cores_task = self.__get_cores()

    # Get previous tests result
    prev_run = self.get_previous_run()
    unit_tests_prev = {}
    if prev_run:
      unit_tests_prev = self.__get_test_info([prev_run])
    
    history = 'Unit tests'
    
    total_pass, total_fail = get_totals(unit_tests)
    new_pass, new_fail = get_diff(unit_tests, unit_tests_prev)

    tests_report = "<header><h1>Unit test results</h1>"
    tests_report+= """<h3>Branch: %s</h3>""" % self.branch
    tests_report+= """<h3>Platform: %s</h4>""" % self.platform.desc()
    tests_report+= """</header><br><br>"""

    # Summary table
    tests_report += """<table>
      <thead><tr>
      <th></th>
      <th>TOTAL</th>
      <th>PASS</th>
      <th>FAIL(ERROR)</th>
      </tr></thead><tbody>"""

    tests_report += get_summary_row('Test units', len(unit_tests), total_fail)
    tests_report += get_summary_row('Test cases',
       sum(map(lambda x: len(x.testcases), unit_tests.values())),
       sum(map(lambda x: len(get_failed_cases(x)), unit_tests.values())))
    
    tests_report += "</tbody></table><br><br>"
 
    # Test results
    tests_report += """<table class="UTTable Expandable Zebra">
    <tr>
    <th>Test name</th>
    <th>Status (TOTAL/FAIL)</th>
    <th>Execution time</th>
    <th>Log</th>
    <th>Cores</th>
    </tr>"""

    for name, info in OrderedDict(sorted(unit_tests.items())).iteritems():
      prev_test_result = unit_tests_prev.get(name)
      status, color = \
         info.status_and_color(prev_test_result)
      tests_report += """<tr>
        <td>%s</td>
        <td bgcolor="%s" align="center">%s</td>
        <td>%s</td>
        <td><a href="%s">log</a></td>
        <td>%s</td>
        </tr>""" % (name,  color, status,
                  info.exec_time(),
                  self.task_href(info.task),
                  self.__get_cores_cell(cores_task, name))
      for case_name, case_info in OrderedDict(sorted(get_failed_cases(info))).iteritems():
        prev_test_cases = {}
        if prev_test_result:
          prev_test_cases = prev_test_result.testcases
        case_status, case_color = \
          case_info.status_and_color(prev_test_cases.get(case_name))

        exec_time = "%s" % case_info.exec_time
        if case_info.status == TERM_STATUS:
          exec_time = "-"

        tests_report += """<tr class="Linked">
        <td>%s</td>
        <td bgcolor="%s" align="center">%s</td>
        <td>%s</td>
        <td>%s</td>
        <td></td>
        </tr>""" % (case_name,  case_color, case_status,
           exec_time, case_info.get_error(self))
      
    tests_report += "</table>"

    self.add_root_report(
      tests_report,
      views = {
      'css': ['/reports/styles/func_tests_report.css'],
      'js': ['/commons/scripts/ExpandableTable.js',
             '/commons/scripts/ZebraTable.js']})

    color = '"GREEN"'
    if total_fail or cores_count:
      color = '"RED"'
    cores_link = ""
    if cores_count:
      cores_link ="""<br>core files: <a href="%s">%d</a>""" % \
        (self.task_href(cores_task), cores_count)
    history += """<br>PASS/FAIL: 
      <a href="%s">
      %d/%d (%d/%d)
      </a>%s""" % (self.href(),
                 total_pass, total_fail,
                 new_pass, new_fail,
                 cores_link)
      
    self.add_history(color, history)

    failed_tests = OrderedDict(sorted(get_failed(unit_tests)))

    import EmailNotify
    if prev_run and not total_fail and new_pass:
      EmailNotify.notify(
        self, prev_run, "unit-tests fixed",
        "The product unit-tests executed successfully.")
    elif cores_count:
      EmailNotify.notify(
        self, prev_run, "unit-tests failed",
        "%d core(s) detected after the unit-tests.%s" % \
        (cores_count, get_failed_text(failed_tests)))
    elif total_fail:
      EmailNotify.notify(
        self, prev_run, "unit-tests failed",
        "Fails detected in the unit-tests.%s" %
        get_failed_text(failed_tests))
    return 0
   
if __name__ == "__main__":
  sys.exit(UTReport(sys.argv[1]).generate())
