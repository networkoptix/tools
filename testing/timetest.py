__author__ = 'Danil Lavrentyuk'
import urllib2
import unittest
import subprocess
import traceback
import time
import os
import json

from functest_util import ClusterWorker, ClusterLongWorker, SafeJsonLoads, get_server_guid

NUM_SERV = 2 # number of servers for test
GRACE = 1.000 # max time difference between responses to say that times are equal
HTTP_TIMEOUT = 5 # seconds
SERVER_UP_TIMEOUT = 20 # seconds
SERVER_SYNC_TIMEOUT = 10 # seconds
MINOR_SLEEP = 1 # seconds
SYSTEM_TIME_SYNC_SLEEP = 10.5 # seconds, a bit greater than server's systime check period (10 seconds)

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
    names = ['InitialSynchronization', 'ChangePrimayServer', 'SystemTimeChangeSynchronization']
    guids = {}
    _init_time = ['01:00:00', '05:00:00']
    _primary = None

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
        cls._worker.stopWork()
        print "TimeSync Test End"
        print "========================================="


    def _get_guids(self):
        for i, addr in enumerate(self.sl):
            guid = get_server_guid(addr)
            self.assertIsNotNone(guid, "Can't get box %s guid!" % addr)
            self.guids[self.hosts[i]] = guid

    def _show_systime(self, box):
        print "%s systime: %s" % (box, self.get_box_time(box))

    def debug_systime(self):
        for box in self.hosts:
            self._worker.enqueue(self._show_systime, (box,))

    def InitialSynchronization(self):
        print
        for num, box in enumerate(self.hosts):
            self._worker.enqueue(self._stop_and_init, (box,num))
        self._worker.joinQueue()
        for box in self.hosts:
            self._worker.enqueue(self.call_box, (box, 'start', 'networkoptix-mediaserver'))
        self._worker.joinQueue()
        print "Boxes started again. wait a bit"
        self.debug_systime()
        self._wait_servers_up()
        self._get_guids()
        print "Checking time..."
        self._check_time_sync()
        #self.debug_systime()


    def _stop_and_init(self, box, num):
        print "Stopping box %s" % box
        self.call_box(box, 'stop', 'networkoptix-mediaserver')
        time.sleep(0)
        self.call_box(box, '/vagrant/timetest/init.sh', self._init_time[num])
        print "Box %s stopped and ready" % box


    def _wait_servers_up(self):
        #print "=================================================="
        #print "Now:       %.1f" % time.time()
        starttime = time.time()
        endtime = starttime + SERVER_UP_TIMEOUT
        #print "Wait until %.1f" % endtime
        tocheck = set(self.sl)
        while tocheck and time.time() < endtime:
            for addr in tocheck.copy():
                try:
                    response = urllib2.urlopen("http://%s/ec2/testConnection" % (addr), timeout=1)
                except urllib2.URLError , e:
                    continue
                if response.getcode() != 200:
                    continue
                response.close()
                tocheck.discard(addr)
            if tocheck:
                time.sleep(0.5)

        if tocheck:
            self.fail("Servers' startup timed out!")
        print "Servers are ready"


    def _request_gettime(self, boxnum):
        "Request server's time and its system time. Also return current local time at moment response was received."
        addr = self.sl[boxnum]
        url = "http://%s/api/gettime" % addr
        try:
            response = urllib2.urlopen(url)
        except Exception, e:
            self.fail("%sw request failed with exception: %s" % (url, traceback.format_exc()))
        self.assertEqual(response.getcode(), 200, "%s failed with statusCode %d" % (url, response.getcode()))
        loctime = time.time()
        boxtime = self.get_box_time(self.hosts[boxnum])
        loctime2 = time.time()
        jresp = SafeJsonLoads(response.read(), addr, 'api/gettime')
        response.close()
        self.assertIsNotNone(jresp, "Bad response from %s" % url)
        return (int(jresp['reply'][u'utcTime'])/1000.0, loctime, boxtime, loctime2)

    def _task_get_time(self, boxnum):
        "Call _request_gettime and store result in self.times"
        self.times[boxnum] = self._request_gettime(boxnum)


    def _check_time_sync(self):
        end_time = time.time() + SERVER_SYNC_TIMEOUT
        reason = ''
        while time.time() < end_time:
            self.times = [[0,0] for _ in xrange(NUM_SERV)]
            for boxnum in xrange(NUM_SERV):
                self._worker.enqueue(self._task_get_time, (boxnum,))
            self._worker.joinQueue()
            #for i in xrange(NUM_SERV):
            #    print "Server %s time: %.3f" % (i, self.times[i][0])
            delta = self.times[0][1] - self.times[1][1]
            diff = self.times[0][0] - self.times[1][0] + delta
            if abs(diff) > GRACE:
                reason = "Time difference too high: %.3f" % diff
                continue
            td = [abs(t[2] - t[0]) for t in self.times]
            min_td = min(td)
            if min_td <= GRACE:
                type(self)._primary = td.index(min_td)
                print "Synchromized by box %s" % self._primary
                return
            else:
                reason = "None of servers report time close enough to it's system time. Min delta = %.3f" % min_td
            time.sleep(0.2)
        #self.debug_systime()
        self.fail(reason)
        #TODO: Add more details about servers' and their systems' time!

    def _check_systime_sync(self, boxnum, must_synchronize=True):
        t1 = time.time()
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        tt = time.time()
        while time.time() < tt + 30:
            server_time, t2, system_time, t3 = self._request_gettime(boxnum)
            print "DEBUG: server time: %s, system time: %s" % (server_time, system_time)
            timediff = system_time - server_time
            if timediff > GRACE:
                print "timediff too high!"
                time.sleep(1)
        print "time passed: %02.f" % (time.time() - t1,)
        if must_synchronize:
            self.assertLess(timediff, GRACE, "Primary server time hasn't synchronized with it's system time change. Time difference = %s" % timediff)
        else:
            self.assertGreater(timediff, GRACE, "Secondary server time has synchronized with it's system time change")

    def call_box(self, box, *command):
        #print "%s: %s" % (box, ' '.join(command))
        try:
            return subprocess.check_output(
                ['./vssh.sh', box, 'sudo'] + list(command),
                shell=False, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError, e:
            self.fail("Box %s: remote command `%s` failed at %s with code. Output:\n%s" %
                      (box, ' '.join(command), e.returncode, e.output))

    def get_box_time(self, box):
        resp = self.call_box(box, 'date', '+%s')
        return int(resp.rstrip())


    def ChangePrimayServer(self):
        print
        #self.debug_systime()
        self._setPrimaryServer()
        time.sleep(MINOR_SLEEP)
        old_primary = self._primary
        self._check_time_sync()
        #self.debug_systime()
        self.assertNotEqual(old_primary, self._primary, "Primary server hasn't been changed")

    def _get_secondary(self):
        "Return any (next) server number which isn't the primary server"
        return NUM_SERV - 1 if self._primary == 0 else self._primary - 1

    def _setPrimaryServer(self):
        boxnum = self._get_secondary()
        print "New primary will be %s (%s)" % (boxnum, self.hosts[boxnum])
        d = json.dumps({'id': self.guids[self.hosts[boxnum]]})
        req = urllib2.Request("http://%s/ec2/forcePrimaryTimeServer" % self.sl[boxnum],
                      data=d, headers={'Content-Type': 'application/json'})
        response = None
        error = None
        try:
            response = urllib2.urlopen(req, timeout=HTTP_TIMEOUT)
        except Exception:
            error = "forcePrimaryTimeServer failed with exception: %s" % traceback.format_exc()
        else:
            if response.getcode() != 200:
                error = "forcePrimaryTimeServer failed with code %s" % response.getcode()
        response.close()
        if error is not None:
            self.fail(error)

    def SystemTimeChangeSynchronization(self):
        print
        self.debug_systime()
        primary = self._primary
        box = self.hosts[primary]
        print "Use primary box %s (%s)" % (primary, box)
        newtime = self.get_box_time(box) + 12345
        self.call_box(box, 'date', '--set=@%d' % newtime)
        self.debug_systime()
        self._check_systime_sync(primary)
        self._check_time_sync()
        self.assertEqual(primary, self._primary, "Time was synchronized by secondary server!")
        #
        sec = self._get_secondary()
        box = self.hosts[sec]
        print "Use secondary box %s (%s)" % (sec, box)
        newtime = self.get_box_time(box) - 12345
        self.call_box(box, 'date', '--set=@%d' % newtime)
        self.debug_systime()
        self._check_systime_sync(sec, False)
        self._check_time_sync()
        self.assertEqual(primary, self._primary, "Primary server has been changed")



