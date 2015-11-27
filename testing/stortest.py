__author__ = 'Danil Lavrentyuk'
import urllib2
import unittest
import subprocess
import traceback
import time
import sys
import os
import json
import socket
import struct
import uuid

import pprint

from functest_util import ClusterLongWorker, get_server_guid, unquote_guid
from testboxes import *

BACKUP_STORAGE_READY_TIMEOUT = 60 # seconds

_NUM_SERV_BAK = 1
_NUM_SERV_MARCH = 2
_WORK_HOST = 0

TEST_CAMERA_TYPE_ID = "f9c03047-72f1-4c04-a929-8538343b6642"

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
    'typeId': TEST_CAMERA_TYPE_ID
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
SERVER_USER_ATTR = {
    'serverID': '', # put the server guid here
    'maxCameras': 10,
    'isRedundancyEnabled': False,
    'serverName': '',
    'backupType': 'BackupSchedule',
    'backupDaysOfTheWeek': 0x7f,
    'backupStart': 0, # == 00:00:00
    'backupDuration': -1,
    'backupBitrate': -1,
}

TMP_STORAGE = '/tmp/bstorage'

class BackupStorageTestError(FuncTestError):
    pass

class StorageBasedTest(FuncTestCase):
    num_serv_t = 0
    _storages = dict()
    _fill_storage_script = ''

    def _load_storage_info(self):
        for num in xrange(self.num_serv_t):
            resp = self._server_request(num, 'api/storageSpace')
            self._storages[num] = [s for s in resp["reply"]["storages"] if s['storageType'] == 'local']
            #print "[DEBUG] Storages found:"
            #for s in self._storages[num]:
            #    print "%s: %s, storageType %s, isBackup %s" % (s['storageId'], s['url'], s['storageType'], s['isBackup'])

    @classmethod
    def new_test_camera(cls):
        data = TEST_CAMERA_DATA.copy()
        data['id'] = str(uuid.uuid4())
        cls.test_camera_id = data['id']
        cls.test_camera_physical_id = data['physicalId']
        return data

    def _add_test_camera(self, boxnum, camera=None):
        camera = self.new_test_camera() if camera is None else camera.copy()
        camera['parentId'] = self.guids[boxnum]
        self._server_request(boxnum, 'ec2/saveCamera', camera)
        answer = self._server_request(boxnum, 'ec2/getCameras')
        #print "getCameras response: '%s'" % answer
        self.assertEquals(unquote_guid(answer[0]['id']), self.test_camera_id, "Failed to assign a test camera to to a server")
        attr_data = [TEST_CAMERA_ATTR.copy()]
        attr_data[0]['cameraID'] = self.test_camera_id
        self._server_request(boxnum, 'ec2/saveCameraUserAttributesList', attr_data) # return None
        #answer = self._server_request(boxnum, 'ec2/getCamerasEx')
        #print "getCamerasEx response: '%s'" % answer

    def _fill_storage(self, boxnum, *args):
        print "Filling the main storage with the test data."
        self._call_box(self.hosts[boxnum], "python", "/vagrant/" + self._fill_storage_script, 'random',
                       self._storages[boxnum][0]['url'], self.test_camera_physical_id, *args)
        answer = self._server_request(boxnum, 'api/rebuildArchive?action=start&mainPool=1')
        try:
            state = answer["reply"]["state"]
        except Exception:
            state = ''
        while state != 'RebuildState_None':
            time.sleep(0.5)
            answer = self._server_request(boxnum, 'api/rebuildArchive?mainPool=1')
            try:
                state = answer["reply"]["state"]
            except Exception:
                pass
        print "Server %s: rebuildArchive done" % boxnum


class BackupStorageTest(StorageBasedTest):
    num_serv_t = _NUM_SERV_BAK
    _fill_storage_script = 'fill_stor.py'

    _suits = (
        ('BackupStartTests', [
            'InitialRestart',
            'AddBackupStorage',
            'ScheduledBackupTest',
            'BackupByRequestTest',
        ]),
    )

    def _get_init_script(self, boxnum):
        return ('/vagrant/bs_init.sh',)

    @classmethod
    def setUpClass(cls):
        print "========================================="
        print "Backup Storage Test Start"
        super(BackupStorageTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(BackupStorageTest, cls).tearDownClass()
        print "Backup Storage Test End"
        print "========================================="

    ################################################################

    def _create_backup_storage(self, boxnum):
        self._call_box(self.hosts[boxnum], "mkdir", '-p', TMP_STORAGE)
        data = self._server_request(boxnum, 'ec2/getStorages?id=' + self.guids[boxnum])
        self.assertIsNotNone(data, 'ec2/getStorages returned empty data')
        #print "Storages: "
        #pprint.pprint(data)
        data = data[0]
        data['id'] = new_id = str(uuid.uuid4())
        data['isBackup'] = True
        data['url'] = TMP_STORAGE
        self._server_request(boxnum, 'ec2/saveStorage', data=data)
        #data = self._server_request(boxnum, 'ec2/getStorages?id=' + self.guids[boxnum])
        #print "New storage list:"
        #pprint.pprint(data)
        t = time.time() + BACKUP_STORAGE_READY_TIMEOUT
        new_id = '{' + new_id + '}'
        while True:
            time.sleep(0.5)
            if time.time() > t:
                self.fail("Can't initialize the backup storage. It doesn't become ready. (Timed out)")
            data = self._server_request(boxnum, 'ec2/getStatusList?id=' + new_id)
            try:
                if data and data[0] and data[0]["id"] == new_id:
                    if data[0]["status"] == "Online":
                        print "Backup storage is ready for backup."
                        return
                    #else:
                    #    print "Backup storage status: %s" % data[0]["status"]
            except Exception:
                pass

    def _wait_backup_start(self):
        while True:
            data = self._server_request(_WORK_HOST, 'api/backupControl/')
            #print "backupControl: %s" % data
            try:
                if data['reply']['state'] != "BackupState_None":
                    break
            except Exception:
                pass
            time.sleep(0.5)

    def _wait_backup_end(self):
        while True:
            time.sleep(0.5)
            data = self._server_request(_WORK_HOST, 'api/backupControl/')
            print "backupControl: %s" % data
            try:
                if data['reply']['state'] == "BackupState_None":
                    break
            except Exception:
                pass

    def _check_backup_result(self):
        try:
            boxssh(self.hosts[_WORK_HOST], ('/vagrant/diffbak.sh', self._storages[_WORK_HOST][0]['url'], TMP_STORAGE))
        except subprocess.CalledProcessError, e:
            DIFF_FAIL_CODE = 1
            DIFF_FAIL_MSG = "DIFFEENT"
            if e.returncode == DIFF_FAIL_CODE and e.output.strip() == DIFF_FAIL_MSG:
                self.fail("The main storage and the backup storage contents are different")
            else:
                raise

    ################################################################

    def InitialRestart(self):
        "Just a re-initialization with clear db."
        self._prepare_test_phase(self._stop_and_init)
        self._load_storage_info()

    def AddBackupStorage(self):
        "Prepare a single camera data and add a backup storage"
        self._add_test_camera(_WORK_HOST)
        self._create_backup_storage(_WORK_HOST)

    def ScheduledBackupTest(self):
        "In fact it tests that scheduling packup for a some moment before the current initiates backup immidiately."
        data = SERVER_USER_ATTR.copy()
        data['serverID'] = self.guids[_WORK_HOST]
        data['backupType'] = 'BackupManual'
        self._server_request(_WORK_HOST, 'ec2/saveServerUserAttributesList', data=[data])
        time.sleep(0.1)
        self._fill_storage(_WORK_HOST, "step1")
        data['backupType'] = 'BackupSchedule'
        time.sleep(0.1)
        self._server_request(_WORK_HOST, 'ec2/saveServerUserAttributesList', data=[data])
        self._wait_backup_start()
        #print "Scheduled backup started"
        self._wait_backup_end()
        self._check_backup_result()

    def BackupByRequestTest(self):
        data = SERVER_USER_ATTR.copy()
        data['serverID'] = self.guids[_WORK_HOST]
        data['backupType'] = 'BackupManual'
        self._server_request(_WORK_HOST, 'ec2/saveServerUserAttributesList', data=[data])
        time.sleep(0.1)
        self._fill_storage(_WORK_HOST, "step2")
        time.sleep(1)
        data = self._server_request(_WORK_HOST, 'api/backupControl/?action=start')
        #print "backupControl start: %s" % data
        self._wait_backup_end()
        time.sleep(1)
        self._check_backup_result()


class MultiserverArchiveTest(StorageBasedTest):
    num_serv_t = _NUM_SERV_MARCH
    _fill_storage_script = ''

# find . -type d -o -name '*.mkv'|sort > main..dir
# find /tmp/bstorage/ -type d -o -name '*.mkv'|sort > bak.dir
