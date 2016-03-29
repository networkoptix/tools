"""Contains common tools to handle virtual boxes based mediaserver functional testing.
Including FuncTestCase - the base class for all mediaserver functional test classes.
"""
__author__ = 'Danil Lavrentyuk'
import sys
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

__all__ = ['boxssh', 'FuncTestCase', 'FuncTestError', 'RunTests', 'LegacyTestWrapper']

class FuncTestError(AssertionError):
    pass


def boxssh(box, command):
    return subprocess.check_output(
        ['./vssh.sh', box, 'sudo'] + list(command),
        shell=False, stderr=subprocess.STDOUT
    )


class TestLoader(unittest.TestLoader):

    def load(self, testclass, testset, config, *args):
        names = getattr(testclass, testset, None)
        if names is not None:
            print "[Preparing %s tests]" % testset
            testclass.testset = testset
            return self.suiteClass(map(testclass, names))
        else:
            print "ERROR: No test set '%s' found!" % testset


def RunTests(testclass, config, *args):
    """
    Runs all test suits from the testclass which is derived from FuncTestCase
    :type testclass: FuncTestCase
    :type config: FtConfigParser
    """
    #print "DEBUG: run test class %s" % testclass
    try:
        try:
            testclass.globalInit(config)
        except Exception as err:
            print "FAIL: %s initialization failed: %s!" % (testclass.__name__, err)
            return
        return all( [
                unittest.TextTestRunner(verbosity=2, failfast=testclass.isFailFast(suit_name))
                .run(
                    TestLoader().load(testclass, suit_name, config, *args)
                ).wasSuccessful()
                for suit_name in testclass.iter_suits()
            ] )
    finally:
        testclass.globalFinalise()



class FuncTestCase(unittest.TestCase):
    # TODO: describe this class logic!
    """A base class for mediaserver functional tests using virtual boxes.
    """
    config = None
    num_serv = NUM_SERV
    testset = None
    _initialised = False
    _configured = False
    _stopped = set()
    _worker = None
    _suits = ()
    _init_suits_done = False
    _serv_version = None  # here I suppose that all servers being created from the same image have the same version
    before_2_5 = False # TODO remove it!
    _test_name = '<UNNAMED!>'
    _test_key = 'NONE'  # a name to pass as an argument to commands
    _init_script = 'ctl.sh'  # clear it in a subclass to disable
    _clear_script = ''  # clear it in a subclass to disable
    _global_clear_script = 'ctl.sh'  # called only after all test suits of this class performed
    sl = []
    hosts = []
    guids = []

    @classmethod
    def globalInit(cls, config):
        print "========================================="
        print
        if config is None:
            raise FuncTestError("%s can't be configured, config is None!" % cls.__name__)
        cls.config = config
        cls.init_suits()
        if not cls.num_serv:
            raise FuncTestError("%s hasn't got a correct num_serv value" % cls.__name__)
        cls._worker = ClusterLongWorker(cls.num_serv)
        cls._worker.startThreads()
        # this lines should be executed once per class
        cls.sl = cls.config.rtget("ServerList")[:]
        if len(cls.sl) < cls.num_serv:
            raise FuncTestError("not enough servers configured to run %s tests.\n(num_serv=%s, list=%s)" % (
                cls._test_name, cls.num_serv, cls.sl))
        if len(cls.sl) > cls.num_serv:
            cls.sl[cls.num_serv:] = []
        cls.guids = ['' for _ in cls.sl]
        cls.hosts = [addr.split(':')[0] for addr in cls.sl]
        #print "Server list: %s" % cls.sl
        cls._configured = True

    @classmethod
    def globalFinalise(cls):
        cls._clear_box(cls._global_clear_script, cls._global_clear_script_args)
        if cls._worker:
            cls._worker.stopWork()
            cls._worker = None

    @classmethod
    def setUpClass(cls):
        print "========================================="
        if cls.testset:
            print "%s Test Start: %s" % (cls._test_name, cls.testset)
        else:
            print "%s Test Start" % cls._test_name
        # cls.config should be assigned in TestLoader.load()

    @classmethod
    def tearDownClass(cls):
        # and test if they work in parallel!
        if cls._clear_script:
            cls._clear_box(cls._clear_script, cls._clear_script_args)
        for host in cls._stopped:  # do we need it?
            print "Restoring mediaserver on %s" % host
            cls.class_call_box(host, '/vagrant/safestart.sh', 'networkoptix-mediaserver')
        cls._stopped.clear()
        print "%s Test End" % cls._test_name
        print "========================================="

    @classmethod
    def isFailFast(cls, suit_name=""):
        # it could depend on the specific suit
        return True

    ################################################################################
    # These 3 methods used in a caller (see the RunTests and functest.CallTest funcions)
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
        "Called by RunTests, prepares attributes with suits names contaning test cases names"
        if cls._init_suits_done:
            return
        cls._check_suits()
        for name, tests in cls._suits:
            setattr(cls, name, tests)
        cls._init_suits_done = True

    ################################################################################

    def _call_box(self, box, *command):
        #sys.stdout.write("_call_box: %s: %s\n" % (box, ' '.join(command)))
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
            print ("ERROR: Box %s: remote command `%s` failed at %s with code. Output:\n%s" %
                      (box, ' '.join(command), e.returncode, e.output))
            return ''

    @classmethod
    def _clear_box(cls, script, args_method):
        if script:
            for num in xrange(cls.num_serv):
                try:
                    if cls._need_clear_box(num):
                        args = args_method(num)
                        print "Remotely calling at box %s: %s %s" % (num, script, ' '.join(args))
                        cls.class_call_box(cls.hosts[num], '/vagrant/' + script, *args)
                except Exception as err:
                    print "ERROR: _clear_box with %s for box %s: %s" % (script, num, err)

    @classmethod
    def _need_clear_box(cls, num):
        return len(cls.hosts) > num  # since it could be called with initialization incomplete

    @classmethod
    def _clear_script_args(cls, num):
        return (str(num), )

    @classmethod
    def _global_clear_extra_args(cls, num):
        return ()

    @classmethod
    def _global_clear_script_args(cls, num):
        return (cls._test_key, 'clear') + cls._global_clear_extra_args(num)

    def _init_script_args(self, boxnum):
        "Return init script's arguments as a tupple, to add after the first two: self._test_key and 'init'"
        return ()

    #def _call_init_script(self, box, num):

    def _stop_and_init(self, box, num):
        sys.stdout.write("Stopping box %s\n" % box)
        self._mediaserver_ctl(box, 'safe-stop')
        time.sleep(0)
        if self._init_script:
            self._call_box(box, '/vagrant/' + self._init_script,  self._test_key, 'init', *self._init_script_args(num))
        sys.stdout.write("Box %s is ready\n" % box)

    def _prepare_test_phase(self, method):
        self._worker.clearOks()
        for num, box in enumerate(self.hosts):
            self._worker.enqueue(method, (box, num))
        self._worker.joinQueue()
        self.assertTrue(self._worker.allOk(), "Failed to prepare test phase")
        self._wait_servers_up()
        if self._serv_version is None:
            self._get_version()
            if self._serv_version < Version("2.5.0"):
                type(self).before_2_5 = True
        print "Servers are ready. Server vervion = %s" % self._serv_version

    def _mediaserver_ctl(self, box, cmd):
        "Perform a service control command for a mediaserver on one of boxes"
        if cmd == 'safe-stop':
            rcmd = '/vagrant/safestop.sh'
        elif cmd == 'safe-start':
            rcmd = '/vagrant/safestart.sh'
        else:
            rcmd = cmd
        self._call_box(box, rcmd, 'networkoptix-mediaserver')
        if cmd in ('stop', 'safe-stop'):
            self._stopped.add(box)
        elif cmd in ('start', 'safe-stop', 'restart'): # for 'restart' - just in case it was off unexpectedly
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

    def _server_request(self, host, func, data=None, headers=None, timeout=None):
        req = self._prepare_request(host, func, data, headers)
        url = req.get_full_url()
        print "DEBUG: requesting: %s" % url
        try:
            response = urllib2.urlopen(req, **({} if timeout is None else {'timeout': timeout}))
        except urllib2.URLError , e:
            self.fail("%s request failed with %s" % (url, e))
        except Exception, e:
            self.fail("%s request failed with exception:\n%s\n\n" % (url, traceback.format_exc()))
        self.assertEqual(response.getcode(), 200, "%s request returns error code %d" % (url, response.getcode()))
        answer = self._json_loads(response.read(), url)
        #TODO make more intelegent check, now some requests return [], not {}
        #if answer is not None and answer.get("error", '') not in ['', '0', 0]:
        #    print "Answer: %s" % (answer,)
        #    self.fail("%s request returned API error %s: %s" % (url, answer["error"], answer.get("errorString","")))
        return answer

    #FIXME combine these two similar methods in one!
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
        #TODO make more intelegent check, now some requests return [], not {}
        #if answer is not None and answer.get("error", '') not in ['', '0', 0] and with_debug:
        #    print "Answer: %s" % (answer,)
        #    print "Host %s, call %s returned API error %s: %s" % (host, func, answer["error"], answer.get("errorString",""))
        return answer

    def _wait_servers_up(self, servers=None):
        endtime = time.time() + SERVER_UP_TIMEOUT
        tocheck = servers or set(range(self.num_serv))
        while tocheck and time.time() < endtime:
            #print "_wait_servers_up: %s, %s" % (endtime - time.time(), str(tocheck))
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
        #print "DEBUG: _change_system_name reply: %s" % res


    def setUp(self):
        "Just prints \n after unittest module prints a test name"
        print
    #    print "*** Setting up: %s" % self._testMethodName  # may be used for debug ;)
    ####################################################

class LegacyTestWrapper(FuncTestCase):
    """
    Provides an object to use virtual box control methods
    """
    _suits = "dummy"
    _test_key = "legacy"

    def __init__(self, config):
        self.globalInit(config)

    def __enter__(self):
        print "Entering TestBoxHandler"
        self._servers_th_ctl('safe-start')
        self._wait_servers_up()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print "Exitting TestBoxHandler"
        try:
            self._servers_th_ctl('safe-stop')
            self.globalFinalise()
        except Exception as err:
            print "Error finalizing tests: $s" % (err,)

    def __del__(self):
        if self._worker:
            self._worker.stopWork()

    @classmethod
    def init_suits(cls):
        "A dummy method since the original one will fail in globalInit()"
        pass
