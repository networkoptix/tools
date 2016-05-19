"""Contains common tools to handle virtual boxes based mediaserver functional testing.
Including FuncTestCase - the base class for all mediaserver functional test classes.
"""
__author__ = 'Danil Lavrentyuk'
import sys, os
import subprocess
import unittest
import urllib, urllib2
import time
import json
import traceback

from functest_util import ClusterLongWorker, unquote_guid, Version, FtConfigParser, checkResultsEqual, ManagerAddPassword, SafeJsonLoads

CONFIG_FNAME = "functest.cfg"

NUM_SERV=2
SERVER_UP_TIMEOUT = 20 # seconds, timeout for server to start to respond requests

__all__ = ['boxssh', 'FuncTestCase', 'FuncTestError', 'RunTests',
           'LegacyTestWrapper', 'UnitTestRollback', 'FuncTestMaster', 'getTestMaster']


_testMaster = None  # type: FuncTestMaster


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
            if hasattr(cls, name):
                raise AssertionError("Test suite naming error: class %s already has attrinute %s" % (cls.__name__, name))
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

    def _server_request(self, host, func, data=None, headers=None, timeout=None, unparsed=False):
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
        data = response.read()
        answer = self._json_loads(data, url)
        #TODO make more intelegent check, now some requests return [], not {}
        #if answer is not None and answer.get("error", '') not in ['', '0', 0]:
        #    print "Answer: %s" % (answer,)
        #    self.fail("%s request returned API error %s: %s" % (url, answer["error"], answer.get("errorString","")))
        return (answer, data) if unparsed else answer

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

# Rollback support
class UnitTestRollback:
    "Legacy: Now it only removes resources, recorded in the eollback file."
    _rollbackFile = None

    def __init__(self):
        if os.path.isfile(".rollback"):
            selection = 'r' if _testMaster.auto_rollback else ''
            if not _testMaster.auto_rollback:
                try :
                    print "+++++++++++++++++++++++++++++++++++++++++++WARNING!!!++++++++++++++++++++++++++++++++"
                    print "The .rollback file has been detected, if continues to run test the previous rollback information will be lost!\n"
                    print "Do you want to run Recover NOW?\n"
                    selection = raw_input("Press r to RUN RECOVER at first or press Enter to SKIP RECOVER and run the test")
                except Exception:
                    pass

            if len(selection) != 0 and selection[0] in ('r', 'R'):
                self.doRecover()

        self._rollbackFile = open(".rollback","w+")

    def addOperations(self,methodName,serverAddress,resourceId):
        #for s in _testMaster.clusterTestServerList:
        self._rollbackFile.write(("%s,%s,%s\n") % (methodName,serverAddress,resourceId))
        self._rollbackFile.flush()

    def _doSingleRollback(self,methodName,serverAddress,resourceId):
        # this function will do a single rollback
        req = urllib2.Request("http://%s/ec2/removeResource" % (serverAddress,),
            data='{ "id":"%s" }' % (resourceId), headers={'Content-Type': 'application/json'})
        #response = None
        try:
            response = urllib2.urlopen(req)
        except:
            return False
        if response.getcode() != 200:
            response.close()
            return False
        response.close()
        return True

    def doRollback(self):
        recoverList = []
        # set the cursor for the file to the file beg
        self._rollbackFile.seek(0,0)
        for line in self._rollbackFile:
            if line == '\n':
                continue
            l = line.rstrip('\n').split(',')
            # now we have method,serverAddress,resourceId
            if not self._doSingleRollback(l[0],l[1],l[2]):
                # failed for this rollback
                print "Failed rollback transaction: Method:%s; Server:%s; ResourceId:%s (you could recover it later)" % (l[0],l[1],l[2])
                recoverList.append(line)
            else:
                print '+',
        print

        self._rollbackFile.close()
        os.remove(".rollback")

        if recoverList:
            recoverFile = open(".rollback","w+")
            for line in recoverList:
                recoverFile.write(line)
            recoverFile.close()

    def doRecover(self):
        if not os.path.isfile(".rollback") :
            print "Nothing needs to be recovered"
            return
        print "Start to recover from previous failed rollback transaction"
        self._rollbackFile = open(".rollback","r")
        self.doRollback()
        print "Recover done..."

    def removeRollbackDB(self):
        self._rollbackFile.close()
        os.remove(".rollback")


class FuncTestMaster(object):
    """
    The main service class to run legacy functional tests.
    """
    clusterTestServerList = []
    clusterTestSleepTime = None
    clusterTestServerUUIDList = []
    clusterTestServerObjs = dict()
    configFname = CONFIG_FNAME
    config = None
    argv = []
    openerReady = False
    threadNumber = 16
    testCaseSize = 2
    unittestRollback = None
    CHUNK_SIZE=4*1024*1024 # 4 MB
    TRANSACTION_LOG="__transaction.log"
    auto_rollback = False
    skip_timesync = False
    skip_backup = False
    skip_mservarc = False
    skip_streming = False
    skip_dbup = False
    do_main_only = False
    need_dump = False

    _argFlags = {
        '--autorollback': 'auto_rollback',
        '--arb': 'auto_rollback', # an alias for the previous
        '--skiptime': 'skip_timesync',
        '--skipbak': 'skip_backup',
        '--skipmsa': 'skip_mservarc',
        '--skipstrm': 'skip_streming',
        '--skipdbup': 'skip_dbup',
        '--mainonly': 'do_main_only',
        '--dump': 'need_dump',
    }

    _getterAPIList = ["getResourceParams",
        "getMediaServersEx",
        "getCamerasEx",
        "getUsers"]

    _ec2GetRequests = ["getResourceTypes",
        "getResourceParams",
        "getMediaServers",
        "getMediaServersEx",
        "getCameras",
        "getCamerasEx",
        "getCameraHistoryItems",
        "getCameraBookmarkTags",
        "getBusinessRules",
        "getUsers",
        "getVideowalls",
        "getLayouts",
        "listDirectory",
        "getStoredFile",
        "getSettings",
        "getCurrentTime",
        "getFullInfo",
        "getLicenses"]

    def getConfig(self):
        if self.config is None:
            self.config = FtConfigParser()
            self.config.read(self.configFname)
        return self.config

    def _loadConfig(self):
        parser = self.getConfig()
        self.clusterTestServerList = parser.get("General","serverList").split(",")
        parser.rtset('ServerList', self.clusterTestServerList)
        self.clusterTestSleepTime = parser.getint("General","clusterTestSleepTime")
        parser.rtset('SleepTime', self.clusterTestSleepTime)
        self.threadNumber = parser.getint("General","threadNumber")
        self.testCaseSize = parser.getint_safe("General","testCaseSize", 2)
        parser.rtset('need_dump', self.need_dump)

    def setUpPassword(self):
        config = self.getConfig()
        pwd = config.get("General","password")
        un = config.get("General","username")
        # configure different domain password strategy
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        for s in self.clusterTestServerList:
            ManagerAddPassword(passman, s, un, pwd)

        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPDigestAuthHandler(passman)))
        self.openerReady = True
#        urllib2.install_opener(urllib2.build_opener(AuthH(passman)))

    def check_flags(self, argv):
        "Checks flag options and remove them from argv"
        #FIXME not used now. remove it?
        g = globals()
        found = False
        for arg in argv:
            if arg in self._argFlags:
                g[self._argFlags[arg]] = True
                found = True
        if found:
            argv[:] = [arg for arg in argv if arg not in self._argFlags]

    def preparseArgs(self, argv):
        other = [argv[0]]
        config_next = False
        for arg in argv[1:]:
            if config_next:
                self.configFname = arg
                config_next = False
                print "Use config", self.configFname
            elif arg in self._argFlags:
                setattr(self, self._argFlags[arg], True)
            elif arg == '--config':
                config_next = True
            elif arg.startswith('--config='):
                self.configFname = arg[len('--config='):]
                print "Use config", self.configFname
            else:
                other.append(arg)
        self.argv = other
        return other

    def _callAllGetters(self):
        print "======================================"
        print "Test all ec2 get request status"
        for s in self.clusterTestServerList:
            for reqName in self._ec2GetRequests:
                print "Connection to http://%s/ec2/%s" % (s,reqName)
                response = urllib2.urlopen("http://%s/ec2/%s" % (s,reqName))
                if response.getcode() != 200:
                    return (False,"%s failed with statusCode %d" % (reqName,response.getcode()))
                response.close()
        print "All ec2 get requests work well"
        print "======================================"
        return (True,"Server:%s test for all getter pass" % (s))

    def _getServerName(self, obj, uuid):
        for s in obj:
            if s["id"] == uuid:
                return s["name"]
        return None

    def _patchUUID(self,uuid):
        if uuid[0] == '{' :
            return uuid
        else:
            return "{%s}" % (uuid)

    # call this function after reading the clusterTestServerList!
    def _fetchClusterTestServerNames(self):
        # We still need to get the server name since this is useful for
        # the SaveServerAttributeList test (required in its post data)

        response = urllib2.urlopen("http://%s/ec2/getMediaServersEx?format=json" % (self.clusterTestServerList[0]))

        if response.getcode() != 200:
            return (False,"getMediaServersEx returned error code: %d" % (response.getcode()))

        json_obj = SafeJsonLoads(response.read(), self.clusterTestServerList[0], 'getMediaServersEx')
        if json_obj is None:
            return (False, "Wrong response")

        for u in self.clusterTestServerUUIDList:
            n = self._getServerName(json_obj,u[0])
            if n == None:
                return (False,"Cannot fetch server name with UUID:%s" % (u[0]))
            else:
                u[1] = n

        response.close()
        return (True,"")

    def _dumpDiffStr(self,str,i):
        if len(str) == 0:
            print "<empty string>"
        else:
            start = max(0,i - 64)
            end = min(64,len(str) - i) + i
            comp1 = str[start:i]
            # FIX: the i can be index that is the length which result in index out of range
            comp2 = "<EOF>" if i >= len(str) else str[i]
            comp3 = "<EOF>" if i + 1 >= len(str) else str[i + 1:end]
            print "%s^^^%s^^^%s\n" % (comp1,comp2,comp3)


    def _seeDiff(self,lhs,rhs,offset=0):
        if len(rhs) == 0 or len(lhs) == 0:
            print "The difference is showing bellow:\n"
            print "<empty string>" if len(lhs) == 0 else rhs[0:min(128,len(rhs))]
            print "<empty string>" if len(rhs) == 0 else rhs[0:min(128,len(rhs))]
            print "One of the string is empty!"
            return

        for i in xrange(max(len(rhs),len(lhs))):
            if i >= len(rhs) or i >= len(lhs) or lhs[i] != rhs[i]:
                print "The difference is showing bellow:"
                self._dumpDiffStr(lhs,i)
                self._dumpDiffStr(rhs,i)
                print "The first different character is at location:%d" % (i + 1+offset)
                return

    def _testConnection(self):
        print "=================================================="
        print "Test connection with each server in the server list "
        timeout = 5
        failed = False
        for s in self.clusterTestServerList:
            print "Try to connect to server: %s" % (s),
            request = urllib2.Request("http://%s/ec2/testConnection" % (s))
            try:
                response = urllib2.urlopen(request, timeout=timeout)
            except urllib2.URLError , e:
                print "\nFAIL: error connecting to %s with a %s seconds timeout:" % (s,timeout),
                if isinstance(e, urllib2.HTTPError):
                    print "HTTP error: (%s) %s" % (e.code, e.reason)
                else:
                    print str(e.reason)
                failed = True
                continue

            if response.getcode() != 200:
                print "\nFAIL: Server %s responds with code %s" % (s, response.getcode())
                continue
            json_obj = SafeJsonLoads(response.read(), s, 'testConnection')
            if json_obj is None:
                print "\nFAIL: Wrong response data from server %s" % (s,)
                continue
            self.clusterTestServerObjs[s] = json_obj
            self.clusterTestServerUUIDList.append([self._patchUUID(json_obj["ecsGuid"]), ''])
            response.close()
            print "- OK"

        self.config.rtset('ServerObjs', self.clusterTestServerObjs)
        self.config.rtset('ServerUUIDList', self.clusterTestServerUUIDList)
        print "Connection Test %s" % ("FAILED" if failed else "passed.")
        print "=================================================="
        return not failed

    # This checkResultEqual function will categorize the return value from each
    # server
    # and report the difference status of this

    def _reportDetailDiff(self,key_list):
        for i in xrange(len(key_list)):
            for k in xrange(i + 1,len(key_list)):
                print "-----------------------------------------"
                print "Group %d compared with Group %d\n" % (i + 1,k + 1)
                self._seeDiff(key_list[i],key_list[k])
                print "-----------------------------------------"

    def _reportDiff(self,statusDict,methodName):
        print "\n\n**************************************************"
        print "Report each server status of method: %s\n" % (methodName)
        print "Groupping servers by the same status\n"
        print "The total group number: %d\n" % (len(statusDict))
        if len(statusDict) == 1:
            print "The status check passed!\n"
        i = 1
        key_list = []
        for key in statusDict:
            list = statusDict[key]
            print "Group %d:(%s)\n" % (i,','.join(list))
            i = i + 1
            key_list.append(key)

        self._reportDetailDiff(key_list)
        print "\n**************************************************\n"

    def _checkResultEqual(self,responseList,methodName):
        statusDict = dict()

        for entry in responseList:
            response = entry[0]
            address = entry[1]

            if response.getcode() != 200:
                return(False,"Server:%s method:%s http request failed with code:%d" % (address,methodName,response.getcode()))
            else:
                content = response.read()
                if content in statusDict:
                    statusDict[content].append(address)
                else:
                    statusDict[content] = [address]
                response.close()

        self._reportDiff(statusDict,methodName)

        if len(statusDict) > 1:
            return (False,"")

        return (True,"")

    def _checkSingleMethodStatusConsistent(self,method):
            responseList = []
            for server in self.clusterTestServerList:
                url = "http://%s/ec2/%s" % (server, method)
                print "Connection to " + url
                try:
                    responseList.append((urllib2.urlopen(url),server))
                except urllib2.URLError as err:
                    return False, "Failed to request %s: %s" % (url, err)
            # checking the last response validation
            return checkResultsEqual(responseList,method)

    # Checking transaction log
    # This checking will create file to store the transaction log since this
    # log could be very large which cause urllib2 silently drop data and get
    # partial read. In order to compare such large data file, we only compare
    # one chunk at a time .The target transaction log will be stored inside
    # of a temporary file and all the later comparison will be based on small
    # chunk.

    def _checkTransactionLog(self):

        first_hit = False
        serverAddr= None
        for s in self.clusterTestServerList:
            print "Connection to http://%s/ec2/%s" %(s,"getTransactionLog")
            # check if we have that transactionLog
            if not first_hit:
                first_hit = True
                serverAddr = s
                with open(self.TRANSACTION_LOG,"w+") as f:
                    req = urllib2.urlopen("http://%s/ec2/%s"%(s,"getTransactionLog"))
                    while True:
                        data = req.read( self.CHUNK_SIZE )
                        if data is None or len(data) == 0:
                            break
                        f.write(data)
                # for the very first transactionLog, just skip
                continue
            else:
                assert os.path.isfile(self.TRANSACTION_LOG), \
                    "The internal temporary file is not found, it means a external program has deleted it"
                with open(self.TRANSACTION_LOG,"r") as f:
                    req = urllib2.urlopen("http://%s/ec2/%s"%(s,"getTransactionLog"))
                    pos = 0
                    if req.getcode() != 200:
                        print "Connection to http://%s/ec2/%s" %(s,"getTransactionLog")
                        return (False,"")

                    while True:
                        data = f.read(self.CHUNK_SIZE)
                        pack = req.read(self.CHUNK_SIZE)

                        if data is None or len(data) == 0:
                            if pack is None or len(pack) == 0:
                                break
                            else:
                                print "Server:%s has different status with server:%s on method:%s" % (s,serverAddr,"getTransactionLog")
                                print "Server:%s has data but server:%s runs out of its transaction log"%(
                                    s,serverAddr)
                                return (False,"")
                        else:
                            if pack is None or len(pack) == 0:
                                print "Server:%s has different status with server:%s on method:%s" % (s,serverAddr,"getTransactionLog")
                                print "Server:%s has data but server:%s runs out of its transaction log"%(
                                    serverAddr,s)
                                return (False,"")
                            else:
                                if data != pack:
                                    print "Server:%s has different status with server:%s on method:%s" % (s,serverAddr,"getTransactionLog")
                                    self._seeDiff(data,pack,pos)
                                    return (False,"")
                                pos += len(pack)
                    req.close()
        os.remove(self.TRANSACTION_LOG)
        return (True,"")

    def checkMethodStatusConsistent(self,method):
            ret,reason = self._checkSingleMethodStatusConsistent(method)
            if ret:
                return self._checkTransactionLog()
            else:
                return (ret,reason)

    def _ensureServerListStates(self,sleep_timeout):
        time.sleep(sleep_timeout)
        for method in self._getterAPIList:
            ret,reason = self._checkSingleMethodStatusConsistent(method)
            if not ret:
                return (ret,reason)
        return self._checkTransactionLog()

    def init(self, notest=False):
        self._loadConfig()
        self.setUpPassword()
        return (True,"") if notest or self._testConnection() else (False,"Connection test failed")

    def init_rollback(self):
        self.unittestRollback = UnitTestRollback()

    def initial_tests(self):
        # ensure all the server are on the same page
        ret,reason = self._ensureServerListStates(self.clusterTestSleepTime)
        if not ret: return (ret,reason)

        ret,reason = self._fetchClusterTestServerNames()
        if not ret: return (ret,reason)

        ret,reason = self._callAllGetters()
        if not ret:return (ret,reason)

        # do the rollback here
        self.init_rollback()
        return (True,"")


def getTestMaster():  # type: FuncTestMaster
    global _testMaster
    if _testMaster is None:
        _testMaster = FuncTestMaster()
    return _testMaster
