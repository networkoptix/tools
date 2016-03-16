# -*- coding: utf-8 -*-
"""
HLS, WEBM and RTSP sreaming test (to use in the autotest sequence)
"""
__author__ = 'Danil Lavrentyuk'
import copy, time
import unittest

#from testboxes import *
from rtsptests import RtspStreamTest, HlsStreamingTest
from stortest import StorageBasedTest, TEST_CAMERA_DATA

_NUM_STREAM_SERV = 1
_WORK_HOST = 0

class StreamingTest(StorageBasedTest):
    _test_name = "Streaming"
    _suits = (
        ('StreamingTests', [
            'Initialisation',
            'MultiProtoStreamingTest',
            'HlsStreamingTest'
         ]),
    )
    num_serv = _NUM_STREAM_SERV   # the 1st server should be "before" NAT, the 2nd - behind NAT
    num_serv_t = _NUM_STREAM_SERV # the 1st server should be "before" NAT, the 2nd - behind NAT
    _fill_storage_script = 'fill_stor.py'
    _clear_storage_script = 'str_clear.sh'
    _need_copy = True

    def _get_init_script(self, boxnum):
        return ('/vagrant/str_init.sh',)

    @classmethod
    def setUpClass(cls):
        super(StreamingTest, cls).setUpClass()
        if cls._need_copy:
            try:
                cls.config = copy.copy(cls.config)
                cls.config.runtime = cls.config.runtime.copy()
                print "DEBUG: Server: %s" % (cls.sl[_WORK_HOST],)
                cls.config.rtset("ServerList", [cls.sl[_WORK_HOST]])
                cls._need_copy = False
            except Exception:
                cls.tearDownClass()
                raise

    def _init_cameras(self):
        name = TEST_CAMERA_DATA['name']
        answer = self._server_request(_WORK_HOST, 'ec2/getCameras')
        for c in answer:
            if c['name'] == name:
                self.test_camera_id = c['id']
                self.test_camera_physical_id = c['physicalId']
                return
        self._add_test_camera(_WORK_HOST)

    def Initialisation(self):
        "Re-initialize with clear db, prepare a single camera data"
        self._InitialRestartAndPrepare()
        self._fill_storage('streaming', _WORK_HOST, "streaming")

    def MultiProtoStreamingTest(self):
        "Check RTSP and HTTP streaming from server"
        self.assertTrue(RtspStreamTest(self.config).run(),
                        "Multi-proto streaming test failed")

    def HlsStreamingTest(self):
        "Check HLS streaming from server"
        self.assertTrue(HlsStreamingTest(self.config).run(),
                        "HLS streaing test failed")
