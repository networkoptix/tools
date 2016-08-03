# -*- coding: utf-8 -*-
"""
HLS, WEBM and RTSP sreaming test (to use in the autotest sequence)
"""
__author__ = 'Danil Lavrentyuk'
#import time
#import unittest

#from testboxes import *
from rtsptests import RtspStreamTest, HlsStreamingTest
from stortest import StorageBasedTest, checkInit  #, TEST_CAMERA_DATA
from functest_util import quote_guid

_NUM_STREAM_SERV = 1
_WORK_HOST = 0

class StreamingTest(StorageBasedTest):
    _test_name = "Streaming"
    _test_key = "stream"
    _suits = (
        ('StreamingTests', [
            'Initialization',
            'MultiProtoStreamingTest',
            'HlsStreamingTest'
         ]),
    )
    num_serv = _NUM_STREAM_SERV   # the 1st server should be "before" NAT, the 2nd - behind NAT
    _fill_storage_script = 'fill_stor.py'

    @classmethod
    def isFailFast(cls, suit_name=""):
        return False

    @classmethod
    def globalInit(cls, config):
        super(StreamingTest, cls).globalInit(config)
        cls._duplicateConfig()
        cls.config.rtset("ServerList", [cls.sl[_WORK_HOST]])

    @classmethod
    def setUpClass(cls):
        super(StreamingTest, cls).setUpClass()
        cls._initFailed = False

    def _init_cameras(self):
        self._add_test_camera(_WORK_HOST)

    def _other_inits(self):
        "Prepare a single camera data"
        self.config.rtset("ServerUUIDList", self.guids[:]) # [quote_guid(guid) for guid in self.guids]
        self._fill_storage('streaming', _WORK_HOST, "streaming")

    @checkInit
    def MultiProtoStreamingTest(self):
        "Check RTSP and HTTP streaming from server"
        self.assertTrue(RtspStreamTest(self.config).run(),
                        "Multi-proto streaming test failed")

    @checkInit
    def HlsStreamingTest(self):
        "Check HLS streaming from server"
        self.assertTrue(HlsStreamingTest(self.config).run(),
                        "HLS streaming test failed")

class HlsOnlyTest(StreamingTest):
    _test_name = "HLS-only streaming"
    _test_key = "hlso"
    _suits = (
        ('HlsOnlyTest', [
            'Initialisation',
            'HlsStreamingTest'
         ]),
    )
