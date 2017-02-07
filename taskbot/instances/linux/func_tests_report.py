#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Functional tests report

import sys, os, re

pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../../pycommons')
sys.path.insert(0, pycommons)
import EmailNotify
from Report import Report

PASSED_REGEXP=r'(\d+)\s+passed'
FAILS_REGEXP=r'(\d+)\s+failed'
ERROR_REGEXP=r'(\d+)\s+error'

def get_counter(regexp, result_str):
    m = re.search(regexp, result_str)
    if m:
        return int(m.group(1))
    return 0


class FTReport(Report):

    class TestResult:

        def __init__(self, passed = 0, failed = 0, errors = 0):
            self.passed = passed
            self.failed = failed
            self.errors = errors

        @property
        def total(self):
            return self.passed + self.failed + self.errors

        @property
        def total_failed(self):
            return self.failed + self.errors
    
    def __init__(self, config):
        Report.__init__(self, config, report_watchers='ft_watchers')

    def _parse_output(self, output):
        result_line = output.split("\n")[-2]
        passed = get_counter(PASSED_REGEXP, result_line)
        errors = get_counter(FAILS_REGEXP, result_line)
        failed = get_counter(ERROR_REGEXP, result_line)
        return self.TestResult(passed, failed, errors)

    def _get_tests_results(self, prev_run = None):
        tasks = self.find_task('Run functional test > %run_func_tests.taskbot%', prev_run)
        if not tasks:
            return None
        tests = self.find_task('Run tests > %py.test%', tasks)
        if not tests:
            return None
        return self._parse_output(self.get_stdout(tests))

    def __generate__( self ):
        results = self._get_tests_results()
        if not results:
            print >> sys.stderr, "Cannot create func-tests report (func-tests task absent)" 
            return 1
        prev_run = self.get_previous_run()
        prev_results = self._get_tests_results([prev_run]) or self.TestResult()

        tasks = self.find_task('Run functional test > %run_func_tests.taskbot%')
        files = self.find_task('Store results > %file.py%', tasks)
        if not files:
            print >> sys.stderr, "Cannot create func-tests report (func-tests report isn't created)"

        print 'Files', files
        log_files = self.find_files_by_name(files[0], 'functest.html')
        if not log_files:
            print >> sys.stderr, "Cannot create func-tests report (func-tests report isn't created)"

        print log_files
        self.add_root_report(self.get_file_content(log_files[0]))

        history = 'Func tests'
        history += """<br>PASS/FAIL: <a href="%s">%d/%d</a>""" % \
                   (self.href(), results.passed, results.total_failed)
        
        
        if results.total_failed:
            color = '"RED"'
        else:
            color = '"GREEN"'

        self.add_history(color, history)

        
        if prev_run and not results.total_failed and prev_results.total_failed:
            EmailNotify.notify(
                self, prev_run, "func-tests fixed",
                "The product func-tests executed successfully.",
                notify_owner = False)
        elif results.total_failed:
            EmailNotify.notify(
                self, prev_run, "func-tests failed",
                "Fails detected in the func-tests.",
                notify_owner = False)

        return 0

if __name__ == "__main__":
    sys.exit(FTReport(sys.argv[1]).generate())
