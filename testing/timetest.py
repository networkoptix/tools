__author__ = 'Danil Lavrentyuk'
import urllib2
import unittest
import subprocess

class TimeTestError(AssertionError):
    pass


class TestLoader(unittest.TestLoader):

    def load(self, config):
        TimeSyncTest.config = config
        return self.suiteClass(map(TimeSyncTest, TimeSyncTest.names))


class TimeSyncTest(unittest.TestCase):
    config = None
    names = ['InitialSynchronization', 'SyncTest2']

    @classmethod
    def setUpClass(cls):
        print "========================================="
        print "TimeSync Test Start"
        if cls.config is None:
            raise TimeTestError("%s hasn't been configured" % cls.__name__)
        cls.sl = cls.config.get("General","serverList").split(',')
        if len(cls.sl) < 2:
            raise TimeTestError("not enough servers configured to test time synchronization")
        if len(cls.sl) > 2:
            cls.sl[2:] = []
        cls.hosts = [addr.split(':')[0] for addr in cls.sl]
        print "Server list: %s" % cls.sl
        cls.boxes = cls.config.get("General","boxList").split(',')


    @classmethod
    def tearDownClass(cls):
        print "TimeSync Test End"
        print "========================================="

    def InitialSynchronization(self):
        self.call_box(0, 'stop', ['networkoptix-mediaserver'])
        self.call_box(1, 'stop', ['networkoptix-mediaserver'])
        self.call_box(0, '/vagrant/timetest/init.sh', ['20:00:00'])
        self.call_box(1, '/vagrant/timetest/init.sh', ['10:00:00'])
        self.call_box(0, 'start', ['networkoptix-mediaserver'])
        self.call_box(1, 'start', ['networkoptix-mediaserver'])

    def SyncTest2(self):
        pass


    #TODO do it in parallel calls!

    def call_box(self, box, cmd, args=[]):
        remote_cmd = ['sudo',  cmd] + args
        addr = self.hosts[box]
        #print "%s: %s" % (addr, ' '.join(('"%s"' % s) if ' ' in s else s for s in remote_cmd))
        rc = subprocess.call(
            ['./vssh.sh', addr] + remote_cmd,
            shell=False, stderr=subprocess.STDOUT
        )
        self.assertEqual(rc, 0, "Remote command %s failed at %s" % (remote_cmd, addr))




