"""Contains common tools to handle virtual boxes based mediaserver functional testing.
"""
__author__ = 'Danil Lavrentyuk'
import subprocess
import unittest
import urllib
import urllib2
import time
import json
import traceback

from functest_util import ClusterLongWorker, unquote_guid, Version

NUM_SERV=2
SERVER_UP_TIMEOUT = 20 # seconds, timeout for server to start to respond requests

__all__ = ['boxssh', 'FuncTestCase', 'FuncTestError', 'RunTests']

class FuncTestError(AssertionError):
    pass


def boxssh(box, command):
    return subprocess.check_output(
        ['./vssh.sh', box, 'sudo'] + list(command),
        shell=False, stderr=subprocess.STDOUT
    )


class TestLoader(unittest.TestLoader):

    def load(self, testclass, testset, config):
        testclass.config = config
        names = getattr(testclass, testset, None)
        if names is not None:
            print "[Preparing %s tests]" % testset
            testclass.testset = testset
            return self.suiteClass(map(testclass, names))
        else:
            print "ERROR: No test set '%s' found!" % testset


def RunTests(testclass, config):
    testclass.init_suits()
    return all( [
            unittest.TextTestRunner(verbosity=2, failfast=True).run(
                TestLoader().load(testclass, suit_name, config)
            ).wasSuccessful()
            for suit_name in testclass.iter_suits()
        ] )


class FuncTestCase(unittest.TestCase):
    """A base class for mediaserver functional tests using virtual boxes
    """
    config = None
    num_serv = NUM_SERV
    testset = None
    guids = {}
    _configured = False
    _stopped = set()
    _worker = None
    _suits = ()
    _init_suits_done = False
    _serv_version = None  # here I suppose that all servers being created from the same image have the same version
    before_2_5 = False

    @classmethod
    def setUpClass(cls):
        if cls.config is None:
            raise FuncTestError("%s hasn't been configured" % cls.__name__)
        if cls.num_serv is None:
            raise FuncTestError("%s hasn't got a correct num_serv value" % cls.__name__)
        if not cls._configured:
            cls.sl = cls.config.get("General","serverList").split(',')
            cls._worker = ClusterLongWorker(cls.num_serv)
            cls._configured = True
        if len(cls.sl) < cls.num_serv:
            raise FuncTestError("not enough servers configured to test time synchronization")
        if len(cls.sl) > cls.num_serv:
            cls.sl[cls.num_serv:] = []
        cls.hosts = [addr.split(':')[0] for addr in cls.sl]
        print "Server list: %s" % cls.sl
        cls._worker.startThreads()

    @classmethod
    def tearDownClass(cls):
        # and test if they work in parallel!
        for host in cls._stopped:
            print "Restoring mediaserver on %s" % host
            cls.class_call_box(host, 'start', 'networkoptix-mediaserver')
        cls._stopped.clear()
        cls._worker.stopWork()

    ################################################################################

    @classmethod
    def _check_suits(cls):
        if not cls._suits:
            raise RuntimeError("%s's test suits list is empty!" % cls.__name__)

    @classmethod
    def iter_suits(cls):
        cls._check_suits()
        return (s[0] for s in cls._suits)

    @classmethod
    def init_suits(cls):
        if cls._init_suits_done:
            return
        cls._check_suits()
        for name, tests in cls._suits:
            setattr(cls, name, tests)
        cls._init_suits_done = True

    ################################################################################

    def _call_box(self, box, *command):
        #print "%s: %s" % (box, ' '.join(command))
        try:
            return boxssh(box, command)
        except subprocess.CalledProcessError, e:
            self.fail("Box %s: remote command `%s` failed at %s with code. Output:\n%s" %
                      (box, ' '.join(command), e.returncode, e.output))


    @classmethod
    def class_call_box(cls, box, *command):
        try:
            return boxssh(box, command)
        except subprocess.CalledProcessError, e:
            print ("Box %s: remote command `%s` failed at %s with code. Output:\n%s" %
                      (box, ' '.join(command), e.returncode, e.output))
            return ''

    def _get_init_script(self, boxnum):
        "Return init script's name and arguments for it. It should return a tupple."
        return () # the default is no script to run

    def _stop_and_init(self, box, num):
        print "Stopping box %s" % box
        self._mediaserver_ctl(box, 'stop')
        time.sleep(0)
        init_script = self._get_init_script(num)
        if init_script:
            self._call_box(box, *init_script)
        print "Box %s stopped and ready" % box

    def _prepare_test_phase(self, method):
        for num, box in enumerate(self.hosts):
            self._worker.enqueue(method, (box, num))
        self._worker.joinQueue()
        self._servers_th_ctl('start')
        self._wait_servers_up()
        if self._serv_version is None:
            self._get_version()
            if self._serv_version < Version("2.5.0"):
                type(self).before_2_5 = True
        print "Servers are ready. Server servion = %s" % self._serv_version

    def _mediaserver_ctl(self, box, cmd):
        "Perform a service control command for a mediaserver on one of boxes"
        self._call_box(box, cmd, 'networkoptix-mediaserver')
        if cmd == 'stop':
            self._stopped.add(box)
        elif cmd in ('start', 'restart'): # for 'restart' - just in case it was off unexpectedly
            self._stopped.discard(box)

    def _servers_th_ctl(self, cmd):
        "Perform the same service control command for all mediaservers in parallel (using threads)."
        for box in self.hosts:
            self._worker.enqueue(self._mediaserver_ctl, (box, cmd))
        self._worker.joinQueue()

    def _json_loads(self, text, url):
        if text == '':
            return None
        try:
            return json.loads(text)
        except ValueError, e:
            self.fail("Error parsing response for %s: %s.\nResponse:%s" % (url, e, text))

    def _prepare_request(self, host, func, data=None, headers=None):
        if type(host) is int:
            host = self.sl[host]
        url = "http://%s/%s" % (host, func)
        if data is None:
            if headers:
                return urllib2.Request(url, headers=headers)
            else:
                return urllib2.Request(url)
        else:
            if headers:
                headers.setdefault('Content-Type', 'application/json')
            else:
                headers = {'Content-Type': 'application/json'}
            return urllib2.Request(url, data=json.dumps(data), headers=headers)

    def _server_request_nofail(self, host, func, data=None, headers=None, timeout=None, with_debug=False):
        "Sends request that don't fail on exception or non-200 return code."
        req = self._prepare_request(host, func, data)
        try:
            response = urllib2.urlopen(req, **({} if timeout is None else {'timeout': timeout}))
        except Exception, e:
            if with_debug:
                print "Host %s, call %s, exception: %s" % (host, func, e)
            return None
        if response.getcode() != 200:
            if with_debug:
                print "Host %s, call %s, HTTP code: %s" % (host, func, response.getcode())
            return None
        # but it could fail here since with code == 200 the response must be parsable or empty
        answer = self._json_loads(response.read(), req.get_full_url())
        response.close()
        return answer

    def _server_request(self, host, func, data=None, headers=None, timeout=None):
        req = self._prepare_request(host, func, data, headers)
        url = req.get_full_url()
        try:
            response = urllib2.urlopen(req, **({} if timeout is None else {'timeout': timeout}))
        except urllib2.URLError , e:
            self.fail("%s request failed with %s" % (url, e))
        except Exception, e:
            self.fail("%s request failed with exception:\n%s\n\n" % (url, traceback.format_exc()))
        self.assertEqual(response.getcode(), 200, "%s request returns error code %d" % (url, response.getcode()))
        answer = self._json_loads(response.read(), url)
        response.close()
        return answer

    def _wait_servers_up(self, servers=None):
        endtime = time.time() + SERVER_UP_TIMEOUT
        tocheck = servers or set(range(self.num_serv))
        while tocheck and time.time() < endtime:
            print "%s, %s" % (endtime - time.time(), str(tocheck))
            for num in tocheck.copy():
                data = self._server_request_nofail(num, 'ec2/testConnection', timeout=1, with_debug=False)
                if data is None:
                    continue
                self.guids[num] = unquote_guid(data['ecsGuid'])
                tocheck.discard(num)
            if tocheck:
                time.sleep(0.5)
        if tocheck:
            self.fail("Servers startup timed out: %s" % (', '.join(map(str, tocheck))))

    def _get_version(self):
        """ Returns mediaserver version as reported in api/moduleInformation.
        If it hasn't been get earlie, perform the 'api/moduleInformation' request.

        """
        if self._serv_version is None:
            data = self._server_request(0, 'api/moduleInformation')
            type(self)._serv_version = Version(data["reply"]["version"])
        return self._serv_version

    def _change_system_name(self, host, newName):
        res = self._server_request(host, 'api/configure?systemName='+urllib.quote_plus(newName))
        self.assertEqual(res['error'], "0",
            "api/configure failed to set a new systemName %s for the server %s: %s" % (newName, host, res['errorString']))



    def setUp(self):
        "Just prints \n after unittest module prints a test name"
        print
    #    print "*** Setting up: %s" % self._testMethodName  # may be used for debug ;)
    ####################################################
