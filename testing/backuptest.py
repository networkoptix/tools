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
import uuid

import pprint

from functest_util import ClusterLongWorker, get_server_guid, unquote_guid
from testboxes import *

_NUM_SERV = 1
_WORK_HOST = 0

TEST_CAMERA_ID = "f9c03047-72f1-4c04-a929-8538343b6642"

TEST_CAMERA_DATA = {
    'id': '',
    'parentId': '',# put the server guid here
    'mac': '11:22:33:44:55:66',
    'physicalId': '11:22:33:44:55:66',
    'manuallyAdded': False,
    'model': 'test-camera',
    'groupId': '',
    'groupName': '',
    'statusFlags': '',
    'vendor': 'test-v',
    'name': 'test-camera',
    'url': '192.168.109.63',
    'typeId': TEST_CAMERA_ID
}
TEST_CAMERA_ATTR = {
    'cameraID': '',
    'scheduleEnabled': True,
    'backupType': "CameraBackup_HighQuality|CameraBackup_LowQuality",  # or CameraBackupBoth
    'cameraName': 'test-camera',
    'userDefinedGroupName': '',
    'licenseUsed': '',
    'motionType': '',
    'motionMask': '',
    'scheduleTasks': '',
    'audioEnabled': '',
    'secondaryStreamQuality': '',
    'controlEnabled': '',
    'dewarpingParams': '',
    'minArchiveDays': '',
    'maxArchiveDays': '',
    'preferedServerId': '',
    'failoverPriority': ''
}

TMP_STORAGE = '/tmp/bstorage'

class BackupStorageTestError(FuncTestError):
    pass

class BackupStorageTest(FuncTestCase):
    num_serv_t = _NUM_SERV
    _storages = dict()

    _suits = (
        ('BackupStartTests', [
            'InitialRestart',
            'AddStorageTest',
            'StartBackupTest',
        ]),
    )

    def _get_init_script(self, boxnum):
        return ('/vagrant/bs_init.sh',)

    @classmethod
    def setUpClass(cls):
        print "========================================="
        print "Backup Storage Test Start: %s" % cls.testset
        super(BackupStorageTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(BackupStorageTest, cls).tearDownClass()
        print "Backup Storage Test End"
        print "========================================="

    ################################################################

    def _load_storage_info(self):
        for num in xrange(self.num_serv_t):
            url = "http://%s/api/storageSpace" % self.sl[num]
            try:
                response = urllib2.urlopen(url)
            except Exception, e:
                self.fail("%s request failed with exception: %s" % (url, traceback.format_exc()))
            self.assertEqual(response.getcode(), 200, "%s request returns code %d" % (url, response.getcode()))
            jresp = self._json_loads(response.read(), url)
            response.close()
            self._storages[num] = [s for s in jresp["reply"]["storages"] if s['storageType'] == 'local']
            print "[DEBUG] Storages found:"
            for s in self._storages[num]:
                print "%s: %s, storageType %s, isBackup %s" % (s['storageId'], s['url'], s['storageType'], s['isBackup'])

    def _add_test_camera(self, boxnum):
        data = TEST_CAMERA_DATA.copy()
        self.test_camera_id = data['id'] = str(uuid.uuid4())
        self.test_camera_physical_id = data['physicalId']
        data['parentId'] = self.guids[boxnum]
        self._server_request(boxnum, 'ec2/saveCamera', data)
        answer = self._server_request(boxnum, 'ec2/getCameras')
        print "getCameras response: '%s'" % answer
        self.assertEquals(unquote_guid(answer[0]['id']), self.test_camera_id, "Failed to assign a test camera to to a server")
        attr_data = [TEST_CAMERA_ATTR.copy()]
        attr_data[0]['cameraID'] = self.test_camera_id
        answer = self._server_request(boxnum, 'ec2/saveCameraUserAttributesList', attr_data)
        print "saveCameraUserAttributesList response: '%s'" % answer
        answer = self._server_request(boxnum, 'ec2/getCamerasEx')
        print "getCamerasEx response: '%s'" % answer


    def _fill_storage(self, boxnum):
        print "Filling the main storage with the test data."
        self._call_box(self.hosts[boxnum], "python", "/vagrant/fill_stor.py", self._storages[boxnum][0]['url'], self.test_camera_physical_id)
        answer = self._server_request(boxnum, 'api/rebuildArchive?action=start&mainPool=1')
        try:
            state = answer["reply"]["state"]
        except Exception:
            state = ''
        while state != 'RebuildState_None':
            answer = self._server_request(boxnum, 'api/rebuildArchive?action=0&mainPool=1')
            try:
                state = answer["reply"]["state"]
            except Exception:
                pass
        print "rebuildArchive done"


    def _create_backup_storage(self, boxnum):
        self._call_box(self.hosts[boxnum], "mkdir", '-p', TMP_STORAGE)
        data = self._server_request(boxnum, 'ec2/getStorages?id=' + self.guids[boxnum])
        self.assertIsNotNone(data, 'ec2/getStorages returned empty data')
        print "Storages: "
        pprint.pprint(data)
        data = data[0]
        data['id'] = str(uuid.uuid4())
        data['isBackup'] = True
        data['url'] = TMP_STORAGE
        self._server_request(boxnum, 'ec2/saveStorage', data=data)
        data2 = self._server_request(boxnum, 'ec2/getStorages?id=' + self.guids[boxnum])
        print "New storage list:"
        pprint.pprint(data2)


    ################################################################

    def InitialRestart(self):
        "Just a re-initialization with clear db."
        self._prepare_test_phase(self._stop_and_init)
        self._load_storage_info()

    def AddStorageTest(self):
        "Prepare a single camera data, add a backup storage and check how the data has been copied =to it."
        self._add_test_camera(_WORK_HOST)
        self._fill_storage(_WORK_HOST)
        self._create_backup_storage(_WORK_HOST)

    def StartBackupTest(self):
        data = self._server_request(_WORK_HOST, 'api/backupControl?action=start')
        print "backupControl start: %s" % data
        while True:
            time.sleep(0.5)
            data = self._server_request(_WORK_HOST, 'api/backupControl?action=0', timeout=1)
            print "backupControl: %s" % data
            try:
                if data['reply']['state'] == "BackupState_None":
                    break
            except Exception:
                pass


## getServerUserAttributes:
##
##[
## 	{
##		"allowAutoRedundancy": false,
##		"backupBitrate": -125000,
##		"backupDaysOfTheWeek": 127,
##		"backupDuration": -1,
##		"backupStart": 64800,
##		"backupType": "BackupManual",
##		"maxCameras": 128,
##		"serverID": "{e6d80b03-4b95-bfd7-302f-ed576bca55ec}",
##		"serverName": "Server"
##	}
##]

## /ec2/getCameraHistoryItems
## [{"archivedCameras": ["{5600af2c-b42a-4b3c-8a57-fa8567528788}"],"serverGuid": "{e6d80b03-4b95-bfd7-302f-ed576bca55ec}"}]
