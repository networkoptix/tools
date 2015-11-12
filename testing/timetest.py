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

from functest_util import ClusterLongWorker, get_server_guid
from testboxes import *

GRACE = 1.0 # max time difference between responses to say that times are equal
INET_GRACE = 2.0 # max time difference between a mediaserver time and the internet time
DELTA_GRACE = 0.05 # max difference between two deltas (each between a mediaserver time and this script local time)
                   # used to check if the server time hasn't changed
HTTP_TIMEOUT = 5 # seconds
SERVER_SYNC_TIMEOUT = 10 # seconds
MINOR_SLEEP = 1 # seconds
SYSTEM_TIME_SYNC_SLEEP = 10.5 # seconds, a bit greater than server's systime check period (10 seconds)
SYSTEM_TIME_NOTSYNC_SURE = 30 # seconds, how long wait to shure server hasn't synced with system time
INET_SYNC_TIMEOUT = 15 * 2 # twice as bigger than the value in tt_setisync.sh

IF_EXT = 'eth0'

class TimeTestError(FuncTestError):
    pass

time_servers = ('time.nist.gov', 'time.ien.it')
TIME_PORT = 37
TIME_SERVER_TIMEOUT = 10
SHIFT_1900_1970 = 2208988800

def get_inet_time(host):
    s = None
    try:
        s = socket.create_connection((host, TIME_PORT), TIME_SERVER_TIMEOUT)
        d = s.recv(4)
        return d
    except Exception:
        return ''
    finally:
        if s:
            s.close()

def check_inet_time():
    "Make sure that at least one of time servers, used by mediaserver for time synchronization, is available and responding."
    for host in time_servers:
        d = get_inet_time(host)
        if len(d) == 4:
            return d # The first success means OK
    return False



class ___TestLoader(unittest.TestLoader):

    def load(self, testclass, testset, config):
        TimeSyncTest.config = config
        names = getattr(TimeSyncTest, testset, None)
        if names is not None:
            print "[Preparing %s tests]" % testset
            TimeSyncTest.testset = testset
            return self.suiteClass(map(TimeSyncTest, names))
        else:
            print "ERROR: No test set '%s' found!" % testset


###########
## NOTE:
## Really it's a sequence of tests where most of tests depend on the previous test result.
##

class TimeSyncTest(FuncTestCase):
    #num_serv = _NUM_SERV # override
    _suits = (
        ('SyncTimeNoInetTests', [
            'InitialSynchronization',
            'ChangePrimayServer',
            'PrimarySystemTimeChange',
            'SecondarySystemTimeChange',
            'StopPrimary', 'RestartSecondaryWhilePrimaryOff', 'StartPrimary',
            'PrimaryStillSynchronized',
            'MakeSecondaryAlone'
        ]),
        ('InetTimeSyncTests', [
            'TurnInetOn', 'ChangePrimarySystime',
            'KeepInetTimeAfterIfdown',
            'KeepInetTimeAfterSecondaryOff',
            'KeepInetTimeAfterSecondaryOn',
            'KeepInetTimeAfterRestartPrimary',
            'BothRestart_SyncWithOS',
            'PrimaryFollowsSystemTime',
        ])
    )
    _init_time = []
    _primary = None
    _secondary = None

    @classmethod
    def setUpClass(cls):
        print "========================================="
        print "TimeSync Test Start: %s" % cls.testset
        if cls.testset == 'InetTimeSyncTests':
            if not check_inet_time():
                raise unittest.SkipTest("Internet time servers aren't sccessible")
        super(TimeSyncTest, cls).setUpClass()
        if not cls._init_time:
            t = int(time.time())
            cls._init_time = [str(t - v) for v in (72000, 144000)]

    @classmethod
    def tearDownClass(cls):
        print "Restoring external interfaces"
        #FIXME: use threads and subprocess.check_output, tbe able to log stderr messages
        with open(os.devnull, 'w') as FNULL:
            proc = [
                #FIXME make the interface name the same with $EXT_IF fom conf.sh !!!
                (box, subprocess.Popen(['./vssh.sh', box, 'sudo', 'ifup', IF_EXT], shell=False, stdout=FNULL, stderr=subprocess.STDOUT)) for box in cls.hosts
            ]
            for b, p in proc:
                if p.wait() != 0:
                    print "ERROR: Failed to start external interface for box %s" % (b,)
        super(TimeSyncTest, cls).tearDownClass()
        print "TimeSync Test End"
        print "========================================="

    ################################################################

    def _get_init_script(self, boxnum):
        return '/vagrant/tt_init.sh', self._init_time[boxnum]

    #def _get_guids(self):
    #    for i, addr in enumerate(self.sl):
    #        guid = get_server_guid(addr)
    #        self.assertIsNotNone(guid, "Can't get box %s guid!" % addr)
    #        self.guids[self.hosts[i]] = guid

    def _show_systime(self, box):
        print "OS time for %s: %s " % (box, self.get_box_time(box))

    def debug_systime(self):
        for box in self.hosts:
            self._worker.enqueue(self._show_systime, (box,))

    def _request_gettime(self, boxnum, ask_box_time=True):
        "Request server's time and its system time. Also return current local time at moment response was received."
        addr = self.sl[boxnum]
        url = "http://%s/api/gettime" % addr
        try:
            response = urllib2.urlopen(url)
        except Exception, e:
            self.fail("%s request failed with exception: %s" % (url, traceback.format_exc()))
        loctime = time.time()
        self.assertEqual(response.getcode(), 200, "%s failed with statusCode %d" % (url, response.getcode()))
        boxtime = self.get_box_time(self.hosts[boxnum]) if ask_box_time else 0
        jresp = self._json_loads(response.read(), url)
        response.close()
        return (int(jresp['reply'][u'utcTime'])/1000.0, loctime, boxtime)

    def _task_get_time(self, boxnum):
        "Call _request_gettime and store result in self.times - used tu run in a separate thread"
        self.times[boxnum] = self._request_gettime(boxnum)

    def _check_time_sync(self, sync_with_system=True):
        end_time = time.time() + SERVER_SYNC_TIMEOUT
        reason = ''
        while time.time() < end_time:
            self.times = [[0,0] for _ in xrange(self.num_serv)]
            for boxnum in xrange(self.num_serv):
                self._worker.enqueue(self._task_get_time, (boxnum,))
            self._worker.joinQueue()
            #for i in xrange(self.num_serv):
            #    print "Server %s time: %.3f" % (i, self.times[i][0])
            delta = self.times[0][1] - self.times[1][1]
            diff = self.times[0][0] - self.times[1][0] + delta
            if abs(diff) > GRACE:
                reason = "Time difference too high: %.3f" % diff
                continue
            elif not sync_with_system:
                return
            if sync_with_system:
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
        print "0: ", self.times[0]
        print "1: ", self.times[1]
        self.fail(reason)
        #TODO: Add more details about servers' and their systems' time!

    def _check_systime_sync(self, boxnum, must_synchronize=True):
        tt = time.time() + (1 if must_synchronize else SYSTEM_TIME_NOTSYNC_SURE)
        timediff = 0
        while time.time() < tt:
            server_time, _, system_time = self._request_gettime(boxnum)
            #print "DEBUG: server time: %s, system time: %s" % (server_time, system_time)
            timediff = abs(system_time - server_time)
            if timediff > GRACE:
                if must_synchronize:
                    print "DEBUG: %s server time: %s, system time: %s. Diff = %.2f - too high" % (boxnum, server_time, system_time, timediff)
                time.sleep(0.5)
            else:
                break
        if must_synchronize:
            self.assertLess(timediff, GRACE, "Primary server time hasn't synchronized with it's system time change. Time difference = %s" % timediff)
        else:
            print "Time diff = %.1f, grace = %s" % (timediff, GRACE)
            self.assertGreater(timediff, GRACE, "Secondary server time has synchronized with it's system time change")

    def get_box_time(self, box):
        resp = self._call_box(box, 'date', '+%s')
        return int(resp.rstrip())

    def shift_box_time(self, box, delta):
        "Changes OS time on the box by the shift value"
        self._call_box(box, "/vagrant/chtime.sh", str(delta))

    def _serv_local_delta(self, boxnum):
        """Returns delta between mediasever's time and local script's time
        """
        times = self._request_gettime(boxnum) #, False) -- return this after removing the next debug
        print "DEBUG: %s server time %s, system time %s, local time %s" % (boxnum, times[0], times[2], times[1])
        return times[1] - times[0]  # local time -- server's time

    def _get_secondary(self):
        "Return any (next) server number which isn't the primary server"
        return self.num_serv - 1 if self._primary == 0 else self._primary - 1

    def _setPrimaryServer(self, boxnum):
        print "New primary is %s (%s)" % (boxnum, self.hosts[boxnum])
        d = json.dumps({'id': self.guids[boxnum]})
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

    ####################################################

    def InitialSynchronization(self):
        """Stop both mediaservers, initialize boxes' system time and start the servers again.
        """
        self._prepare_test_phase(self._stop_and_init)
        #self.debug_systime()
        #self._get_guids()
        print "Checking time..."
        self._check_time_sync()
        #self.debug_systime()
        #TODO add here flags check, what server has became the primary one

    def ChangePrimayServer(self):
        """Check mediaservers' time synchronization by the new primary server.
        """
        #self.debug_systime()
        self._setPrimaryServer(self._get_secondary())
        time.sleep(MINOR_SLEEP)
        old_primary = self._primary
        self._check_time_sync()
        #self.debug_systime()
        self.assertNotEqual(old_primary, self._primary, "Primary server hasn't been changed")
        #TODO add the flags check!

    def PrimarySystemTimeChange(self):
        """Change system time on the primary servers' box, check if the servers have synchronized.
        """
        self.shortDescription()
        self.debug_systime()
        primary = self._primary # they'll be compared later
        box = self.hosts[primary]
        print "Use primary box %s (%s)" % (primary, box)
        self.shift_box_time(box, 12345)
        self.debug_systime()
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        self._check_systime_sync(primary)
        self._check_time_sync()
        self.assertEqual(primary, self._primary, "Time was synchronized by secondary server")

    def SecondarySystemTimeChange(self):
        """Change system time on the secondary servers' box, check if the servers have ignored it.
        """
        primary = self._primary # they'll be compared later
        sec = self._get_secondary()
        box = self.hosts[sec]
        print "Use secondary box %s (%s)" % (sec, box)
        self.shift_box_time(box, -12345)
        self.debug_systime()
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        self._check_systime_sync(sec, False)
        self._check_time_sync()
        self.assertEqual(primary, self._primary, "Primary server has been changed")

    def StopPrimary(self):
        """Check if stopping the primary server doesn't lead to the secondary's time change.
        """
        type(self)._secondary = self._get_secondary()
        self._show_systime(self.hosts[self._primary])
        delta_before = self._serv_local_delta(self._secondary) # remember difference between seco9ndary server's time and the local time
        self._mediaserver_ctl(self.hosts[self._primary], 'stop')
        time.sleep(MINOR_SLEEP)
        delta_after = self._serv_local_delta(self._secondary)
        self.assertAlmostEqual(delta_before, delta_after, delta=DELTA_GRACE,
                               msg="The secondary server's time changed after the primary server was stopped")

    @unittest.expectedFailure
    def RestartSecondaryWhilePrimaryOff(self):
        """Check if restarting the secondary (while the primary is off) doesn't change it's time
        """
        delta_before = self._serv_local_delta(self._secondary)
        print "Delta before = %.2f" % delta_before
        self._mediaserver_ctl(self.hosts[self._secondary], 'restart')
        self._wait_servers_up()
        delta_after = self._serv_local_delta(self._secondary)
        print "Delta after = %.2f" % delta_after
        self.assertAlmostEqual(delta_before, delta_after, delta=DELTA_GRACE,
                               msg="The secondary server's time changed (by %.3f) after it was restarted (while the primary is off)" %
                                   (delta_before - delta_after))

    def StartPrimary(self):
        """Check if starting the primary server again doesn't change time on the both primary and secondary.
        """
        delta_before = self._serv_local_delta(self._secondary)
        self._mediaserver_ctl(self.hosts[self._primary], 'start')
        self._wait_servers_up()
        delta_after = self._serv_local_delta(self._secondary)
        self.assertAlmostEqual(delta_before, delta_after, delta=DELTA_GRACE,
                               msg="The secondary server's time changed after the primary server was started again")
        #self.debug_systime()
        self._check_time_sync(False)

    @unittest.expectedFailure
    def PrimaryStillSynchronized(self):
        self._check_systime_sync(self._primary)

    #TODO: now it should test thet the secondary DOES'T become the new primary and DOESN'T sync. with it's OS time
    @unittest.skip("To be reimpemented")
    def MakeSecondaryAlone(self):
        """Check if the secondary after stopping and deleting the primary becomes primary itself and synchronize with it's OS time.
        """
        self._mediaserver_ctl(self.hosts[self._primary], 'stop')
        box = self.hosts[self._secondary]
        self.shift_box_time(box, -12345)
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)

        # remove from the secondary server the record about the prime (which is down now)
        d = json.dumps({'id': self.guids[self._primary]})
        req = urllib2.Request("http://%s/ec2/removeMediaServer" % self.sl[self._secondary],
                      data=d, headers={'Content-Type': 'application/json'})
        response = None
        error = None
        try:
            response = urllib2.urlopen(req, timeout=HTTP_TIMEOUT)
        except Exception:
            error = "removeMediaServer failed with exception: %s" % traceback.format_exc()
        else:
            if response.getcode() != 200:
                error = "forcePrimaryTimeServer failed with code %s" % response.getcode()
        response.close()
        if error is not None:
            self.fail(error)
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)

        # wait if the secondary becomes new primary
        pass

        # check if the server time
        #TODO: continue (or remove, or rewrite) after the right logic will be determined

    ###################################################################

    def _prepare_inet_test(self, box, num):
        print "Stopping box %s" % box
        self._mediaserver_ctl(box, 'stop')
        time.sleep(0)
        self._call_box(box, '/vagrant/tt_setisync.sh', self._init_time[num])

    ###################################################################

    def TurnInetOn(self):
        self._prepare_test_phase(self._prepare_inet_test)
        self._check_time_sync()
        #TODO check for primary, make it primary if not bn
        # until that, set it to be sure
        self._setPrimaryServer(self._primary)
        self._check_time_sync(False)
        type(self)._secondary = self._get_secondary()
        self._call_box(self.hosts[self._secondary], '/vagrant/tt_iup.sh')
        time.sleep(INET_SYNC_TIMEOUT)
        itime_str = check_inet_time()
        self.assertTrue(itime_str, "Internet time request filed!")
        itime = struct.unpack('!I', itime_str)[0] - SHIFT_1900_1970
        idelta = itime - time.time() # get the difference between local ant inet time to use it later
        print "DEBUG: time from internet: %s, %s" % (itime, time.asctime(time.localtime(itime)))

        for boxnum in xrange(self.num_serv):
            btime = self._request_gettime(boxnum)
            itime = time.time() + idelta
            print "Server %s time %s; inet time %s" % (boxnum, btime[0], itime)
            self.assertAlmostEqual(itime, btime[0], delta=INET_GRACE,
                                   msg="Server at box %s hasn't sinchronized with Internet time in %s seconds" %
                                       (boxnum, INET_SYNC_TIMEOUT))

    def ChangePrimarySystime(self):
        delta_before = self._serv_local_delta(self._primary)
        self.shift_box_time(self.hosts[self._primary], -12345)
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        delta_after = self._serv_local_delta(self._primary)
        self.assertAlmostEqual(delta_before, delta_after, delta=DELTA_GRACE,
                               msg="Primary server's time changed (%s) after changing of it's system time" %
                                   (delta_before - delta_after))
        self._check_time_sync(False)

    def KeepInetTimeAfterIfdown(self):
        """Check if the servers keep time, synchronized with the Internet, after the Internet connection goes down.
        """
        delta_before = self._serv_local_delta(self._primary)
        print "Turn off the internet connection at the box %s" % self._secondary
        self._call_box(self.hosts[self._secondary], 'ifdown', IF_EXT)
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        delta_after = self._serv_local_delta(self._primary)
        self.assertAlmostEqual(delta_before, delta_after, delta=DELTA_GRACE,
                               msg="Primary server's time changed (%s) after the Internet connection "
                                   "on the secondary server was turned off" %
                                   (delta_before - delta_after))
        self._check_time_sync(False)

    def KeepInetTimeAfterSecondaryOff(self):
        """Check if the primary server keeps time after the secondary one (which was connected to the Internet) goes down.
        """
        delta_before = self._serv_local_delta(self._primary)
        self._mediaserver_ctl(self.hosts[self._secondary], 'stop')
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        delta_after = self._serv_local_delta(self._primary)
        self.assertAlmostEqual(delta_before, delta_after, delta=DELTA_GRACE,
                               msg="Primary server's time changed (%s) after the secondary server was turned off" %
                                   (delta_before - delta_after))

    def KeepInetTimeAfterSecondaryOn(self):
        """Check if the primary server keeps time after the secondary one starts up again. Also check symchronization.
        """
        delta_before = self._serv_local_delta(self._primary)
        self._mediaserver_ctl(self.hosts[self._secondary], 'start')
        self._wait_servers_up()
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        delta_after = self._serv_local_delta(self._primary)
        self.assertAlmostEqual(delta_before, delta_after, delta=DELTA_GRACE,
                               msg="Primary server's time changed (%s) after the secondary server was turned off" %
                                   (delta_before - delta_after))
        self._check_time_sync(False)

    def KeepInetTimeAfterRestartPrimary(self):
        """Restart primary and check time from the Internet is still kept.
        """
        delta_before = self._serv_local_delta(self._primary)
        self._mediaserver_ctl(self.hosts[self._primary], 'restart')
        self._wait_servers_up()
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        delta_after = self._serv_local_delta(self._primary)
        self.assertAlmostEqual(delta_before, delta_after, delta=DELTA_GRACE,
                               msg="Primary server's time changed (%s) after it's restart" %
                                   (delta_before - delta_after))
        self._check_time_sync(False)

    @unittest.expectedFailure
    def BothRestart_SyncWithOS(self):
        """Restart both servers and check that now they are synchronized with the primary's OS time.
        """
        primary = self._primary # save it
        self._servers_th_ctl('stop')
        time.sleep(MINOR_SLEEP)
        self._servers_th_ctl('start')
        self._wait_servers_up()
        self._check_time_sync()
        self.assertEqual(primary, self._primary, "The primary server changed after both servers were restarted.")

    @unittest.expectedFailure
    def PrimaryFollowsSystemTime(self):
        """Check if the primary server changes time when it's system time has been changed.
        """
        primary = self._primary # save it
        self.shift_box_time(self.hosts[self._primary], 5000)
        time.sleep(SYSTEM_TIME_SYNC_SLEEP)
        self._check_time_sync()
        self.assertEqual(primary, self._primary, "The primary server changed after the previous primary's system time changed.")

