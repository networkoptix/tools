# -*- coding: utf-8 -*-
"""
Storages functional tests:
1. Backup storage test
2. Multiarchive storage test
Both imported and called by functest.py
"""
__author__ = 'Danil Lavrentyuk'
import os, os.path, sys, time
#import urllib2
import subprocess
#import traceback
import uuid
from pipes import quote as shquote

import pprint

from functest_util import ClusterLongWorker, get_server_guid, unquote_guid, CAMERA_ATTR_EMPTY
from testboxes import *

mypath = os.path.dirname(os.path.abspath(sys.argv[0]))
multiserv_interfals_fname = os.path.join(mypath, "multiserv_intervals.py")

BACKUP_STORAGE_READY_TIMEOUT = 60  # seconds

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

TEST_CAMERA_ATTR = CAMERA_ATTR_EMPTY.copy()
TEST_CAMERA_ATTR.update({
    'scheduleEnabled': True,
    'backupType': "CameraBackup_HighQuality|CameraBackup_LowQuality",  # or CameraBackupBoth
    'cameraName': 'test-camera',
})
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

TMP_STORAGE = '/tmp/bstorage'  # directory path on the server side to create backup storage in


class BackupStorageTestError(FuncTestError):
    pass


class StorageBasedTest(FuncTestCase):
    """ Some common logic for storage tests.
    """
    num_serv_t = 0
    _storages = dict()
    _fill_storage_script = ''
    test_camera_id = 0
    test_camera_physical_id = 0

    def _load_storage_info(self):
        "Get servers' storage space data"
        for num in xrange(self.num_serv_t):
            resp = self._server_request(num, 'api/storageSpace')
            self._storages[num] = [s for s in resp["reply"]["storages"] if s['storageType'] == 'local']
            #print "[DEBUG] Storages found:"
            #for s in self._storages[num]:
            #    print "%s: %s, storageType %s, isBackup %s" % (s['storageId'], s['url'], s['storageType'], s['isBackup'])

    @classmethod
    def new_test_camera(cls):
        "Creates initial dict of camera data."
        data = TEST_CAMERA_DATA.copy()
        data['id'] = str(uuid.uuid4())
        cls.test_camera_id = data['id']
        cls.test_camera_physical_id = data['physicalId']
        return data

    def _add_test_camera(self, boxnum, camera=None, log_response=False):
        camera = self.new_test_camera() if camera is None else camera.copy()
        camera['parentId'] = self.guids[boxnum]
        self._server_request(boxnum, 'ec2/saveCamera', camera)
        answer = self._server_request(boxnum, 'ec2/getCameras')
        if log_response:
            print "getCameras(%s) response: '%s'" % (boxnum, answer)
        for c in answer:
            if c['parentId'] == self.guids[boxnum]:
                self.assertEquals(unquote_guid(c['id']), self.test_camera_id, "Failed to assign a test camera to to a server")
        attr_data = [TEST_CAMERA_ATTR.copy()]
        attr_data[0]['cameraID'] = self.test_camera_id
        self._server_request(boxnum, 'ec2/saveCameraUserAttributesList', attr_data) # return None
        answer = self._server_request(boxnum, 'ec2/getCamerasEx')
        if log_response:
            print "getCamerasEx(%s) response: '%s'" % (boxnum, answer)

    def _fill_storage(self, mode, boxnum, *args):
        print "Server %s: Filling the main storage with the test data." % boxnum
        self._call_box(self.hosts[boxnum], "python", shquote("/vagrant/" + self._fill_storage_script), mode,
                       shquote(self._storages[boxnum][0]['url']), self.test_camera_physical_id, *args)
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


    @classmethod
    def tearDownClass(cls):
        if cls._clear_script:
            for num in xrange(cls.num_serv_t):
                if num in cls._storages:
                    print "Remotely calling %s at box %s" % (cls._clear_script, num)
                    cls.class_call_box(cls.hosts[num], '/vagrant/' + cls._clear_script, cls._storages[num][0]['url'], TMP_STORAGE)
        super(StorageBasedTest, cls).tearDownClass()

    def _init_cameras(self):
        pass

    def _InitialRestartAndPrepare(self):
        """
        Common initial preparatioin code for subclasses
        Re-initialize with clear db, prepare a single camera data.
        """
        self._prepare_test_phase(self._stop_and_init)
        self._load_storage_info()
        self._init_cameras()


class BackupStorageTest(StorageBasedTest):
    """
    The test for backup storage functionality.
    Creates a backup storage and tries to start the backup procedure both manually and scheduled.
    """
    _test_name = "Backup Storage"
    num_serv_t = _NUM_SERV_BAK
    _fill_storage_script = 'fill_stor.py'
    _clear_script = 'bs_clear.sh'

    _suits = (
        ('BackupStartTests', [
            'InitialRestartAndPrepare',
            'ScheduledBackupTest',
            'BackupByRequestTest',
        ]),
    )

    def _get_init_script(self, boxnum):
        return ('/vagrant/bs_init.sh',)

    #@classmethod
    #def setUpClass(cls):
    #    super(BackupStorageTest, cls).setUpClass()

    #@classmethod
    #def tearDownClass(cls):
    #    super(BackupStorageTest, cls).tearDownClass()

    ################################################################

    def _init_cameras(self):
        self._add_test_camera(_WORK_HOST)

    def _create_backup_storage(self, boxnum):
        self._call_box(self.hosts[boxnum], "mkdir", '-p', TMP_STORAGE)
        data = self._server_request(boxnum, 'ec2/getStorages?id=' + self.guids[boxnum])
        self.assertIsNotNone(data, 'ec2/getStorages returned empty data')
        #print "DEBUG: Storages: "
        #pprint.pprint(data)
        data = data[0]
        data['id'] = new_id = str(uuid.uuid4())
        data['isBackup'] = True
        data['url'] = TMP_STORAGE
        self._server_request(boxnum, 'ec2/saveStorage', data=data)
        data = self._server_request(boxnum, 'ec2/getStorages?id=' + self.guids[boxnum])
        #print "DEBUG: New storage list:"
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
            # print "backupControl: %s" % data
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
            DIFF_FAIL_MSG = "DIFFERENT"
            if e.returncode == DIFF_FAIL_CODE and e.output.strip() == DIFF_FAIL_MSG:
                self.fail("The main storage and the backup storage contents are different")
            else:
                raise

    ################################################################

    def InitialRestartAndPrepare(self):
        "Re-initialize with clear db, prepare a single camera data and add a backup storage"
        self._InitialRestartAndPrepare()
        self._create_backup_storage(_WORK_HOST)

    def ScheduledBackupTest(self):
        "In fact it tests that scheduling backup for a some moment before the current initiates backup immidiately."
        data = SERVER_USER_ATTR.copy()
        data['serverID'] = self.guids[_WORK_HOST]
        data['backupType'] = 'BackupManual'
        self._server_request(_WORK_HOST, 'ec2/saveServerUserAttributesList', data=[data])
        time.sleep(0.1)
        self._fill_storage('random', _WORK_HOST, "step1")
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
        self._fill_storage('random', _WORK_HOST, "step2")
        time.sleep(1)
        data = self._server_request(_WORK_HOST, 'api/backupControl/?action=start')
        #print "backupControl start: %s" % data
        self._wait_backup_end()
        time.sleep(1)
        self._check_backup_result()


class MultiserverArchiveTest(StorageBasedTest):
    _test_name = "Multiserver Archive"
    num_serv_t = _NUM_SERV_MARCH
    _fill_storage_script = 'fill_stor.py'
    _clear_script = 'ms_clear.sh'
    time_periods_single = []
    time_periods_joined = []

    _suits = (
        ('MultiserverArchiveTest', [
            'InitialRestartAndPrepare',
            'CheckArchiveMultiserv',
            'CheckArchivesSeparated',
        ]),
    )

    def _get_init_script(self, boxnum):
        return ('/vagrant/ms_init.sh', )

    #@classmethod
    #def setUpClass(cls):
    #    super(MultiserverArchiveTest, cls).setUpClass()

    #@classmethod
    #def tearDownClass(cls):
    #    super(MultiserverArchiveTest, cls).tearDownClass()

    ################################################################

    def _init_cameras(self):
        c = self.new_test_camera()
        for num in xrange(_NUM_SERV_MARCH):
            self._worker.enqueue(self._add_test_camera, (num, c, False))
            #self._add_test_camera(num, c)
        self._worker.joinQueue()

    def _getRecordedTime(self, boxnum, flat=True):
        req = 'ec2/recordedTimePeriods?physicalId=%s' % self.test_camera_physical_id
        if flat:
            req += '&flat' # ! it's not bool parameter, it's existance is it's value
        return self._server_request(boxnum, req)

    def _compare_chunks(self, boxnum, server, prepared):
        fail_count = 0
        i = 0
        serv_str = "" if boxnum is None else (' (%d)' % boxnum)
        for chunk in server:
            if i >= len(prepared):
                print "FAIL: Extra data in server%s answer at position %s: %s" % (serv_str, i, chunk)
                fail_count += 1
            elif int(chunk['startTimeMs']) != prepared[i]['start'] + self.base_time:
                print "FAIL: Chunk %s start time differs: server%s %s, prepared %s" % (
                    i, serv_str, int(chunk['startTimeMs']), prepared[i]['start'] + self.base_time)
                fail_count += 1
            elif int(chunk['durationMs']) != prepared[i]['duration']:
                print "FAIL: Chunk %s duration differs: server%s %s, prepared %s" % (
                    i, serv_str, chunk['durationMs'], prepared[i]['duration'])
                fail_count += 1
            if fail_count >= 10:
                break
            i += 1
        if fail_count < 10 and i < len(prepared):
            print "FAIL: Server%s anser shorter then prepared data (%s vs %s)" % (serv_str, i, len(prepared))
        self.assertEqual(fail_count, 0, "Server%s reports chunk list different from the prepared one." % serv_str)

    ################################################################

    def InitialRestartAndPrepare(self):
        "Re-initialize with clear db, prepare a single camera data and fill the storage with video data"
        self._InitialRestartAndPrepare()
        print "Filling archives with data..."
        for num in xrange(_NUM_SERV_MARCH):
            self._fill_storage('multiserv', num, str(num))
        print "Done. Wait a bit..."
        tmp = {}
        execfile(multiserv_interfals_fname, tmp)
        type(self).time_periods_single = tmp['time_periods_single']
        type(self).time_periods_joined = tmp['time_periods_joined']
        time.sleep(20)

    def CheckArchiveMultiserv(self):
        "Checks recorded time periods for both servers joined into one system."
        answer = [self._getRecordedTime(num) for num in xrange(self.num_serv_t)]
        for a in answer:
            self.assertTrue(a["error"] == '0' and a["errorString"] == '',
                "ec2/recordedTimePeriods request to the box %s returns error %s: %s" % (num, a["error"], a["errorString"]))
        self.assertEqual(answer[0]["reply"], answer[1]["reply"],
                "Boxes return different answers to the ec2/recordedTimePeriods request")
        #for chunk in answer[0]['reply'][:10]:
        #    print chunk
        type(self).base_time = int(answer[0]['reply'][0]['startTimeMs'])
        #print "DEBUG: base = %s" % self.base_time
        self._compare_chunks(None, answer[0]['reply'], self.time_periods_joined)

    def _splitSystems(self):
        print "Split servers into two systems"
        newname = "anothername"
        self._change_system_name(1, newname)
        time.sleep(1)
        info0 = self._server_request(0, 'api/moduleInformation')
        info1 = self._server_request(1, 'api/moduleInformation')
        self.assertEqual(info1['reply']['systemName'], newname, "Failed to give server 1 new system name")
        self.assertNotEqual(info0['reply']['systemName'], newname, "Server 0 system name also has changed")

    def CheckArchivesSeparated(self):
        self._splitSystems()
        answer = [[], []]
        uri = 'ec2/recordedTimePeriods?physicalId=%s&flat' % self.test_camera_physical_id
        for atempt_count in xrange(10):
            answer[0] = self._server_request(0, uri)['reply'][:]
            time.sleep(0.2)
            answer[1] = self._server_request(1, uri)['reply'][:]
            #print "0: %s, %s..." % (id(answer[0]), answer[0][:10])
            #print "1: %s, %s..." % (id(answer[1]), answer[1][:10])
            if answer[0] != answer[1]:
                break
            print "Attempt %s failed!" % atempt_count
            time.sleep(1)
        for i in xrange(min(len(answer[0]), len(answer[1]))):
            if answer[0][i] == answer[1][i]:
                print "Separated servers report the same chunk: %s, %s" % (answer[0][i], answer[1][i])
        self.assertFalse(answer[0] == answer[1], "Separated servers report the same chunk list")
        #print "Server 0\n" + "\n".join(str(chunk) for chunk in answer[0][:4])
        self._compare_chunks(0, answer[0], self.time_periods_single[0])
        #print "Server 1\n" + "\n".join(str(chunk) for chunk in answer[1][:4])
        self._compare_chunks(1, answer[1], self.time_periods_single[1])
        #print "Join servers back"
        #self._change_system_name(1, sysname)  # it's done by _clear_storage_script 'ms_clear.sh'
        time.sleep(0.1)


