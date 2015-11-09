__author__ = 'Danil Lavrentyuk'
__author__ = 'Danil Lavrentyuk'
import urllib2
import unittest
import subprocess
import traceback
import time
import os
import json
import socket
import struct

from functest_util import ClusterLongWorker, SafeJsonLoads, get_server_guid
from testboxes import *

_NUM_SERV=1

TEST_CAMERA_ID = "f9c03047-72f1-4c04-a929-8538343b6642"

TEST_CAMERA_DATA = {
    'mac': '11:22:33:44:55:66',
    'physicalId': '11:22:33:44:55:66',
    'manuallyAdded': False,
    'model': 'test-camera',
    'groupId': '',
    'groupName': '',
    'statusFlags': '',
    'vendor': 'test-v',
    'id': '', #TODO generate: any globally unique id
    'parentId': '',#TODO put the server guid here
    'name': 'test-camera',
    'url': '192.168.109.63',
    'typeId': TEST_CAMERA_ID
}

class BackupStorageTestError(FuncTestError):
    pass

class BackupStorageTest(FuncTestCase):
    num_serv = _NUM_SERV # override
    _storages = dict()

    _suits = (
        ('BackupStartTests', [
            'InitialRestart',
            'AddStorageTest'
        ]),
    )

    def _get_init_script(self, boxnum):
        return ('/vagrant/bs_init.sh',)

    @classmethod
    def setUpClass(cls):
        print "========================================="
        print "TimeSync Test Start: %s" % cls.testset
        super(BackupStorageTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(BackupStorageTest, cls).tearDownClass()
        print "Backup Storage Test End"
        print "========================================="

    ################################################################

    def _load_storage_info(self):
        for num in xrange(self.num_serv):
            url = "http://%s/api/storageSpace" % self.sl[num]
            try:
                response = urllib2.urlopen(url)
            except Exception, e:
                self.fail("%s request failed with exception: %s" % (url, traceback.format_exc()))
            self.assertEqual(response.getcode(), 200, "%s request returns code %d" % (url, response.getcode()))
            jresp = SafeJsonLoads(response.read(), self.sl[num], 'api/storageSpace')
            response.close()
            self._storages[num] = [s for s in jresp["reply"]["storages"] if s['storageType'] == 'local']
            print "[DEBUG] Storages found:"
            for s in self._storages[num]:
                print "%s: %s" % (s['storageId'], s['url'])

    ################################################################

    def InitialRestart(self):
        "Just a re-initialization with clear db."
        self._prepare_test_phase(self._stop_and_init)
        self._load_storage_info()

    def AddStorageTest(self):
        pass
