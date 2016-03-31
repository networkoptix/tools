__author__ = 'Danil Lavrentyuk'
"This module contains some utility functions and classes for the functional tests script."
import sys
import json
from urllib import urlencode
import urllib2
from ConfigParser import RawConfigParser
import traceback

__all__ = ['JsonDiff', 'FtConfigParser', 'compareJson', 'showHelp', 'ManagerAddPassword', 'SafeJsonLoads',
           'checkResultsEqual',
           'ClusterWorker', 'ClusterLongWorker', 'parse_size', 'args2str', 'real_caps',
           'CAMERA_ATTR_EMPTY', 'FULL_SCHEDULE_TASKS']


# Empty camera's attributes structure
CAMERA_ATTR_EMPTY = {
    'cameraID': '',
    'scheduleEnabled': '',
    'backupType': '',  # CameraBackup_HighQuality, CameraBackup_LowQuality or CameraBackupBoth
    'cameraName': '',
    'userDefinedGroupName': '',
    'licenseUsed': '',
    'motionType': '',
    'motionMask': '',
    'scheduleTasks': '',
    'audioEnabled': '',
    'secondaryStreamQuality': '',
    'controlEnabled': '',
    'dewarpingParams': '',
    'minArchiveDays': '',
    'maxArchiveDays': '',
    'preferedServerId': '',
    'failoverPriority': ''
}

# Schedule to activate camera recording
FULL_SCHEDULE_TASKS = [
    {
        "afterThreshold": 5,
        "beforeThreshold": 5,
        "dayOfWeek": 1,
        "endTime": 86400,
        "fps": 15,
        "recordAudio": False,
        "recordingType": "RT_Always",
        "startTime": 0,
        "streamQuality": "highest"
    },
    {
        "afterThreshold": 5,
        "beforeThreshold": 5,
        "dayOfWeek": 2,
        "endTime": 86400,
        "fps": 15,
        "recordAudio": False,
        "recordingType": "RT_Always",
        "startTime": 0,
        "streamQuality": "highest"
    },
    {
        "afterThreshold": 5,
        "beforeThreshold": 5,
        "dayOfWeek": 3,
        "endTime": 86400,
        "fps": 15,
        "recordAudio": False,
        "recordingType": "RT_Always",
        "startTime": 0,
        "streamQuality": "highest"
    },
    {
        "afterThreshold": 5,
        "beforeThreshold": 5,
        "dayOfWeek": 4,
        "endTime": 86400,
        "fps": 15,
        "recordAudio": False,
        "recordingType": "RT_Always",
        "startTime": 0,
        "streamQuality": "highest"
    },
    {
        "afterThreshold": 5,
        "beforeThreshold": 5,
        "dayOfWeek": 5,
        "endTime": 86400,
        "fps": 15,
        "recordAudio": False,
        "recordingType": "RT_Always",
        "startTime": 0,
        "streamQuality": "highest"
    },
    {
        "afterThreshold": 5,
        "beforeThreshold": 5,
        "dayOfWeek": 6,
        "endTime": 86400,
        "fps": 15,
        "recordAudio": False,
        "recordingType": "RT_Always",
        "startTime": 0,
        "streamQuality": "highest"
    },
    {
        "afterThreshold": 5,
        "beforeThreshold": 5,
        "dayOfWeek": 7,
        "endTime": 86400,
        "fps": 15,
        "recordAudio": False,
        "recordingType": "RT_Always",
        "startTime": 0,
        "streamQuality": "highest"
    }
]

# ---------------------------------------------------------------------
# A deep comparison of json object
# This comparision is slow , but it can output valid result when 2 json
# objects has different order in their array
# ---------------------------------------------------------------------
class JsonDiff:
    _hasDiff = False
    _errorInfo=""
    _anchorStr=None
    _currentRecursionSize=0
    _anchorStack = []

    def keyNotExisted(self,lhs,rhs,key):
        """ format the error information based on key lost """
        self._errorInfo = ("CurrentPosition:{anchor}\n"
                     "The key:{k} is not existed in both two objects\n").format(anchor=self._anchorStr,k=key)
        self._hasDiff = True
        return self

    def keysDiffer(self, lhs, rhs):
        " format the error information on key sets difference"
        self._errorInfo = ("CurrentPosition:{anchor}\n"
            "Different keys found. {lk} in one object and {rk} in the other\n"
        ).format(anchor=self._anchorStr,
                 lk=str(list(lhs.viewkeys()-rhs.viewkeys())),
                 rk=str(list(rhs.viewkeys()-lhs.viewkeys()))
                 )
        self._hasDiff = True
        return self

    def arrayIndexNotFound(self,lhs,idx):
        """ format the error information based on the array index lost"""
        self._errorInfo= ("CurrentPosition:{anchor}\n"
                    "The element in array at index:{i} cannot be found in other objects\n"
                    "Element: {e}"
            ).format(anchor=self._anchorStr, i=idx, e=lhs[idx])
        self._hasDiff = True
        return self

    def leafValueNotSame(self,lhs,rhs):
        lhs_str = None
        rhs_str = None
        try :
            lhs_str = str(lhs)
        except Exception:
            lhs_str = repr(lhs)
        try:
            rhs_str = str(rhs)
        except:
            rhs_str = repr(rhs)

        self._errorInfo= ("CurrentPosition:{anchor}\n"
            "The left hand side value:{lval} and right hand side value:{rval} is not same"
            ).format(anchor=self._anchorStr, lval=lhs_str, rval=rhs_str)
        self._hasDiff = True
        return self

    def typeNotSame(self,lhs,rhs):
        self._errorInfo=("CurrentPosition:{anchor}\n"
            "The left hand value type:{lt} is not same with right hand value type:{rt}\n"
            ).format(anchor=self._anchorStr, lt=type(lhs), rt=type(rhs))
        self._hasDiff = True
        return self

    def enter(self,position):
        if self._anchorStr is None:
            self._anchorStack.append(0)
        else:
            self._anchorStack.append(len(self._anchorStr))

        if self._anchorStr is None:
            self._anchorStr=position
        else:
            self._anchorStr+=".%s"%(position)

        self._currentRecursionSize += 1

    def leave(self):
        assert len(self._anchorStack) != 0 , "No place to leave"
        val = self._anchorStack[len(self._anchorStack)-1]
        self._anchorStack.pop(len(self._anchorStack)-1)
        self._anchorStr = self._anchorStr[:val]
        self._currentRecursionSize -= 1

    def hasDiff(self):
        return self._hasDiff

    def errorInfo(self):
        if self._hasDiff:
            return self._errorInfo
        else:
            return "<no diff>"


    def resetDiff(self):
        self._hasDiff = False
        self._errorInfo=""


class FtConfigParser(RawConfigParser):

    def __init__(self, *args, **kw_args):
        RawConfigParser.__init__(self, *args, **kw_args)
        self.runtime = dict()

    def get_safe(self, section, option, default=None):
        if not self.has_option(section, option):
            return default
        return self.get(section, option)

    def getint_safe(self, section, option, default=None):
        if not self.has_option(section, option):
            return default
        return self.getint(section, option)

    def getfloat_safe(self, section, option, default=None):
        if not self.has_option(section, option):
            return default
        return self.getfloat(section, option)

    def rtset(self, name, value):
        self.runtime[name] = value

    def rtget(self, name):
        return self.runtime[name]

    def rthas(self, name):
        return name in self.runtime


def _compareJsonObject(lhs,rhs,result):
    assert isinstance(lhs,dict),"The lhs object _MUST_ be an object"
    assert isinstance(rhs,dict),"The rhs object _MUST_ be an object"
    # compare the loop and stuff
    if lhs.viewkeys() ^ rhs.viewkeys():
        return result.keysDiffer(lhs, rhs)
    for lhs_key in lhs.iterkeys():
        if lhs_key not in rhs:
            return result.keyNotExisted(lhs,rhs,lhs_key);
        else:
            lhs_obj = lhs[lhs_key]
            rhs_obj = rhs[lhs_key]
            result.enter(lhs_key)
            if _compareJson(lhs_obj,rhs_obj,result).hasDiff():
                result.leave()
                return result
            result.leave()

    return result


def _compareJsonList(lhs,rhs,result):
    assert isinstance(lhs,list),"The lhs object _MUST_ be a list"
    assert isinstance(rhs,list),"The rhs object _MUST_ be a list"

    # The comparison of list should be ignore the element's order. A
    # naive O(n*n) comparison is used here. For each element P in lhs,
    # it will try to match one element in rhs , if not failed, otherwise
    # passed.

    tabooSet = set()

    for lhs_idx,lhs_ele in enumerate(lhs):
        notFound = True
        for idx,val in enumerate(rhs):
            if idx in tabooSet:
                continue
            # now checking if this value has same value with the lhs_ele
            if not _compareJson(lhs_ele,val,result).hasDiff():
                tabooSet.add(idx)
                notFound = False
                break
            else:
                result.resetDiff()

        if notFound:
            return result.arrayIndexNotFound(lhs,lhs_idx)

    return result


def _compareJsonLeaf(lhs,rhs,result):
    lhs_type = type(lhs)
    if isinstance(rhs,type(lhs)):
        if rhs != lhs:
            return result.leafValueNotSame(lhs,rhs)
        else:
            return result
    else:
        return result.typeNotSame(lhs,rhs)


def _compareJson(lhs,rhs,result):
    lhs_type = type(lhs)
    rhs_type = type(rhs)
    if lhs_type != rhs_type:
        return result.typeNotSame(lhs,rhs)
    else:
        if lhs_type is dict:
            # Enter the json object here
            return _compareJsonObject(lhs,rhs,result)
        elif rhs_type is list:
            return _compareJsonList(lhs,rhs,result)
        else:
            return _compareJsonLeaf(lhs,rhs,result)


def compareJson(lhs,rhs):
    result = JsonDiff()
    # An outer most JSON element must be an array or dict
    if isinstance(lhs,list):
        if isinstance(rhs,list):
            result.enter("<root>")
            if _compareJson(lhs,rhs,result).hasDiff():
                return result
            result.leave()

        else:
            return result.typeNotSame(lhs,rhs)
    else:
        if isinstance(rhs,dict):
            result.enter("<root>")
            if _compareJson(lhs,rhs,result).hasDiff():
                return result
            result.leave()
        else:
            return result.typeNotSame(lhs,rhs)
    #FIXME check if lhs neither list nor dit!

    return result


def checkResultsEqual(responseList, methodName):
    """responseList - is a list of pairs (response, address).
    The function compares that all responces are ok and their json contents are equal.
    Returns a tupple of a boolean success indicator and a string fail reason.
    """
    print "------------------------------------------"
    print "Test sync status on method: %s" % (methodName)
    result = None
    resultAddr = None
    resultJsonObject = None

    for entry in responseList:
        response, address = entry[0:2]

        if response.getcode() != 200:
            return (False,"Server: %s method: %s HTTP request failed with code: %d" % (address,methodName,response.getcode()))
        else:
            content = response.read()
            if result == None:
                result = content
                resultAddr = address
                resultJsonObject = SafeJsonLoads(result, resultAddr, methodName)
                if resultJsonObject is None:
                    return (False, "Wrong response from %s" % resultAddr)
            else:
                if content != result:
                    # Since the server could issue json object has different order which makes us
                    # have to do deep comparison of json object internally. This deep comparison
                    # is very slow and only performs on objects that has failed the naive comparison
                    contentJsonObject = SafeJsonLoads(content, address, methodName)
                    if contentJsonObject is None:
                        return (False, "Wrong response from %s" % address)
                    compareResult = compareJson(contentJsonObject, resultJsonObject)
                    if compareResult.hasDiff():
                        print "Server %s has different status with server %s on method %s" % (address,resultAddr,methodName)
                        print compareResult.errorInfo()
                        return (False,"Failed to sync")
        response.close()
    print "Method:%s is synced in cluster" % (methodName)
    print "------------------------------------------"
    return (True,"")



# ---------------------------------------------------------------------
# Print help (general page or function specific, depending in sys.argv
# ---------------------------------------------------------------------
_helpMenu = {
    "perf":("Run performance test",(
        "Usage: python main.py --perf --type=... \n\n"
        "This command line will start built-in performance test\n"
        "The --type option is used to specify what kind of resource you want to profile.\n"
        "Currently you could specify Camera and User, eg : --type=Camera,User will test on Camera and User both;\n"
        "--type=User will only do performance test on User resources")),
    "clear":("Clear resources",(
        "Usage: python main.py --clear \nUsage: python main.py --clear --fake\n\n"
        "This command is used to clear the resource in server list.\n"
        "The resource includes Camera,MediaServer and Users.\n"
        "The --fake option is a flag to tell the command _ONLY_ clear\n"
        "resource that has name prefixed with \"ec2_test\".\n"
        "This name pattern typically means that the data is generated by the automatic test\n")),
    "sync":("Test cluster is sycnchronized or not",(
        "Usage: python main.py --sync \n\n"
        "This command is used to test whether the cluster has synchronized states or not.")),
    "recover":("Recover from previous fail rollback",(
        "Usage: python main.py --recover \n\n"
        "This command is used to try to recover from previous failed rollback.\n"
        "Each rollback will based on a file .rollback. However rollback may failed.\n"
        "The failed rollback transaction will be recorded in side of .rollback file as well.\n"
        "Every time you restart this program, you could specify this command to try\n "
        "to recover the failed rollback transaction.\n"
        "If you are running automatic test, the recover will be detected automatically and \n"
        "prompt for you to choose whether recover or not")),
    "merge-test":("Run merge test",(
        "Usage: python main.py --merge-test \n\n"
        "This command is used to run merge test speicifically.\n"
        "This command will run admin user password merge test and resource merge test.\n")),
    "merge-admin":("Run merge admin user password test",(
        "Usage: python main.py --merge-admin \n\n"
        "This command is used to run run admin user password merge test directly.\n"
        "This command will be removed later on")),
    "rtsp-test":("Run rtsp test",(
        "Usage: python main.py --rtsp-test \n\n"
        "This command is used to run RTSP Test test.It means it will issue RTSP play command,\n"
        "and wait for the reply to check the status code.\n"
        "User needs to set up section in functest.cfg file: [Rtsp]\ntestSize=40\n"
        "The testSize is configuration parameter that tell rtsp the number that it needs to perform \n"
        "RTSP test on _EACH_ server. Therefore, the above example means 40 random RTSP test on each server.\n")),
    "add":("Resource creation",(
        "Usage: python main.py --add=... --count=... \n\n"
        "This command is used to add different generated resources to servers.\n"
        "3 types of resource is available: MediaServer,Camera,User. \n"
        "The --add parameter needs to be specified the resource type. Eg: --add=Camera \n"
        "means add camera into the server, --add=User means add user to the server.\n"
        "The --count option is used to tell the size that you wish to generate that resources.\n"
        "Eg: main.py --add=Camera --count=100           Add 100 cameras to each server in server list.\n")),
    "remove":("Resource remove",(
        "Usage: python main.py --remove=Camera --id=... \n"
        "Usage: python main.py --remove=Camera --fake \n\n"
        "This command is used to remove resource on each servers.\n"
        "The --remove needs to be specified required resource type.\n"
        "3 types of resource is available: MediaServer,Camera,User. \n"
        "The --id option is optinoal, if it appears, you need to specify a valid id like this:--id=SomeID.\n"
        "It is used to delete specific resource. \n"
        "Optionally, you could specify --fake flag , if this flag is on, then the remove will only \n"
        "remove resource that has name prefixed with \"ec2_test\" which typically means fake resource")),
    "auto-test":("Automatic test",(
        "Usage: python main.py \n\n"
        "This command is used to run built-in automatic test.\n"
        "The automatic test includes 11 types of test and they will be runed automatically."
        "The configuration parameter is as follow: \n"
        "threadNumber                  The thread number that will be used to fire operations\n"
        "mergeTestTimeout              The timeout for merge test\n"
        "clusterTestSleepTime          The timeout for other auto test\n"
        "All the above configuration parameters needs to be defined in the General section.\n"
        "The test will try to rollback afterwards and try to recover at first.\n"
        "Also the sync operation will be performed before any test\n")),
    "rtsp-perf":("Rtsp performance test",(
        "Usage: python main.py --rtsp-perf \n\n"
        "Usage: python main.py --rtsp-perf --dump \n\n"
        "This command is used to run rtsp performance test.\n"
        "The test will try to check RTSP status and then connect to the server \n"
        "and maintain the connection to receive RTP packet for several seconds. The request \n"
        "includes archive and real time streaming.\n"
        "Additionally,an optional option --dump may be specified.If this flag is on, the data will be \n"
        "dumped into a file, the file stores raw RTP data and also the file is named with following:\n"
        "{Part1}_{Part2}, Part1 is the URL ,the character \"/\" \":\" and \"?\" will be escaped to %,$,#\n"
        "Part2 is a random session number which has 12 digits\n"
        "The configuration parameter is listed below:\n\n"
        "threadNumbers    A comma separate list to specify how many list each server is required \n"
        "The component number must be the same as component in serverList. Eg: threadNumbers=10,2,3 \n"
        "This means that the first server in serverList will have 10 threads,second server 2,third 3.\n\n"
        "archiveDiffMax       The time difference upper bound for archive request, in minutes \n"
        "archiveDiffMin       The time difference lower bound for archive request, in minutes \n"
        "timeoutMax           The timeout upper bound for each RTP receiving, in seconds. \n"
        "timeoutMin           The timeout lower bound for each RTP receiving, in seconds. \n"
        "Notes: All the above parameters needs to be specified in configuration file: functest.cfg under \n"
        "section Rtsp.\nEg:\n[Rtsp]\nthreadNumbers=10,2\narchiveDiffMax=..\nardchiveDiffMin=....\n"
        )),
    "sys-name":("System name test",(
        "Usage: python main.py --sys-name \n\n"
        "This command will perform system name test for each server.\n"
        "The system name test is , change each server in cluster to another system name,\n"
        "and check each server that whether all the other server is offline and only this server is online.\n"
        ))
    }

def showHelp(argv):
    if len(argv) == 2:
        helpStrHeader=("Help for auto test tool\n\n"
                 "*****************************************\n"
                 "**************Function Menu**************\n"
                 "*****************************************\n"
                 "Entry            Introduction            \n")

        print helpStrHeader

        maxitemlen = max(len(s) for s in _helpMenu.iterkeys())+1
        for k,v in _helpMenu.iteritems():
            print "%s   %s" % ( (k+':').ljust(maxitemlen), v[0])

        helpStrFooter = ("\n\nTo see detail help information, please run command:\n"
               "python main.py --help Entry\n\n"
               "Eg: python main.py --help auto-test\n"
               "This will list detail information about auto-test\n")

        print helpStrFooter
    else:
        option = argv[2]
        if option in _helpMenu:
            print "==================================="
            print option
            print "===================================\n\n"
            print _helpMenu[option][1]
        else:
            print "Option: %s is not found !"%(option)


# A helper function to unify pasword managers' configuration
def ManagerAddPassword(passman, host, user, pwd):
    passman.add_password(None, "http://%s/ec2" % (host), user, pwd)
    passman.add_password(None, "http://%s/api" % (host), user, pwd)
    passman.add_password(None, "http://%s/hls" % (host), user, pwd)
    passman.add_password(None, "http://%s/proxy" % (host), user, pwd)


def SafeJsonLoads(text, serverAddr, methodName):
    try:
        return json.loads(text)
    except ValueError, e:
        print "Error parsing server %s, method %s response: %s" % (serverAddr, methodName, e)
        return None


def HttpRequest(serverAddr, methodName, params=None, headers=None, timeout=None, printHttpError=False, logURL=False):
    url = "http://%s/%s" % (serverAddr, methodName)
    err = ""
    if params:
        url += '?'+ urlencode(params)
    if logURL:
        print "Requesting: " + url
    req = urllib2.Request(url)
    if headers:
        for k, v in headers.iteritems():
            req.add_header(k, v)
    try:
        response = urllib2.urlopen(req) if timeout is None else urllib2.urlopen(req, timeout=timeout)
    except Exception as e:
        err = "ends with exception %s" % e
    else:
        if response.getcode() != 200:
            err = "returns %s HTTP code" % (response.getcode(),)
    if err:
        if printHttpError:
            if params:
                err = "Error: url %s %s" % (url, err)
            else:
                err = "Error: server %s, method %s %s" % (serverAddr, methodName, err)
            if isinstance(printHttpError, Exception):
                raise printHttpError(err)
            print err
        return None
    data = response.read()
    if len(data):
        return SafeJsonLoads(data, serverAddr, methodName)
    return True


#def safe_request_json(req):
#    try:
#        return json.loads(urllib2.urlopen(req).read())
#    except Exception as e:
#        if isinstance(req, urllib2.Request):
#            req = req.get_full_uri()
#        print "FAIL: error requesting '%s': %s" % (req, e)
#        return None

import Queue
import threading

# Thread queue for multi-task.  This is useful since if the user
# want too many data to be sent to the server, then there maybe
# thousands of threads to be created, which is not something we
# want it.  This is not a real-time queue, but a push-sync-join
class ClusterWorker(object):
    _queue = None
    _threadList = None
    _threadNum = 1

    def __init__(self, num, element_size=0):
        self._threadNum = num
        if element_size == 0:
            element_size = num
        elif element_size < num:
            self._threadNum = element_size
        self._queue = Queue.Queue(element_size)
        self._threadList = []
        self._working = False
        self._oks = []

    def _do_work(self):
        return not self._queue.empty()

    def _worker(self, num):
        while self._do_work():
            func, args = self._queue.get(True)
            try:
                func(*args)
            except Exception:
                print "ERROR: ClusterWorker call to %s got an Exception: %s" % (func.__name__, traceback.format_exc())
                self._oks.append(False)
            else:
                self._oks.append(True)
            finally:
                self._queue.task_done()

    def startThreads(self):
        for _ in xrange(self._threadNum):
            t = threading.Thread(target=self._worker, args=(_,))
            t.start()
            self._threadList.append(t)

    def joinThreads(self):
        for t in self._threadList:
            t.join()

    def joinQueue(self):
        self._queue.join()

    def workDone(self):
        return self._queue.empty()

    def join(self):
        # We delay the real operation until we call join
        self.startThreads()
        # Second we call queue join to join the queue
        self._queue.join()
        # Now we safely join the thread since the queue
        # will utimatly be empty after execution
        self.joinThreads()

    def enqueue(self, task, args):
        self._queue.put((task, args), True)

    def allOk(self):
        return all(self._oks)

    def clearOks(self):
        self._oks = []



class ClusterLongWorker(ClusterWorker):

    def __init__(self, num, element_size=0):
        print "ClusterLongWorker starting"
        super(ClusterLongWorker, self).__init__(num, element_size)
        self._working = False

    def _do_work(self):
        return self._working

    def startThreads(self):
        self._working = True
        super(ClusterLongWorker, self).startThreads()

    def stopWork(self):
        self.enqueue(self._terminate, ())
        self.joinThreads()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Queue.Empty:
                break

    def _terminate(self):
        self._working = False
        self.enqueue(self._terminate, ()) # for other threads


def quote_guid(guid):
    return guid if guid[0] == '{' else "{" + guid + "}"

def unquote_guid(guid):
    return guid[1:-1] if guid[0] == '{' and guid[-1] == '}' else guid


def get_server_guid(host):
    info = HttpRequest(host, "api/moduleInformation", printHttpError=True)
    if info and (u'id' in info['reply']):
        return unquote_guid(info['reply'][u'id'])
    return None


class Version(object):
    value = []

    def __init__(self, verstr=''):
        self.value = verstr.split('.')

    def __str__(self):
        return '.'.join(self.value)

    def __cmp__(self, other):
        return cmp(self.value, other.value)


def parse_size(size_str):
    "Parse string like 100M, 20k to a number of bytes, i.e. 100M = 100*1024*1024 bytes"
    if size_str[-1].upper() == 'K':
        mult = 1024
        size_str = size_str[:-1].rstrip()
    elif size_str[-1].upper() == 'M':
        mult = 1024*1024
        size_str = size_str[:-1].rstrip()
    else:
        mult = 1
    return int(size_str) * mult


def args2str(args):
    return '%s and %s' % (', '.join('--'+opt for opt in args[:-1]), '--'+args[-1])

def real_caps(str):
    "String's method capitalize makes lower all chars except the first. If it isn't desired - use real_caps."
    return (str[0].upper() + str[1:]) if len(str) else str
