# -*- coding: utf-8 -*-
""" Database migration on version upgrade test.
Uses two servers, each of them starts with earlier version DB copy.
The DB copy contains some transactions with users, cameras, server settings and rules.
Checks if both servers start and merge their data correctly.
"""
__author__ = 'Danil Lavrentyuk'

import time
from functest_util import compareJson, checkResultsEqual
from testbase import FuncTestCase
import difflib

NUM_SERV=2
SERVERS_MERGE_WAIT=10

class DBUpgradeTest(FuncTestCase):

    num_serv = NUM_SERV
    _test_name = "DB Upgrade"
    _test_key = 'dbup'

    _suits = (
        ('DBUpgradeTest', [
            'CheckServerStart'
        ]),
    )

    _dbfiles = ['v2.4.1-box1.db', 'v2.4.1-box2.db']
    _ids = [
        '{62a54ada-e7c7-0d09-c41a-4ab5c1251db8}',
        '{88b807ab-0a0f-800e-e2c3-b640b31f3a1c}',
    ]

    def _init_script_args(self, boxnum):
        print "DEBUG: box %s, set id %s" % (boxnum, self._ids[boxnum])
        return (self._dbfiles[boxnum], self._ids[boxnum])

    def CheckServerStart(self):
        """
         Start both servers and check that their data are synchronized.
        """
        self._prepare_test_phase(self._stop_and_init)
        print "Wait %s seconds for server to upgrade DB and merge data..." % SERVERS_MERGE_WAIT
        time.sleep(SERVERS_MERGE_WAIT)
        print "Now check the data"
        func = 'ec2/getFullInfo?extraFormatting'
        answers = [self._server_request(n, func, unparsed=True) for n in xrange(self.num_serv)]
        diff = compareJson(answers[0][0], answers[1][0])
        if diff.hasDiff():
            ud = difflib.unified_diff(
                answers[0][1].splitlines(True),
                answers[1][1].splitlines(True),
                self.sl[0], self.sl[1], n=5)
            textdiff = ''.join(ud)
            self.fail("Servers responses on %s are different: %s\nTextual diff results:\n%s" % (func, diff.errorInfo(), textdiff))


