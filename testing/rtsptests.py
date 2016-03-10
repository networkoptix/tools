# -*- coding: utf-8 -*-
""" All RTSP tests and their additional classes, called from functest.py
Initially moved out from functest.py
"""
__author__ = 'Danil Lavrentyuk'
import random
import errno, select, signal, socket, time, traceback
import base64
from hashlib import md5
import urllib2
import json
import threading
import re
from collections import namedtuple

from functest_util import SafeJsonLoads, HttpRequest, parse_size, quote_guid, CAMERA_ATTR_EMPTY, FULL_SCHEDULE_TASKS

DEFAULT_ARCHIVE_STREAM_RATE = 1024*1024*10 # 10 MB/Sec


_urlsub = re.compile(r'[:/?]')
_urlsubtbl = {':': '$', '/': '%', '?': '#'}

def _urlsubfunc(m):
    return _urlsubtbl[m.group(0)]

def _buildUrlPath(url):
    return _urlsub.sub(_urlsubfunc, url) + '_' + ''.join(str(random.randint(0,9)) for _ in xrange(12))


class RtspLog:
    """ Controls two log files: for ok- and fail-messages.
    """
    _fileOK = None
    _fileFail = None

    def __init__(self, serverAddr):
        l = serverAddr.split(":")
        self._fileOK = open("%s_%s.rtsp.ok.log" % (l[0],l[1]),"w+")
        self._fileFail = open("%s_%s.rtsp.fail.log" % (l[0],l[1]),"w+")

    def writeOK(self, msg):
        self._fileOK.write("%s\n" % (msg))

    def writeFail(self, msg):
        self._fileFail.write("%s\n" % (msg))

    def flushOK(self):
        self._fileOK.flush()

    def flushFail(self):
        self._fileFail.flush()

    def close(self):
        self._fileOK.close()
        self._fileFail.close()


class RtspStreamURLGenerator:
    _streamURLTemplate = "rtsp://%s:%s/%s"
    _server = None
    _port = None
    _mac = None

    def __init__(self, (server, port), mac):
        self._server = server
        self._port = port
        self._mac = mac

    def generateURL(self):
        return self._streamURLTemplate % (self._server, self._port, self._mac)


class RtspArchiveURLGenerator:
    _archiveURLTemplate = "rtsp://%s:%s/%s?pos=%d"
    _diffMax = 5
    _diffMin = 1
    _server = None
    _port = None
    _mac = None

    def __init__(self, max, min, (server, port), mac):
        self._diffMax = max
        self._diffMin = min
        self._server = server
        self._port = port
        self._mac = mac

    def _generateUTC(self):
        return int((time.time() - random.randint(self._diffMin, self._diffMax) * 60) * 1e6)

    def generateURL(self):
        return self._archiveURLTemplate % (self._server, self._port, self._mac, self._generateUTC())


# RTSP global backoff timer, this is used to solve too many connection to server
# which makes the server think it is suffering DOS attack
class RtspBackOffTimer:
    _timerLock = threading.Lock()
    _globalTimerTable= dict()

    MAX_TIMEOUT = 4.0
    HALF_MAX_TIMEOUT = MAX_TIMEOUT / 2.0
    MIN_TIMEOUT = 0.01

    @classmethod
    def increase(cls, url):
        with cls._timerLock:
            if url in cls._globalTimerTable:
                if cls._globalTimerTable[url] > cls.HALF_MAX_TIMEOUT:
                    cls._globalTimerTable[url] = cls.MAX_TIMEOUT
                else:
                    cls._globalTimerTable[url] *= 2.0
            else:
                cls._globalTimerTable[url] = cls.MIN_TIMEOUT
        # it's not a problem if some other thread change cls._globalTimerTable[url] this moment -
        # let it sleep the newly corrected length,
        # but not lock other threads from access other cls._globalTimerTable elements while it sleeps
        time.sleep(cls._globalTimerTable[url])

    @classmethod
    def decrease(cls, url):
        with cls._timerLock:
            if url in cls._globalTimerTable:
                if cls._globalTimerTable[url] <= cls.MIN_TIMEOUT:
                    cls._globalTimerTable[url] = cls.MIN_TIMEOUT
                else:
                    cls._globalTimerTable[url] /= 2.0


class DummyLock(object):
    def __enter__(self):
        pass
    def __exit__(self,type,value,trace):
        pass


class RtspTcpBasic(object):
    _socket = None
    _addr = None
    _port = None
    _data = None
    _url = None
    _cid = None
    _sid = None
    _mac = None
    _uname = None
    _pwd = None
    _urlGen = None
    _resolution = None
    _lock = None
    _log  = None

    _rtspBasicTemplate = "\r\n".join((
        "PLAY %s RTSP/1.0",
        "CSeq: 2",
        "Range: npt=now-",
        "Scale: 1",
        "x-guid: %s",
        "Session:",
        "User-Agent: Network Optix",
        "x-play-now: true",
        "Authorization: Basic %s",
        "x-server-guid: %s", '', '')) # two '' -- to add two '\r\n' at the end

    _rtspDigestTemplate = "\r\n".join((
        "PLAY %s RTSP/1.0",
        "CSeq: 2",
        "Range: npt=now-",
        "Scale: 1",
        "x-guid: %s",
        "Session:",
        "User-Agent: Network Optix",
        "x-play-now: true",
        "%s",
        "x-server-guid: %s", '' ''))

    _digestAuthTemplate = 'Authorization:Digest username="%s",realm="%s",nonce="%s",uri="%s",response="%s",algorithm="MD5"'

    _skip_errno = [errno.EAGAIN, errno.EWOULDBLOCK] + ([errno.WSAEWOULDBLOCK] if hasattr(errno, 'WSAEWOULDBLOCK') else [])
    # There is no errno.WSAEWOULDBLOCK on Linux.

    def __init__(self, (addr, port), (mac, cid), sid, uname, pwd, urlGen, lock=None, log=None, socket_reraise=False):
        self._addr = addr
        self._port = int(port)
        self._urlGen = urlGen
        self._url = urlGen.generateURL()
        self._basic_auth = base64.encodestring('%s:%s' % (uname, pwd)).rstrip()
        self._data = self._rtspBasicTemplate % (self._url, cid, self._basic_auth, sid)

        self._cid = cid
        self._sid = sid
        self._mac = mac
        self._uname = uname
        self._pwd = pwd
        self._lock = lock if lock is not None else DummyLock()
        self._log = log
        self._socket_reraise = socket_reraise

    def add_prefered_resolution(self, resolution):
        self._resolution = resolution
        self._data = self._add_resolution_str(self._data)

    def _add_resolution_str(self, header):
        return ''.join((header[:-2], 'x-media-quality: ', self._resolution, "\r\n\r\n"))

    def _logError(self, msg):
        with self._lock:
            print msg
            if self._log is not None:
                print >>self._log, msg
                self._log.flush()

    def _checkEOF(self,data):
        return data.find("\r\n\r\n") > 0

    def _parseRelamAndNonce(self, reply):
        idx = reply.find("WWW-Authenticate")
        if idx < 0:
            return False
        # realm is fixed for our server - NO! it's chhanged already!
        realm = "NetworkOptix" #FIXME get the realm from the reply!

        # find the Nonce
        idx = reply.find("nonce=",idx)
        if idx < 0:
            return False
        idx_start = idx + 6
        idx_end = reply.find(",",idx)
        if idx_end < 0:
            idx_end = reply.find("\r\n",idx)
            if idx_end < 0:
                return False
        nonce = reply[idx_start + 1:idx_end - 1]

        return (realm,nonce)

    # This function only calculate the digest response
    # not the specific header field.  So another format
    # is required to format the header into the target
    # HTTP digest authentication

    def _calDigest(self, realm, nonce):
        return md5(':'.join((
            md5(':'.join((self._uname,realm,self._pwd))).hexdigest(),
            nonce,
            md5("PLAY:/" + self._mac).hexdigest()
        ))).hexdigest()

    def _formatDigestHeader(self,realm,nonce):
        return self._digestAuthTemplate % (self._uname,
            realm,
            nonce,
            "/%s" % (self._mac),
            self._calDigest(realm,nonce)
        )

    def _requestWithDigest(self,reply):
        ret = self._parseRelamAndNonce(reply)
        if ret == False:
            return reply
        auth = self._formatDigestHeader(ret[0],ret[1])
        data = self._rtspDigestTemplate % (self._url,
            self._cid,
            auth,
            self._sid)
        if self._resolution:
            data = self._add_resolution_str(data)
        self._request(data)
        return self._response()

    def _checkAuthorization(self,data):
        return data.find("Unauthorized") < 0

    def _request(self,data):
        while True:
            sz = self._socket.send(data)
            if sz == len(data):
                return
            else:
                data = data[sz:]

    def _response(self):
        ret = ""
        while True:
            try:
                data = self._socket.recv(256)
            except socket.error,e:
                RtspBackOffTimer.increase("%s:%d"%(self._addr,self._port))
                self._logError("Socket errror %s on URL %s" % (e, self._url))
                if self._socket_reraise:
                    raise
                return "This is not RTSP error but socket error: %s"%(e)

            RtspBackOffTimer.decrease("%s:%d"%(self._addr,self._port))

            if not data:
                self._logError("Empty RSTP response on URL %s" % self._url)
                return ret
            else:
                ret += data
                if self._checkEOF(ret):
                    return ret

    def __enter__(self):
        self._socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self._socket.connect((self._addr,self._port))
        self._request(self._data)
        reply = self._response()
        if not self._checkAuthorization(reply):
            reply = self._requestWithDigest(reply)
        return (reply, self._url)

    def __exit__(self,type,value,trace):
        self._socket.close()


Camera = namedtuple('Camera', ['physicalId', 'id', 'name', 'status'])
Camera.isOnline = lambda self: self.status in ('Online', 'Recording')


class SingleServerRtspTestBase(object):
    """ Provides:
        _fetchCameraList() called from __init__()
        _checkRtspRequest() that checks reply for "200 OK', reporting to stdout and into the log
        _lock is used to avoid different streams' output intersection
        _mkRtspStreamHandler and _mkRtspArchiveHandler - to simplify RtspTcpBasic object creation
    """
    _serverAddr = None
    _serverGUID = None
    _testCase = 0
    _username = None
    _password = None
    _archiveMax = 1
    _archiveMin = 5
    _log = None
    _lock = None

    def __init__(self, archiveMax, archiveMin, serverAddr, serverGUID, uname, pwd, log, lock):
        self._archiveMax = archiveMax
        self._archiveMin = archiveMin
        self._serverAddr = serverAddr
        self._serverAddrPair = self._serverAddr.split(':',1)
        self._serverGUID = quote_guid(serverGUID)
        self._username = uname
        self._password = pwd
        self._log = log
        self._lock = lock
        self._fetchCameraList()

    def _fetchCameraList(self):
        """Gets this server's GUID and filters out the only cameras that should be used on this server
           Fills self._cameraList
        """
        self._cameraList = []
        self._allCameraList = []
        self._cameraInfoTable = dict()
        obj = HttpRequest(self._serverAddr, 'ec2/getCamerasEx', params={'id': self._serverGUID}, printHttpError=Exception)
        for c in obj:
            if c["typeId"] == "{1657647e-f6e4-bc39-d5e8-563c93cb5e1c}":
                continue # Skip desktop
            if "name" in c and c["name"].startswith("ec2_test"):
                continue # Skip fake camera
            camera = Camera(c["physicalId"], c["id"], c["name"].encode('utf8'), c['status'])
            self._allCameraList.append(camera)
            if camera.isOnline:
                self._cameraList.append(camera)
                # c['name'] is used for output only and some pseudo-OSes (like Windows) don't have UTF-8 consoles :(
            self._cameraInfoTable[c["id"]] = c
        if not self._cameraList:
            msg = "Error: no active cameras found on server %s" % (self._serverAddr,)
            with self._lock:
                print msg
                self._log.writeFail(msg)

    def _checkReply(self, reply):
        idx = reply.find("\r\n")
        return False if idx < 0 else ("RTSP/1.0 200 OK" == reply[:idx])

    def _checkRtspRequest(self,c,reply):
        ret = None
        with self._lock:
            print "RTSP request on URL: %s issued!" % (reply[1])
            if not self._checkReply(reply[0]):
                print "RTSP request on Server %s failed" % (self._serverAddr)
                print reply
                print "Camera name: %s" % (c[2].encode('utf8'),)
                print "Camera Physical Id: %s" % (c[0])
                print "Camera Id: %s" % (c[1])

                self._log.writeFail("-------------------------------------------")
                self._log.writeFail("RTSP request on Server %s failed" % (self._serverAddr))
                self._log.writeFail("RTSP request URL %s issued" % (reply[1]))
                self._log.writeFail("Camera name: %s" % (c[2]))
                self._log.writeFail("Camera Physical Id: %s" % (c[0]))
                self._log.writeFail("Camera Id: %s" % (c[1]))
                self._log.writeFail("Detail RTSP reply protocol:\n\n%s" % (reply[0]))
                self._log.flushFail()
                ret = False
            else:
                self._log.writeOK("-------------------------------------")
                self._log.writeOK("RTSP request on Server %s with URL %s passed!" % (self._serverAddr, reply[1]))
                self._log.flushOK()
                print "Rtsp Test Passed!"
                ret = True
            print "-----------------------------------------------------"
            return ret

    def _mkRtspHandler(self, camera, urlGenerator, log=None, socket_reraise=False):
        return RtspTcpBasic(self._serverAddrPair, camera[0:2], self._serverGUID,
                            self._username, self._password,
                            urlGenerator, self._lock, log, socket_reraise)

    def _mkRtspStreamHandler(self, camera, log=None, socket_reraise=False):
        return self._mkRtspHandler(camera,
            RtspStreamURLGenerator(self._serverAddrPair, camera.physicalId),
            log, socket_reraise)

    def _mkRtspArchiveHandler(self, camera, log=None, socket_reraise=False):
        return self._mkRtspHandler(camera,
            RtspArchiveURLGenerator(self._archiveMax,self._archiveMin,self._serverAddrPair, camera.physicalId),
            log, socket_reraise)

    def run(self):
        raise NotImplementedError("ERROR: the abstract method SingleServerRtspTestBase.run isn't overriden in %s" % self.__class__)

# ===================================
# RTSP test
# ===================================
# --- finite test ---

class FiniteSingleServerRtspTest(SingleServerRtspTestBase):
    _log = None
    _testCase = 0
    def __init__(self, archiveMax, archiveMin, serverAddr, serverGUID, testCase, uname, pwd, log, lock):
        self._testCase = testCase
        SingleServerRtspTestBase.__init__(self, archiveMax, archiveMin, serverAddr, serverGUID,
                                          uname, pwd, log, lock)

    def _testMain(self):
        if self._cameraList:
            # Streaming version RTSP test
            c = random.choice(self._cameraList)
            with self._mkRtspStreamHandler(c) as reply:
                self._checkRtspRequest(c, reply)

        c = random.choice(self._allCameraList)
        with self._mkRtspArchiveHandler(c) as reply:
            self._checkRtspRequest(c, reply)

    def run(self):
        for _ in xrange(self._testCase):
            self._testMain()


class FiniteRtspTest(object):
    """ For each server perform FiniteSingleServerRtspTest
    """

    def __init__(self, cluster, testSize, userName, passWord, archiveMax, archiveMin):
        self._cluster = cluster
        self._testCase = testSize
        self._username = userName
        self._password = passWord
        self._archiveMax = archiveMax # max difference
        self._archiveMin = archiveMin # min difference
        self._lock = threading.Lock()

    def test(self):
        thPool = []
        print "-----------------------------------"
        print "Finite RTSP test starts"
        print "The failed detail result will be logged in rtsp.log file"

        for i, serverAddr in enumerate(self._cluster.clusterTestServerList):
            serverAddrGUID = self._cluster.clusterTestServerUUIDList[i][0]
            log = RtspLog(serverAddr)

            tar = FiniteSingleServerRtspTest(self._archiveMax, self._archiveMin, serverAddr, serverAddrGUID,
                                             self._testCase, self._username, self._password, log, self._lock)

            th = threading.Thread(target = tar.run)
            th.start()
            thPool.append((th, log))

        # Join the thread
        for t in thPool:
            t[0].join()
            t[1].close()

        print "Finite RTSP test ends"
        print "-----------------------------------"


# --- infinite test ---

class InfiniteSingleServerRtspTest(SingleServerRtspTestBase):
    _flag = None

    def __init__(self, archiveMax, archiveMin, serverAddr, serverGUID, uname, pwd, log, lock, flag):
        SingleServerRtspTestBase.__init__(self,
                                          archiveMax, archiveMin, serverAddr, serverGUID,
                                          uname, pwd, log, lock)
        self._flag = flag

    def run(self):
        l = self._serverAddr.split(":")
        results = {False: 0, True: 0} # count results, key is a self._checkRtspRequest call result
        while self._flag.isOn():
            for c in self._allCameraList:
                # Streaming version RTSP test
                if c.isOnline():
                    with self._mkRtspStreamHandler(c) as reply:
                        results[self._checkRtspRequest(c, reply)] += 1

                with self._mkRtspArchiveHandler(c) as reply:
                    results[self._checkRtspRequest(c, reply)] += 1

        print "-----------------------------------"
        print "On server %s\nRTSP Passed: %d\nRTSP Failed: %d" % (self._serverAddr, results[True], results[False])
        print "-----------------------------------\n"


class InfiniteRtspTest(object):
    def __init__(self, cluster, userName, passWord, archiveMax, archiveMin):
        self._cluster = cluster
        self._username = userName
        self._password = passWord
        self._archiveMax = archiveMax # max difference
        self._archiveMin = archiveMin # min difference
        self._lock = threading.Lock()
        self._flag = True

    def isOn(self):
        return self._flag

    def turnOff(self):
        self._flag = False

    def _onInterrupt(self,a,b):
        self.turnOff()

    def test(self):
        thPool = []

        print "-------------------------------------------"
        print "Infinite RTSP test starts"
        print "You can press CTRL+C to interrupt the tests"
        print "The failed detail result will be logged in rtsp.log file"

        # Setup the interruption handler
        signal.signal(signal.SIGINT,self._onInterrupt)

        for i, serverAddr in enumerate(self._cluster.clusterTestServerList):
            serverAddrGUID = self._cluster.clusterTestServerUUIDList[i][0]
            log = RtspLog(serverAddr)

            tar = InfiniteSingleServerRtspTest(self._archiveMax, self._archiveMin,
                                               serverAddr, serverAddrGUID,
                                               self._username, self._password,
                                               log, self._lock, self)

            th = threading.Thread(target=tar.run)
            th.start()
            thPool.append((th, log))


        # This is a UGLY work around that to allow python get the interruption
        # while execution.  If I block into the join, python seems never get
        # interruption there.
        while self.isOn():
            try:
                time.sleep(0.5)
            except:
                self.turnOff()
                break

        # Afterwards join them
        for t in thPool:
            t[0].join()
            t[1].close()

        print "Infinite RTSP test ends"
        print "-------------------------------------------"


class RtspTestSuit(object):

    def __init__(self, cluster):
        self._cluster = cluster
        self._config = cluster.getConfig()
        #if not self._cluster.unittestRollback:
        #    self._cluster.init_rollback()

    def run(self):
        username = self._config.get("General","username")
        password = self._config.get("General","password")
        testSize = self._config.getint("Rtsp","testSize")
        diffMax = self._config.getint("Rtsp","archiveDiffMax")
        diffMin = self._config.getint("Rtsp","archiveDiffMin")

        if testSize < 0 :
            InfiniteRtspTest(self._cluster, username, password, diffMax, diffMin).test()
        else:
            FiniteRtspTest(self._cluster, testSize, username, password, diffMax, diffMin).test()


# ================================================================================================
# RTSP performance Operations
# ================================================================================================

class SingleServerRtspPerf(SingleServerRtspTestBase):
    _archiveStreamRate = DEFAULT_ARCHIVE_STREAM_RATE
    _timeoutMax = 0 # whole number of milliseconds
    _timeoutMin = 0 # whole number of milliseconds
    _perfLog = None
    _threadNum = 0
    _exitFlag = None
    _threadPool = []

    _archiveNumOK = 0
    _archiveNumFail = 0
    _archiveNumTimeout = 0
    _archiveNumClose = 0
    _archiveNumSocketError = 0
    _streamNumOK = 0
    _streamNumFail = 0
    _streamNumTimeout = 0
    _streamNumClose = 0
    _streamNumSocketError = 0
    _need_dump = False
    _rtspTimeout = 3
    _httpTimeout = 5
    _threadStartSpacing = 0
    _socketCloseGrace = 0
    _camerasStartGrace = 8
    _liveDataPart = 50

    _startTime = 0

    @classmethod
    def set_global(cls, name, value):
        setattr(cls, '_'+name, value)

    def __init__(self, archiveMax, archiveMin, serverAddr, guid, username, password, threadNum, flag, lock):
        SingleServerRtspTestBase.__init__(self,
                                          archiveMax, archiveMin,
                                          serverAddr, guid,
                                          username, password,
                                          RtspLog(serverAddr),
                                          lock)
        self._threadNum = threadNum
        self._exitFlag = flag
        # Initialize the performance log
        print "DEBUG: A: %s" % self._serverAddrPair
        self._perfLog = open("%s_%s.perf.rtsp.log" % tuple(self._serverAddrPair),"w+")
        # Order cameras to start recording and preserve a time gap for starting
        self._camerasReadyTime = time.time() + (self._camerasStartGrace if self._startRecording() else 0)

    def _startRecording(self):
        "Start recording for all available cameras." #TODO probably it's good to place it into SingleServerRtspTestBase and call it there.
        cameras = []
        for ph_id, id, name, status in self._cameraList:
            if status != 'Recording':
                attr_data = CAMERA_ATTR_EMPTY.copy()
                attr_data['cameraID'] = id
                attr_data['scheduleEnabled'] = True
                attr_data['scheduleTasks'] = FULL_SCHEDULE_TASKS
                cameras.append(attr_data)

        if cameras:
            response = urllib2.urlopen(urllib2.Request(
                    "http://%s/ec2/saveCameraUserAttributesList" % (self._serverAddr),
                    data=json.dumps(cameras),
                    headers={'Content-Type': 'application/json'}),
                    timeout=self._httpTimeout
            )
            if response.getcode() != 200:
                raise Exception("Error calling /ec2/saveCameraUserAttributesList at server %s: %s" % (self._serverAddr, response.getcode()))
        return len(cameras) > 0

    def _timeoutRecv(self, socket, rate_limit, timeout):
        """ Read some bytes from the socket, no more then RATE, no longer then TIMEOUT
            If RATE == -1, just read one portion of data
        """
        socket.setblocking(0)
        buf = []
        total_size = 0
        finish = time.time() + timeout

        try:
            while time.time() < finish:
                # recording the time for fetching an event
                ready = select.select([socket], [], [], timeout)
                if ready[0]:
                    data = socket.recv(1024*16) if rate_limit < 0 else socket.recv(rate_limit)
                    if rate_limit == -1:
                        return data
                    buf.append(data)
                    total_size += len(data)
                    if total_size > rate_limit:
                        extra = total_size - rate_limit * (time.time() - self._startTime)
                        if extra > 0:
                            time.sleep(extra/rate_limit) # compensate the rate of packet size here
                        return ''.join(buf)
                else:
                    # timeout reached
                    return None
            # time limit reached
            return ''.join(buf)
        finally:
            socket.setblocking(1)

    def _dumpArchiveHelper(self, c, tcp_rtsp, timeout, dump_file):
        self._startTime = time.time()
        finish = self._startTime + timeout
        while time.time() < finish:
            try:
                data = self._timeoutRecv(tcp_rtsp._socket, self._archiveStreamRate, self._rtspTimeout)
                if dump_file is not None:
                    dump_file.write(data)
                    dump_file.flush()
            except Exception:
                traceback.print_exc()
            else:
                if data is None or data == '':
                    with self._lock:
                        print "--------------------------------------------"
                        if data is None:
                            print "The RTSP url %s no archive data response for %s seconds" % (
                                tcp_rtsp._url, self._rtspTimeout)
                        else:
                            print "The RTSP url %s connection has been closed by server after %.2f seconds" % (
                                tcp_rtsp._url, time.time() - self._startTime)
                        self._perfLog.write("--------------------------------------------\n")
                        if data is None:
                            self._perfLog.write("! The RTSP/RTP url %s no data response for %s seconds\n" % (
                                tcp_rtsp._url, self._rtspTimeout))
                        else:
                            self._perfLog.write("! The RTSP/RTP url %s connection has been CLOSED by server\n" % (
                                tcp_rtsp._url,))
                        self._perfLog.write("Camera name:%s\n" % c.name)
                        self._perfLog.write("Camera Physical Id:%s\n" % c.physicalId)
                        self._perfLog.write("Camera Id:%s\n" % c.id)
                        self._perfLog.write("--------------------------------------------\n")
                        self._perfLog.flush()
                    if data is None:
                        self._archiveNumTimeout += 1
                    else:
                        self._archiveNumClose += 1
                    self._archiveNumOK -= 1
                    return
        with self._lock:
            print "--------------------------------------------"
            print "The %.3f seconds RTP sink finished on RTSP url %s" % (timeout,tcp_rtsp._url)

    def _dumpStreamHelper(self, c, tcp_rtsp, timeout, dump_file):
        self._startTime = time.time()
        finish = self._startTime + timeout
        while time.time() < finish:
            try:
                data = self._timeoutRecv(tcp_rtsp._socket, -1, self._rtspTimeout)
                if dump_file is not None:
                    dump_file.write(data)
                    dump_file.flush()
            except Exception:
                traceback.print_exc()
            else:
                if data is None or data == '':
                    with self._lock:
                        print "--------------------------------------------"
                        if data is None:
                            print "The RTSP url %s no live data response for %s seconds" % (
                                tcp_rtsp._url, self._rtspTimeout)
                        else:
                            print "The RTSP url %s connection has been closed by server after %.2f seconds" % (
                                tcp_rtsp._url, time.time() - self._startTime)
                        self._perfLog.write("--------------------------------------------\n")
                        if data is None:
                            self._perfLog.write("! The RTSP/RTP url %s no data response for %s seconds\n" % (
                                tcp_rtsp._url, self._rtspTimeout))
                        else:
                            self._perfLog.write("! The RTSP/RTP url %s connection has been CLOSED by server\n" % (
                                tcp_rtsp._url,))
                        self._perfLog.write("Camera name:%s\n" % c.name)
                        self._perfLog.write("Camera Physical Id:%s\n" % c.physicalId)
                        self._perfLog.write("Camera Id:%s\n" % c.id)
                        self._perfLog.write("--------------------------------------------\n")
                        self._perfLog.flush()
                    if data is None:
                        self._streamNumTimeout += 1
                    else:
                        self._streamNumClose += 1
                    self._streamNumOK -= 1
                    return
        with self._lock:
            print "--------------------------------------------"
            print "The %.3f seconds RTP sink finished on RTSP url %s" % (timeout, tcp_rtsp._url)

    def _dump(self,c, tcp_rtsp, timeout, helper):
        if self._need_dump:
            with open(_buildUrlPath(tcp_rtsp._url),"w+") as f:
                helper(c, tcp_rtsp, timeout, f)
        else:
            helper(c, tcp_rtsp, timeout, None)

    def _makeDataReceivePeriod(self):
        return random.randint(self._timeoutMin, self._timeoutMax) / 1000.0

    # Represent a streaming TASK on the camera
    def _main_streaming(self, c):
        obj = self._mkRtspStreamHandler(c, self._perfLog, socket_reraise=True)
        obj.add_prefered_resolution(random.choice(['low', 'high']))

        try:
            with obj as reply:
                # 1.  Check the reply here
                if self._checkRtspRequest(c,reply):
                    self._dump(c, tcp_rtsp=obj, timeout=self._makeDataReceivePeriod(), helper=self._dumpStreamHelper)
                    self._streamNumOK += 1
                else:
                    self._streamNumFail += 1
        except socket.error:
            print "--------------------------------------------"
            print "The RTSP url %s test fails with the socket error %s" % (obj._url, sys.exc_info() )
            self._streamNumSocketError += 1

    def _main_archive(self, c):
        obj = self._mkRtspArchiveHandler(c, self._perfLog, socket_reraise=True)
        obj.add_prefered_resolution(random.choice(['low', 'high']))
        try:
            with obj as reply:
                # 1.  Check the reply here
               if self._checkRtspRequest(c,reply):
                   self._dump(c, tcp_rtsp=obj, timeout=self._makeDataReceivePeriod(), helper=self._dumpArchiveHelper)
                   self._archiveNumOK += 1
               else:
                   self._archiveNumFail += 1
        except socket.error:
            print "--------------------------------------------"
            print "The RTSP url %s test fails with the socket error %s" % (obj._url, sys.exc_info() )
            self._archiveNumSocketError += 1

    def _threadMain(self, num):
        while self._exitFlag.isOn():
            # choose a random camera in the server list
            c = random.choice(self._cameraList)
            if random.randint(1,100) <= self._liveDataPart:
                self._main_streaming(c)
            else:
                self._main_archive(c)
            if self._socketCloseGrace:
                time.sleep(self._socketCloseGrace)

    def join(self):
        for th in self._threadPool:
            th.join()
        self._perfLog.close()
        print "======================================="
        print "Server: %s" % (self._serverAddr)
        print "Number of threads: %s" % self._threadNum
        print "rtspTimeout value: %s" % self._rtspTimeout
        print "Archive Success Number: %d" % self._archiveNumOK
        print "Archive Failed Number: %d" % self._archiveNumFail
        print "Archive Timed Out Number: %d" % self._archiveNumTimeout
        print "Archive Server Closed Number: %d" % self._archiveNumClose
        print "Archive Socket Error Number: %d" % self._archiveNumSocketError
        print "Stream Success Number:%d" % self._streamNumOK
        print "Stream Failed Number:%d" % self._streamNumFail
        print "Stream Timed Out Number: %d" % self._streamNumTimeout
        print "Stream Server Closed Number: %d" % self._streamNumClose
        print "Stream Socket Error Number: %d" % self._streamNumSocketError
        print "======================================="

    def run(self, need_dump=False):
        if not self._cameraList:
            if self._allCameraList:
                print "All cameras on cerver %s are offline!" % (self._serverAddr,)
            else:
                print "The camera list on server: %s is empty!" % (self._serverAddr,)
            print "Do nothing and abort!"
            return False
        dt = self._camerasReadyTime - time.time()
        if dt > 0:
            print "DEBUG: cameras could be unready, sleep %.2f seconds" % dt
            time.sleep(dt)

        self._need_dump = need_dump
        for _ in xrange(self._threadNum):
            th = threading.Thread(target=self._threadMain, args=(_,))
            th.start()
            self._threadPool.append(th)
            if self._threadStartSpacing:
                time.sleep(self._threadStartSpacing)
        return True


class RtspPerf(object):
    _perfServer = []
    _lock = threading.Lock()
    _exit = False

    def __init__(self, cluster):
        self._cluster = cluster
        self._config = config = cluster.getConfig()
        self.threadNumbers = self._config.get("Rtsp","threadNumbers").split(",")
        if len(self.threadNumbers) != len(cluster.clusterTestServerList):
            self.run = self._cantRun # substitute the `run` method
            return

        #RtspTcpBasic.set_close_timeout_global(config.getint_safe("Rtsp", "rtspCloseTimeout", 5))
        SingleServerRtspPerf.set_global('timeoutMin', config.getint("Rtsp","timeoutMin") * 1000)
        SingleServerRtspPerf.set_global('timeoutMax', config.getint("Rtsp","timeoutMax") * 1000)
        SingleServerRtspPerf.set_global('rtspTimeout', config.getint_safe("Rtsp", "rtspTimeout", 3))
        SingleServerRtspPerf.set_global('httpTimeout', config.getint_safe("Rtsp", "httpTimeout", 5))
        SingleServerRtspPerf.set_global('camerasStartGrace', config.getint_safe("Rtsp", "camerasStartGrace", 5))
        SingleServerRtspPerf.set_global('threadStartSpacing', config.getfloat_safe("Rtsp", "threadStartSpacing", 0))
        SingleServerRtspPerf.set_global('socketCloseGrace', config.getfloat_safe("Rtsp", "socketCloseGrace", 0))
        SingleServerRtspPerf.set_global('liveDataPart', config.getint_safe("Rtsp", "liveDataPart", 50))

        rate = config.get_safe("Rtsp", "archiveStreamRate", None)
        if rate is not None:
            SingleServerRtspPerf.set_global('archiveStreamRate', parse_size(rate))

    def isOn(self):
        return not self._exit

    def turnOff(self):
        self._exit = True

    def _onInterrupt(self,a,b):
        self.turnOff()

    def _cantRun(self):
        print "The threadNumbers in Rtsp section doesn't match the size of the servers in serverList"
        print "threadNumbers = %s" % self.threadNumbers
        print "clusterTestServerList = %s" % self._cluster.clusterTestServerList
        print "Every server MUST be assigned with a correct thread Numbers"
        print "RTSP Pressure test failed"

    def initTest(self):
        archiveMax = self._config.getint("Rtsp","archiveDiffMax")
        archiveMin = self._config.getint("Rtsp","archiveDiffMin")
        username = self._config.get("General","username")
        password = self._config.get("General","password")

        # Let's add those RtspSinglePerf
        for i, serverAddr in enumerate(self._cluster.clusterTestServerList):
            serverGUID = self._cluster.clusterTestServerUUIDList[i][0]
            serverThreadNum = int(self.threadNumbers[i])

            self._perfServer.append(SingleServerRtspPerf(
                    archiveMax,archiveMin,
                    serverAddr,serverGUID,
                    username,password,
                    serverThreadNum,self,self._lock))

        return True

    def run(self, need_dump=False):
        self.initTest()
        print "---------------------------------------------"
        print "Start to run RTSP pressure test now!"
        print "Press CTRL+C to interrupt the test!"
        print "The exceptional cases are stored inside of server_end_point.rtsp.perf.log"

        # Add the signal handler
        signal.signal(signal.SIGINT,self._onInterrupt)

        for e in self._perfServer:
            if not e.run(need_dump):
                return

        while self.isOn():
            try:
                time.sleep(1)
            except Exception:
                break
            except KeyboardInterrupt:
                break

        # all threads should stop since self.isOn() returns False
        for e in self._perfServer:
            e.join()

        print "RTSP performance test done,see log for detail"
        print "---------------------------------------------"


if __name__ == '__main__':
    print "%s not supposed to be executed alone." % (__file__,)
