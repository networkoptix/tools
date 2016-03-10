# -*- coding: utf-8 -*-
"""
HLS, WEBM and RTSP sreaming test (to use in the autotest sequence)
"""
__author__ = 'Danil Lavrentyuk'
import time

from testboxes import *
import rtsptests

NUM_STREAM_SERV = 1

class StreamingTest(FuncTestCase):
    _test_name = "Streaming"
    _suits = (
        ('StreaingTests', [
            'Initialisation',
            'RtspTest',
         ]),
    )
    num_serv_t = NUM_STREAM_SERV # the 1st server should be "before" NAT, the 2nd - behind NAT


    def Initialisation(self):
        pass

    def RtspTest(self):
        pass
