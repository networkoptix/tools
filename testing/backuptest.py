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

class BackupStorageTestError(FuncTestError):
    pass

class BackupStorageTest(FuncTestCase):
    num_serv = _NUM_SERV # override

    _suits = (
        ('BackupStartTests', [
            'AddStorageTest'
        ])
    )


    @classmethod
    def setUpClass(cls):
        super(BackupStorageTest, cls).setUpClass()


    def AddStorageTest(self):
        pass
