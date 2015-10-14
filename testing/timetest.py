__author__ = 'Danil Lavrentyuk'
import urllib2
import unittest
import subprocess
import time
import os
from functest_util import ClusterWorker, ClusterLongWorker, SafeJsonLoads

NUM_SERV = 2 # number of servers for test
GRACE = 2.000 # max time difference between responses to say that times are equal

class TimeTestError(AssertionError):
    pass


class TestLoader(unittest.TestLoader):

    def load(self, config):
        TimeSyncTest.config = config
        return self.suiteClass(map(TimeSyncTest, TimeSyncTest.names))

###########
## NOTE:
## Really it's a sequence of tests where each one after ther first depends on the previous test result.
##

class TimeSyncTest(unittest.TestCase):
    config = None
    names = ['InitialSynchronization', 'SyncTest2']
    _init_time = ['01:00:00', '05:00:00']

    @classmethod
    def setUpClass(cls):
        print "========================================="
        print "TimeSync Test Start"
        if cls.config is None:
            raise TimeTestError("%s hasn't been configured" % cls.__name__)
        cls.sl = cls.config.get("General","serverList").split(',')
        if len(cls.sl) < NUM_SERV:
            raise TimeTestError("not enough servers configured to test time synchronization")
        if len(cls.sl) > NUM_SERV:
            cls.sl[NUM_SERV:] = []
        cls.hosts = [addr.split(':')[0] for addr in cls.sl]
        print "Server list: %s" % cls.sl
        cls.boxes = cls.config.get("General","boxList").split(',')
        cls._worker = ClusterLongWorker(NUM_SERV)
        cls._worker.startThreads()


    @classmethod
    def tearDownClass(cls):
        print "Restoring external interfaces"
        #FIXME: use threads and subprocess.check_output, tbe able to log stderr messages
        # and test if they work in parallel!
        with open(os.devnull, 'w') as FNULL:
            proc = [
                #FIXME make the interface name the same with $EXT_IF fom conf.sh !!!
                (box, subprocess.Popen(['./vssh.sh', box, 'sudo', 'ifup', 'eth0'], shell=False, stdout=FNULL, stderr=subprocess.STDOUT)) for box in cls.hosts
            ]
            for b, p in proc:
                if p.wait() != 0:
                    print "ERROR: Failed to start external interface for box %s" % (b,)
        time.sleep(1)
        for box in cls.hosts:
            subprocess.call(['./vssh.sh', box, 'date', '+%s'])
        cls._worker.stopWork()
        print "TimeSync Test End"
        print "========================================="


    def InitialSynchronization(self):
        for num, box in enumerate(self.hosts):
            self._worker.enqueue(self._stop_and_init, (box,num))
        self._worker.joinQueue()
        for box in self.hosts:
            self._worker.enqueue(self.call_box, (box, 'start', 'networkoptix-mediaserver'))
        self._worker.joinQueue()
        print "Boxes started again. wait a bit"
        def now(box):
            print "%s systime: %s" % (box, self.get_box_time(box))
        for box in self.hosts:
            self._worker.enqueue(now, (box,))
        self._worker.joinQueue()
        #TODO: check connection here!
        time.sleep(10)
        print "Checking time..."
        self.times = [[0,0] for _ in xrange(NUM_SERV)]
        for boxnum, addr in enumerate(self.sl):
            self._worker.enqueue(self._request_gettime, (boxnum, addr))
        self._worker.joinQueue()
        for i in xrange(NUM_SERV):
            print "Server %s time: %.3f" % (i, self.times[i][0])
        delta = self.times[0][1] - self.times[1][1]
        diff = self.times[0][0] - self.times[1][0] + delta
        self.assertLess(abs(diff), GRACE, "Time difference too high: %.3f" % (diff))
        td = [t[2] - t[0] for t in self.times]
        min_td = min(td)
        self.assertLess(min_td, GRACE, "None of servers report time close enough to it's system time. Min delta = %.3f" % min_td)
        self.primary = td.index(min_td)
        print "Synchromized by box %s" % self.primary

    def _stop_and_init(self, box, num):
        print "Stopping box %s" % box
        self.call_box(box, 'stop', 'networkoptix-mediaserver')
        time.sleep(0)
        self.call_box(box, '/vagrant/timetest/init.sh', self._init_time[num])
        print "Box %s stopped and ready" % box

    def _request_gettime(self, boxnum, addr):
        url = "http://%s/api/gettime" % addr
        print "Connection to %s" % url
        response = urllib2.urlopen(url)
        self.assertEqual(response.getcode(), 200, "%s failed with statusCode %d" % (url, response.getcode()))
        jresp = SafeJsonLoads(response.read(), addr, 'api/gettime')
        response.close()
        self.times[boxnum] = (int(jresp['reply'][u'utcTime'])/1000.0, time.time(), self.get_box_time(self.hosts[boxnum]))


    def SyncTest2(self):
        pass

    def call_box(self, box, *command):
        print "%s: %s" % (box, ' '.join(command))
        try:
            return subprocess.check_output(       # TODO change to check_output to gather output strings
                ['./vssh.sh', box, 'sudo'] + list(command),
                shell=False, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError, e:
            self.fail("Box %s: remote command `%s` failed at %s with code. Output:\n%s" %
                      (box, ' '.join(command), e.returncode, e.output))

    def get_box_time(self, box):
        resp = self.call_box(box, 'date', '+%s')
        return int(resp.rstrip())
