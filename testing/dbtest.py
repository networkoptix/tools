# -*- coding: utf-8 -*-
""" Database migration on version upgrade test.
Uses two servers, each of them starts with earlier version DB copy.
The DB copy contains some transactions with users, cameras, server settings and rules.
Checks if both servers start and merge their data correctly.
"""
__author__ = 'Danil Lavrentyuk'

import time
from functest_util import compareJson, checkResultsEqual
#from testbase import FuncTestCase
from stortest import StorageBasedTest
import difflib

NUM_SERV=2
SERVERS_MERGE_WAIT=10
BACKUP_RESTORE_TIMEOUT=40


def _textdiff(data0, data1, src0, src1):
    ud = difflib.unified_diff(data0.splitlines(True), data1.splitlines(True), src0, src1, n=5)
    return ''.join(ud)

def _sleep(n):
    print "Sleep %s..." % n
    time.sleep(n)

class DBTest(StorageBasedTest):

    num_serv = NUM_SERV
    _test_name = "Database"
    _test_key = 'db'

    _suits = (
        ('DBTest', [
            'DBUpgradeTest',
            'BackupRestoreTest',
        ]),
    )

    _dbfiles = ['v2.4.1-box1.db', 'v2.4.1-box2.db']
    _ids = [
        '{62a54ada-e7c7-0d09-c41a-4ab5c1251db8}',
        '{88b807ab-0a0f-800e-e2c3-b640b31f3a1c}',
    ]

    @classmethod
    def _global_clear_extra_args(cls, num):
        return ()

    def _init_script_args(self, boxnum):
        print "DEBUG: box %s, set id %s" % (boxnum, self._ids[boxnum])
        return (self._dbfiles[boxnum], self._ids[boxnum])

    def DBUpgradeTest(self):
        """ Start both servers and check that their data are synchronized. """
        self._prepare_test_phase(self._stop_and_init)
        print "Wait %s seconds for server to upgrade DB and merge data..." % SERVERS_MERGE_WAIT
        time.sleep(SERVERS_MERGE_WAIT)
        print "Now check the data"
        func = 'ec2/getFullInfo?extraFormatting'
        answers = [self._server_request(n, func, unparsed=True) for n in xrange(self.num_serv)]
        diff = compareJson(answers[0][0], answers[1][0])
        if diff.hasDiff():
            textdiff = _textdiff(answers[0][1], answers[1][1], self.sl[0], self.sl[1])
            self.fail("Servers responses on %s are different: %s\nTextual diff results:\n%s" % (func, diff.errorInfo(), textdiff))

    def BackupRestoreTest(self):
        """ Check if backup/restore preserve all necessary data. """
        getInfoFunc = 'ec2/getFullInfo?extraFormatting'
        fulldataBefore = self._server_request(0, getInfoFunc, unparsed=True)
        with open("data-before", "w") as f:
            print >>f, fulldataBefore[1]
        resp = self._server_request(0, 'ec2/dumpDatabase?format=json')
        #print "DEBUG: Returned data size: %s" % len(resp['data'])
        backup = resp['data']
        _sleep(15)
        # Now change DB data -- add a camera
        #self._add_test_camera(0)
        #_sleep(15)
        #
        self._server_request(0, 'ec2/restoreDatabase', data={'data': backup})
        save_guids = self.guids[:]
        _sleep(15)
        self._wait_servers_up()
        self.assertSequenceEqual(save_guids, self.guids,
            "Server guids have changed after restore: %s -> %s" % (save_guids, self.guids))
        _sleep(5)
        start = time.time()
        stop = start + BACKUP_RESTORE_TIMEOUT
        cnt = 1
        while True:
            fulldataAfter = self._server_request(0, getInfoFunc, unparsed=True)
            diff = compareJson(fulldataBefore[0], fulldataAfter[0])
            if diff.hasDiff() and time.time() < stop:
                print "Try %d failed" % cnt
                cnt += 1
                time.sleep(1)
                continue
            break
        with open("data-after", "w") as f:
            print >>f, fulldataAfter[1]
        if diff.hasDiff():
            print "DEBUG: compareJson has found differences: %s" % (diff.errorInfo(),)
            textdiff = _textdiff(fulldataBefore[1], fulldataAfter[1], "Before", "After")
            self.fail("Servers responses on %s are different:\n%s" % (getInfoFunc, textdiff))
        else:
            print "Success after %.1f seconds" % (time.time() - start,)
