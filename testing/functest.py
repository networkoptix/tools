#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, time
import unittest
import urllib2
import urllib
import threading
import json
import random
import os.path
import signal
import traceback

from functest_util import *
from generator import *
from rtsptests import RtspPerf, RtspTestSuit
from sysname_test import SystemNameTest
from timetest import TimeSyncTest
from stortest import BackupStorageTest, MultiserverArchiveTest
from streaming_test import StreamingTest
from natcon_test import NatConnectionTest
from testboxes import RunTests as RunBoxTests

CONFIG_FNAME = "functest.cfg"


# Rollback support
class UnitTestRollback:
    _rollbackFile = None
    _removeTemplate = '{ "id":"%s" }'

    def __init__(self):
        if os.path.isfile(".rollback"):
            selection = 'r' if clusterTest.auto_rollback else ''
            if not clusterTest.auto_rollback:
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
        for s in clusterTest.clusterTestServerList:
            self._rollbackFile.write(("%s,%s,%s\n") % (methodName,s,resourceId)) #FIXME Is it OK - ignore serverAddress and record operation for ALL SERVERS?!
        self._rollbackFile.flush()

    def _doSingleRollback(self,methodName,serverAddress,resourceId):
        # this function will do a single rollback
        req = urllib2.Request("http://%s/ec2/%s" % (serverAddress,"removeResource"),
            data=self._removeTemplate % (resourceId), headers={'Content-Type': 'application/json'})
        response = None
        try:
            response = urllib2.urlopen(req)
        except:
            return False
        if response.getcode() != 200:
            response.close()
            return False
        response.close()
        return True

    def doRollback(self, quiet=False):
        recoverList = []
        failed = False
        # set the cursor for the file to the file beg
        self._rollbackFile.seek(0,0)
        for line in self._rollbackFile:
            if line == '\n':
                continue
            l = line.rstrip('\n').split(',')
            # now we have method,serverAddress,resourceId
            if self._doSingleRollback(l[0],l[1],l[2]) == False:
                failed = True
                # failed for this rollback
                print ("Cannot rollback for transaction:(MethodName:%s;ServerAddress:%s;ResourceId:%s\n)") % (l[0],l[1],l[2])
                print  "Or you could run recover later when all the rollback done\n"
                recoverList.append("%s,%s,%s\n" % (l[0],l[1],l[2]))
            else:
                if quiet:
                    print '+',
                else:
                    print "..rollback done.."
        if quiet:
            print

        self._rollbackFile.close()
        os.remove(".rollback")

        if failed:
            recoverFile = open(".rollback","w+")
            for line in recoverList:
                recoverFile.write(line)
            recoverFile.close()

    def doRecover(self):
        if not os.path.isfile(".rollback") :
            print "Nothing needs to be recovered"
            return
        else:
            print "Start to recover from previous failed rollback transaction"
        # Do the rollback here
        self._rollbackFile = open(".rollback","r")
        self.doRollback()
        print "Recover done..."

    def removeRollbackDB(self):
        self._rollbackFile.close()
        os.remove(".rollback")


#class AuthH(urllib2.HTTPDigestAuthHandler):
#    def http_error_401(self, req, fp, code, msg, hdrs):
#        print "[DEBUG] Code 401"
#        print "Req: %s" % req
#        return urllib2.HTTPDigestAuthHandler.http_error_401(self, req, fp, code, msg, hdrs)


class ClusterTest(object):
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
    do_main_only = False
    need_dump = False

    _argFlags = {
        '--autorollback': 'auto_rollback',
        '--arb': 'auto_rollback', # an alias for the previous
        '--skiptime': 'skip_timesync',
        '--skipbak': 'skip_backup',
        '--skipmsa': 'skip_mservarc',
        '--skipstrm': 'skip_streming',
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
        self.clusterTestSleepTime = parser.getint("General","clusterTestSleepTime")
        self.threadNumber = parser.getint("General","threadNumber")
        try :
            self.testCaseSize = parser.getint("General","testCaseSize")
        except :
            self.testCaseSize = 2

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
        for s in clusterTest.clusterTestServerList:
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
            if i >= len(str):
                comp2 = "<EOF>"
            else:
                comp2 = str[i]
            comp3 = ""
            if i + 1 >= len(str):
                comp3 = "<EOF>"
            else:
                comp3 = str[i + 1:end]
            print "%s^^^%s^^^%s\n" % (comp1,comp2,comp3)


    def _seeDiff(self,lhs,rhs,offset=0):
        if len(rhs) == 0 or len(lhs) == 0:
            print "The difference is showing bellow:\n"
            if len(lhs) == 0:
                print "<empty string>"
            else:
                print rhs[0:min(128,len(rhs))]
            if len(rhs) == 0:
                print "<empty string>"
            else:
                print rhs[0:min(128,len(rhs))]

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

        print "Connection Test %s" % ("FAILED" if failed else "passed.")
        print "=================================================="
        return True

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
                print "Connection to http://%s/ec2/%s" % (server, method)
                responseList.append((urllib2.urlopen("http://%s/ec2/%s" % (server, method)),server))
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
            if ret == False:
                return (ret,reason)
        return self._checkTransactionLog()

    def init(self, short=False):
        self._loadConfig()
        self.setUpPassword()
        return (True,"") if self._testConnection() else (False,"Connection test failed")

    def init_rollback(self):
        self.unittestRollback = UnitTestRollback()

    def initial_tests(self):
        # ensure all the server are on the same page
        ret,reason = self._ensureServerListStates(self.clusterTestSleepTime)

        if ret == False:
            return (ret,reason)

        ret,reason = self._fetchClusterTestServerNames()

        if ret == False:
            return (ret,reason)

        ret,reason = self._callAllGetters()
        if ret == False:
            return (ret,reason)

        # do the rollback here
        self.init_rollback()
        return (True,"")

clusterTest = ClusterTest()

####################################################################################################
## Some more generators, a bit complex than classes from generator.py
####################################################################################################

class CameraDataGenerator(BasicGenerator):
    _template = """[
        {
            "audioEnabled": %s,
            "controlEnabled": %s,
            "dewarpingParams": "",
            "groupId": "",
            "groupName": "",
            "id": "%s",
            "mac": "%s",
            "manuallyAdded": false,
            "maxArchiveDays": 0,
            "minArchiveDays": 0,
            "model": "%s",
            "motionMask": "",
            "motionType": "MT_Default",
            "name": "%s",
            "parentId": "%s",
            "physicalId": "%s",
            "preferedServerId": "{00000000-0000-0000-0000-000000000000}",
            "scheduleEnabled": false,
            "scheduleTasks": [ ],
            "secondaryStreamQuality": "SSQualityLow",
            "status": "Unauthorized",
            "statusFlags": "CSF_NoFlags",
            "typeId": "{7d2af20d-04f2-149f-ef37-ad585281e3b7}",
            "url": "%s",
            "vendor": "%s"
        }
    ]"""

    def _generateCameraId(self,mac):
        return self.generateUUIdFromMd5(mac)

    def _getServerUUID(self,addr):
        if addr == None:
            return "{2571646a-7313-4324-8308-c3523825e639}"
        i = 0
        for s in  clusterTest.clusterTestServerList:
            if addr == s:
                break
            else:
                i = i + 1

        return clusterTest.clusterTestServerUUIDList[i][0]

    def generateCameraData(self,number,mediaServer):
        ret = []
        for i in xrange(number):
            mac = self.generateMac()
            id = self._generateCameraId(mac)
            name_and_model = self.generateCameraName()
            ret.append((self._template % (self.generateTrueFalse(),
                    self.generateTrueFalse(),
                    id,
                    mac,
                    name_and_model,
                    name_and_model,
                    self._getServerUUID(mediaServer),
                    mac,
                    self.generateIpV4(),
                    self.generateRandomString(4)),id))

        return ret

    def generateUpdateData(self,id,mediaServer):
        mac = self.generateMac()
        name_and_model = self.generateCameraName()
        return (self._template % (self.generateTrueFalse(),
                self.generateTrueFalse(),
                id,
                mac,
                name_and_model,
                name_and_model,
                self._getServerUUID(mediaServer),
                mac,
                self.generateIpV4(),
                self.generateRandomString(4)),id)


# This class serves as an in-memory data base.  Before doing the confliction
# test,
# we begining by creating some sort of resources and then start doing the
# confliction
# test.  These data is maintained in a separate dictionary and once everything
# is done
# it will be rollback.
class ConflictionDataGenerator(BasicGenerator):
    conflictCameraList = []
    conflictUserList = []
    conflictMediaServerList = []
    _lock = threading.Lock()
    _listLock = threading.Lock()

    def _prepareData(self,dataList,methodName,l):
        worker = ClusterWorker(8,len(clusterTest.clusterTestServerList) * len(dataList))

        for d in dataList:
            for s in clusterTest.clusterTestServerList:

                def task(lock,list,list_lock,post_data,server):

                    req = urllib2.Request("http://%s/ec2/%s" % (server,methodName),
                      data=post_data[0], headers={'Content-Type': 'application/json'})

                    response = None

                    with lock:
                        response = urllib2.urlopen(req)

                    if response.getcode() != 200:
                        response.close()
                        print "Failed to connect to http://%s/ec2/%s" % (server,methodName)
                    else:
                        clusterTest.unittestRollback.addOperations(methodName,server,post_data[1])
                        with list_lock:
                            list.append(post_data[0])
                    response.close()

                worker.enqueue(task,(self._lock,l,self._listLock,d,s,))

        worker.join()
        return True

    def _prepareCameraData(self,op,num,methodName,l):
        worker = ClusterWorker(8,len(clusterTest.clusterTestServerList) * num)

        for _ in xrange(num):
            for s in clusterTest.clusterTestServerList:
                d = op(1,s)[0]

                def task(lock,list,list_lock,post_data,server):
                    req = urllib2.Request("http://%s/ec2/%s" % (server,methodName),
                          data=post_data[0], headers={'Content-Type': 'application/json'})

                    response = None

                    with lock:
                        response = urllib2.urlopen(req)

                    if response.getcode() != 200:
                        # failed
                        response.close()
                        print "Failed to connect to http://%s/ec2/%s" % (server,methodName)
                    else:
                        clusterTest.unittestRollback.addOperations(methodName,server,post_data[1])
                        with list_lock:
                            list.append(d[0])

                    response.close()

                worker.enqueue(task,(self._lock,l,self._listLock,d,s,))

        worker.join()
        return True

    def prepare(self,num):
        return \
            self._prepareCameraData(CameraDataGenerator().generateCameraData,num,"saveCameras",self.conflictCameraList) and \
            self._prepareData(UserDataGenerator().generateUserData(num),"saveUser",self.conflictUserList) and \
            self._prepareData(MediaServerGenerator().generateMediaServerData(num),"saveMediaServer",self.conflictMediaServerList)


class ResourceDataGenerator(BasicGenerator):

    _ec2ResourceGetter = ["getCameras",
        "getMediaServersEx",
        "getUsers"]

    _resourceParEntryTemplate = """
        {
            "name":"%s",
            "resourceId":"%s",
            "value":"%s"
        }
    """

    _resourceRemoveTemplate = '{ "id":"%s" }'

    # this list contains all the existed resource that I can find.
    # The method for finding each resource is based on the API in
    # the list _ec2ResourceGetter.  What's more , the parentId, typeId
    # and resource name will be recorded (Can be None).
    _existedResourceList = []

    # this function is used to retrieve the resource list on the
    # server side.  We just retrieve the resource list from the
    # very first server since each server has exact same resource
    def _retrieveResourceUUIDList(self,num):
        gen = ConflictionDataGenerator()
        if not gen.prepare(num):
            return False

        # cameras
        for entry in gen.conflictCameraList:
            obj = json.loads(entry)[0]
            self._existedResourceList.append((obj["id"],obj["parentId"],obj["typeId"]))
        # users
        for entry in gen.conflictUserList:
            obj = json.loads(entry)
            self._existedResourceList.append((obj["id"],obj["parentId"],obj["typeId"]))
        # media server
        for entry in gen.conflictMediaServerList:
            obj = json.loads(entry)
            self._existedResourceList.append((obj["id"],obj["parentId"],obj["typeId"]))

        return True

    def __init__(self,num):
        ret = self._retrieveResourceUUIDList(num)
        if ret == False:
            raise Exception("cannot retrieve resources list on server side")

    def _generateKeyValue(self,uuid):
        key_len = random.randint(4,12)
        val_len = random.randint(24,512)
        return self._resourceParEntryTemplate % (self.generateRandomString(key_len),
            uuid,
            self.generateRandomString(val_len))

    def _getRandomResourceUUID(self):
        idx = random.randint(0,len(self._existedResourceList) - 1)
        return self._existedResourceList[idx][0]

    def _generateOneResourceParams(self):
        uuid = self._getRandomResourceUUID()
        kv_list = ["["]
        num = random.randint(2,20)
        for i in xrange(num - 1):
            num = random.randint(2,20)
            kv_list.append(self._generateKeyValue(uuid))
            kv_list.append(",")

        kv_list.append(self._generateKeyValue(uuid))
        kv_list.append("]")

        return ''.join(kv_list)

    def generateResourceParams(self,number):
        ret = []
        for i in xrange(number):
            ret.append(self._generateOneResourceParams())
        return ret

    def generateRemoveResource(self,number):
        ret = []
        for i in xrange(number):
            ret.append(self._resourceRemoveTemplate % (self._getRandomResourceUUID()))
        return ret

# This class is used to generate data for simulating resource confliction

# Currently we don't have general method to _UPDATE_ an existed record in db,
# so I implement it through creation routine since this routine is the only way
# to modify the existed record now.
class CameraConflictionDataGenerator(BasicGenerator):
    #(id,mac,model,parentId,typeId,url,vendor)
    _existedCameraList = []
    # For simplicity , we just modify the name of this camera
    _updateTemplate = \
    """
        [{
            "groupId": "",
            "groupName": "",
            "id": "%s",
            "mac": "%s",
            "manuallyAdded": false,
            "maxArchiveDays": 0,
            "minArchiveDays": 0,
            "model": "%s",
            "motionMask": "",
            "motionType": "MT_Default",
            "name": "%s",
            "parentId": "%s",
            "physicalId": "%s",
            "preferedServerId": "{00000000-0000-0000-0000-000000000000}",
            "scheduleEnabled": false,
            "scheduleTasks": [ ],
            "secondaryStreamQuality": "SSQualityLow",
            "status": "Unauthorized",
            "statusFlags": "CSF_NoFlags",
            "typeId": "%s",
            "url": "%s",
            "vendor": "%s"
        }]
    """

    _removeTemplate = '{ "id":"%s" }'

    def _fetchExistedCameras(self,dataGen):
        for entry in dataGen.conflictCameraList:
            obj = json.loads(entry)[0]
            self._existedCameraList.append((obj["id"],obj["mac"],obj["model"],obj["parentId"],
                 obj["typeId"],obj["url"],obj["vendor"]))
        return True

    def __init__(self,dataGen):
        if self._fetchExistedCameras(dataGen) == False:
            raise Exception("Cannot get existed camera list")

    def _generateModify(self,camera):
        name = self.generateRandomString(random.randint(8,12))
        return self._updateTemplate % (camera[0],
            camera[1],
            camera[2],
            name,
            camera[3],
            camera[1],
            camera[4],
            camera[5],
            camera[6])

    def _generateRemove(self,camera):
        return self._removeTemplate % (camera[0])

    def generateData(self):
        camera = self._existedCameraList[random.randint(0,len(self._existedCameraList) - 1)]

        return (self._generateModify(camera),self._generateRemove(camera))


class UserConflictionDataGenerator(BasicGenerator):
    _updateTemplate = """
    {
        "digest": "%s",
        "email": "%s",
        "hash": "%s",
        "id": "%s",
        "isAdmin": false,
        "name": "%s",
        "parentId": "{00000000-0000-0000-0000-000000000000}",
        "permissions": "%s",
        "typeId": "{774e6ecd-ffc6-ae88-0165-8f4a6d0eafa7}",
        "url": ""
    }
    """

    _removeTemplate = '{ "id":"%s" }'

    _existedUserList = []

    def _fetchExistedUser(self,dataGen):
        for entry in dataGen.conflictUserList:
            obj = json.loads(entry)
            if obj["isAdmin"] == True:
                continue # skip admin
            self._existedUserList.append((obj["digest"],obj["email"],obj["hash"],
                                          obj["id"],obj["permissions"]))
        return True

    def __init__(self,dataGen):
        if self._fetchExistedUser(dataGen) == False:
            raise Exception("Cannot get existed user list")

    def _generateModify(self,user):
        name = self.generateRandomString(random.randint(8,20))

        return self._updateTemplate % (user[0],
            user[1],
            user[2],
            user[3],
            name,
            user[4])

    def _generateRemove(self,user):
        return self._removeTemplate % (user[3])


    def generateData(self):
        user = self._existedUserList[random.randint(0,len(self._existedUserList) - 1)]

        return(self._generateModify(user),self._generateRemove(user))


class MediaServerConflictionDataGenerator(BasicGenerator):
    _updateTemplate = """
    {
        "apiUrl": "%s",
        "authKey": "%s",
        "flags": "SF_HasPublicIP",
        "id": "%s",
        "name": "%s",
        "networkAddresses": "192.168.0.1;10.0.2.141;192.168.88.1;95.31.23.214",
        "panicMode": "PM_None",
        "parentId": "{00000000-0000-0000-0000-000000000000}",
        "systemInfo": "windows x64 win78",
        "systemName": "%s",
        "typeId": "{be5d1ee0-b92c-3b34-86d9-bca2dab7826f}",
        "url": "%s",
        "version": "2.3.0.0"
    }
    """

    _removeTemplate = '{ "id":"%s" }'

    _existedMediaServerList = []

    def _fetchExistedMediaServer(self,dataGen):
        for server in dataGen.conflictMediaServerList:
            obj = json.loads(server)
            self._existedMediaServerList.append((obj["apiUrl"],obj["authKey"],obj["id"],
                                                 obj["systemName"],obj["url"]))

        return True


    def __init__(self,dataGen):
        if self._fetchExistedMediaServer(dataGen) == False:
            raise Exception("Cannot fetch media server list")


    def _generateModify(self,server):
        name = self.generateRandomString(random.randint(8,20))

        return self._updateTemplate % (server[0],server[1],server[2],name,
            server[3],server[4])

    def _generateRemove(self,server):
        return self._removeTemplate % (server[2])

    def generateData(self):
        server = self._existedMediaServerList[random.randint(0,len(self._existedMediaServerList) - 1)]
        return (self._generateModify(server),self._generateRemove(server))


class CameraUserAttributesListDataGenerator(BasicGenerator):
    _template = """
        [
            {
                "audioEnabled": %s,
                "cameraID": "%s",
                "cameraName": "%s",
                "controlEnabled": %s,
                "dewarpingParams": "%s",
                "maxArchiveDays": -30,
                "minArchiveDays": -1,
                "motionMask": "5,0,0,44,32:5,0,0,44,32:5,0,0,44,32:5,0,0,44,32",
                "motionType": "MT_SoftwareGrid",
                "preferedServerId": "%s",
                "scheduleEnabled": %s,
                "scheduleTasks": [ ],
                "secondaryStreamQuality": "SSQualityMedium"
            }
        ]
        """

    _dewarpingTemplate = "{ \\\"enabled\\\":%s,\\\"fovRot\\\":%s,\
            \\\"hStretch\\\":%s,\\\"radius\\\":%s, \\\"viewMode\\\":\\\"VerticalDown\\\",\
            \\\"xCenter\\\":%s,\\\"yCenter\\\":%s}"

    _existedCameraUUIDList = []

    _lock = threading.Lock()
    _listLock = threading.Lock()

    def __init__(self,prepareNum):
        if self._fetchExistedCameraUUIDList(prepareNum) == False:
            raise Exception("Cannot initialize camera list attribute test data")

    def _prepareData(self,op,num,methodName,l):
        worker = ClusterWorker(8,num * len(clusterTest.clusterTestServerList))

        for _ in xrange(num):
            for s in clusterTest.clusterTestServerList:

                def task(lock,list,listLock,server,mname,oper):

                    with lock:
                        d = oper(1,s)[0]
                        req = urllib2.Request("http://%s/ec2/%s" % (server,mname),
                                data=d[0], headers={'Content-Type': 'application/json'})
                        response = urllib2.urlopen(req)

                    if response.getcode() != 200:
                        print "Failed to connect http://%s/ec2/%s" % (server,mname)
                        return
                    else:
                        clusterTest.unittestRollback.addOperations(mname,server,d[1])
                        with listLock:
                            list.append(d[0])

                    response.close()

                worker.enqueue(task,(self._lock,l,self._listLock,s,methodName,op,))

        worker.join()
        return True

    def _fetchExistedCameraUUIDList(self,num):
        # We could not use existed camera list since if we do so we may break
        # the existed
        # database on the server side.  What we gonna do is just create new
        # fake cameras and
        # then do the test by so.
        json_list = []

        if not self._prepareData(CameraDataGenerator().generateCameraData,num,"saveCameras",json_list):
            return False

        for entry in json_list:
            obj = json.loads(entry)[0]
            self._existedCameraUUIDList.append((obj["id"],obj["name"]))

        return True

    def _getRandomServerId(self):
        idx = random.randint(0,len(clusterTest.clusterTestServerUUIDList) - 1)
        return clusterTest.clusterTestServerUUIDList[idx][0]

    def _generateNormalizeRange(self):
        return str(random.random())

    def _generateDewarpingPar(self):
        return self._dewarpingTemplate % (self.generateTrueFalse(),
            self._generateNormalizeRange(),
            self._generateNormalizeRange(),
            self._generateNormalizeRange(),
            self._generateNormalizeRange(),
            self._generateNormalizeRange())

    def _getRandomCameraUUIDAndName(self):
        return self._existedCameraUUIDList[random.randint(0,len(self._existedCameraUUIDList) - 1)]

    def generateCameraUserAttribute(self,number):
        ret = []

        for i in xrange(number):
            uuid , name = self._getRandomCameraUUIDAndName()
            ret.append(self._template % (self.generateTrueFalse(),
                    uuid,name,
                    self.generateTrueFalse(),
                    self._generateDewarpingPar(),
                    self._getRandomServerId(),
                    self.generateTrueFalse()))

        return ret


class ServerUserAttributesListDataGenerator(BasicGenerator):
    _template = """
    [
        {
            "allowAutoRedundancy": %s,
            "maxCameras": %s,
            "serverID": "%s",
            "serverName": "%s"
        }
    ]
    """

    _existedFakeServerList = []

    _lock = threading.Lock()
    _listLock = threading.Lock()

    def _prepareData(self,dataList,methodName,l):
        worker = ClusterWorker(8,len(dataList) * len(clusterTest.clusterTestServerList))

        for d in dataList:
            for s in clusterTest.clusterTestServerList:

                def task(lock,list,listLock,post_data,mname,server):
                    req = urllib2.Request("http://%s/ec2/%s" % (server,mname),
                        data=post_data[0], headers={'Content-Type': 'application/json'})

                    with lock:
                        response = urllib2.urlopen(req)

                    if response.getcode() != 200:
                        print "Failed to connect http://%s/ec2/%s" % (server,mname)
                        return
                    else:
                        clusterTest.unittestRollback.addOperations(methodName,server,post_data[1])
                        with listLock:
                            list.append(d[0])

                    response.close()

                worker.enqueue(task,(self._lock,l,self._listLock,d,methodName,s,))

        worker.join()
        return True


    def _generateFakeServer(self,num):
        json_list = []

        if not self._prepareData(MediaServerGenerator().generateMediaServerData(num),"saveMediaServer",json_list):
            return False

        for entry in json_list:
            obj = json.loads(entry)
            self._existedFakeServerList.append((obj["id"],obj["name"]))

        return True

    def __init__(self,num):
        if not self._generateFakeServer(num) :
            raise Exception("Cannot initialize server list attribute test data")

    def _getRandomServer(self):
        idx = random.randint(0,len(self._existedFakeServerList) - 1)
        return self._existedFakeServerList[idx]

    def generateServerUserAttributesList(self,number):
        ret = []
        for i in xrange(number):
            uuid,name = self._getRandomServer()
            ret.append(self._template % (self.generateTrueFalse(),
                    random.randint(0,200),
                    uuid,name))
        return ret

####################################################################################################

class ClusterTestBase(unittest.TestCase):
    _Lock = threading.Lock()

    def _generateModifySeq(self):
        return None

    def _getMethodName(self):
        pass

    def _getObserverName(self):
        pass

    def _defaultModifySeq(self,fakeData):
        ret = []
        for f in fakeData:
            # pick up a server randomly
            ret.append((f,clusterTest.clusterTestServerList[random.randint(0,len(clusterTest.clusterTestServerList) - 1)]))
        return ret

    def _defaultCreateSeq(self,fakeData):
        ret = []
        for f in fakeData:
            serverName = clusterTest.clusterTestServerList[random.randint(0,len(clusterTest.clusterTestServerList) - 1)]
            # add rollback cluster operations
            clusterTest.unittestRollback.addOperations(self._getMethodName(),serverName,f[1])
            ret.append((f[0],serverName))

        return ret

    def _dumpFailedRequest(self,data,methodName):
        f = open("%s.failed.%.json" % (methodName,threading.active_count()),"w")
        f.write(data)
        f.close()

    def _sendRequest(self,methodName,d,server):
        req = urllib2.Request("http://%s/ec2/%s" % (server,methodName),
            data=d, headers={'Content-Type': 'application/json'})
        response = None

        with self._Lock:
            print "Connection to http://%s/ec2/%s" % (server,methodName)
            response = urllib2.urlopen(req)

        # Do a sligtly graceful way to dump the sample of failure
        if response.getcode() != 200:
            self._dumpFailedRequest(d,methodName)

        self.assertTrue(response.getcode() == 200,
            "%s failed with statusCode %d" % (methodName,response.getcode()))

        response.close()

    def run(self, result=None):
        if result is None: result = self.defaultTestResult()
        result.startTest(self)
        testMethod = getattr(self, self._testMethodName)
        try:
            #FIXME Refactor error handling!
            try:
                self.setUp()
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, sys.exc_info())
                return

            ok = False
            try:
                testMethod()
                ok = True
            except self.failureException:
                result.addFailure(self, sys.exc_info())
                result.stop()
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, sys.exc_info())
                result.stop()

            try:
                self.tearDown()
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, sys.exc_info())
                ok = False
            if ok: result.addSuccess(self)
        finally:
            result.stopTest(self)

    def test(self):
        postDataList = self._generateModifySeq()

        # skip this class
        if postDataList == None:
            return

        workerQueue = ClusterWorker(clusterTest.threadNumber,len(postDataList))

        print "\n===================================\n"
        print "Test:%s start!\n" % (self._getMethodName())

        for test in postDataList:
            workerQueue.enqueue(self._sendRequest , (self._getMethodName(),test[0],test[1],))

        workerQueue.join()

        time.sleep(clusterTest.clusterTestSleepTime)
        observer = self._getObserverName()

        if isinstance(observer,(list)):
            for m in observer:
                ret,reason = clusterTest.checkMethodStatusConsistent(m)
                self.assertTrue(ret,reason)
        else:
            ret , reason = clusterTest.checkMethodStatusConsistent(observer)
            self.assertTrue(ret,reason)

        #DEBUG
        #self.assertNotEqual(0, 0, "DEBUG FAIL")

        print "Test:%s finish!\n" % (self._getMethodName())
        print "===================================\n"


class CameraTest(ClusterTestBase):
    _gen = None
    _testCase = clusterTest.testCaseSize

    def setTestCase(self,num):
        self._testCase = num

    def setUp(self):
        self._testCase = clusterTest.testCaseSize
        self._gen = CameraDataGenerator()


    def _generateModifySeq(self):
        ret = []
        for _ in xrange(self._testCase):
            s = clusterTest.clusterTestServerList[random.randint(0,len(clusterTest.clusterTestServerList) - 1)]
            data = self._gen.generateCameraData(1,s)[0]
            clusterTest.unittestRollback.addOperations(self._getMethodName(),s,data[1])
            ret.append((data[0],s))
        return ret

    def _getMethodName(self):
        return "saveCameras"

    def _getObserverName(self):
        return "getCameras?format=json"


class UserTest(ClusterTestBase):
    _gen = None
    _testCase = clusterTest.testCaseSize

    def setTestCase(self,num):
        self._testCase = num

    def setUp(self):
        self._testCase = clusterTest.testCaseSize
        self._gen = UserDataGenerator()

    def _generateModifySeq(self):
        return self._defaultCreateSeq(self._gen.generateUserData(self._testCase))

    def _getMethodName(self):
        return "saveUser"

    def _getObserverName(self):
        return "getUsers?format=json"


class MediaServerTest(ClusterTestBase):
    _gen = None
    _testCase = clusterTest.testCaseSize

    def setTestCase(self,num):
        self._testCase = num

    def setUp(self):
        self._testCase = clusterTest.testCaseSize
        self._gen = MediaServerGenerator()

    def _generateModifySeq(self):
        return self._defaultCreateSeq(self._gen.generateMediaServerData(self._testCase))

    def _getMethodName(self):
        return "saveMediaServer"

    def _getObserverName(self):
        return "getMediaServersEx?format=json"


class ResourceParaTest(ClusterTestBase):
    _gen = None
    _testCase = clusterTest.testCaseSize

    def setTestCase(self,num):
        self._testCase = num

    def setUp(self):
        self._testCase = clusterTest.testCaseSize
        self._gen = ResourceDataGenerator(self._testCase * 2)

    def _generateModifySeq(self):
        return self._defaultModifySeq(self._gen.generateResourceParams(self._testCase))

    def _getMethodName(self):
        return "setResourceParams"

    def _getObserverName(self):
        return "getResourceParams?format=json"


class ResourceRemoveTest(ClusterTestBase):
    _gen = None
    _testCase = clusterTest.testCaseSize

    def setTestCase(self,num):
        self._testCase = num

    def setUp(self):
        self._testCase = clusterTest.testCaseSize
        self._gen = ResourceDataGenerator(self._testCase * 2)

    def _generateModifySeq(self):
        return self._defaultModifySeq(self._gen.generateRemoveResource(self._testCase))

    def _getMethodName(self):
        return "removeResource"

    def _getObserverName(self):
        return ["getMediaServersEx?format=json",
                "getUsers?format=json",
                "getCameras?format=json"]


class CameraUserAttributeListTest(ClusterTestBase):
    _gen = None
    _testCase = clusterTest.testCaseSize

    def setTestCase(self,num):
        self._testCase = num

    def setUp(self):
        self._testCase = clusterTest.testCaseSize
        self._gen = CameraUserAttributesListDataGenerator(self._testCase * 2)

    def _generateModifySeq(self):
        return self._defaultModifySeq(self._gen.generateCameraUserAttribute(self._testCase))

    def _getMethodName(self):
        return "saveCameraUserAttributesList"

    def _getObserverName(self):
        return "getCameraUserAttributes"


class ServerUserAttributesListDataTest(ClusterTestBase):
    _gen = None
    _testCase = clusterTest.testCaseSize

    def setTestCase(self,num):
        self._testCase = num

    def setUp(self):
        self._testCase = clusterTest.testCaseSize
        self._gen = ServerUserAttributesListDataGenerator(self._testCase * 2)

    def _generateModifySeq(self):
        return self._defaultModifySeq(self._gen.generateServerUserAttributesList(self._testCase))

    def _getMethodName(self):
        return "saveServerUserAttributesList"

    def _getObserverName(self):
        return "getServerUserAttributes"

# The following test will issue the modify and remove on different servers to
# trigger confliction resolving.
class ResourceConflictionTest(ClusterTestBase):
    _testCase = clusterTest.testCaseSize
    _conflictList = []

    def setTestCase(self,num):
        self._testCase = num

    def setUp(self):
        dataGen = ConflictionDataGenerator()

        print "Start confliction data preparation, this will generate Cameras/Users/MediaServers"
        dataGen.prepare(clusterTest.testCaseSize)
        print "Confilication data generation done"

        self._testCase = clusterTest.testCaseSize
        self._conflictList = [("removeResource","saveMediaServer",MediaServerConflictionDataGenerator(dataGen)),
            ("removeResource","saveUser",UserConflictionDataGenerator(dataGen)),
            ("removeResource","saveCameras",CameraConflictionDataGenerator(dataGen))]

    def _generateRandomServerPair(self):
        # generate first server here
        s1 = clusterTest.clusterTestServerList[random.randint(0,len(clusterTest.clusterTestServerList) - 1)]
        s2 = None
        if len(clusterTest.clusterTestServerList) == 1:
            s2 = s1
        else:
            while True:
                s2 = clusterTest.clusterTestServerList[random.randint(0,len(clusterTest.clusterTestServerList) - 1)]
                if s2 != s1:
                    break
        return (s1,s2)

    def _generateResourceConfliction(self):
        return self._conflictList[random.randint(0,len(self._conflictList) - 1)]

    def _checkStatus(self):
        apiList = ["getMediaServersEx?format=json",
            "getUsers?format=json",
            "getCameras?format=json"]

        time.sleep(clusterTest.clusterTestSleepTime)
        for api in  apiList:
            ret , reason = clusterTest.checkMethodStatusConsistent(api)
            self.assertTrue(ret,reason)


    # Overwrite the test function since the base method doesn't work here

    def test(self):
        workerQueue = ClusterWorker(clusterTest.threadNumber,self._testCase * 2)

        print "===================================\n"
        print "Test:ResourceConfliction start!\n"

        for _ in xrange(self._testCase):
            conf = self._generateResourceConfliction()
            s1,s2 = self._generateRandomServerPair()
            data = conf[2].generateData()

            # modify the resource
            workerQueue.enqueue(self._sendRequest , (conf[1],data[0][0],s1,))
            # remove the resource
            workerQueue.enqueue(self._sendRequest , (conf[0],data[0][1],s2,))

        workerQueue.join()

        self._checkStatus()

        print "Test:ResourceConfliction finish!\n"
        print "===================================\n"

####################################################################################################

# ========================================
# Server Merge Automatic Test
# ========================================
class MergeTestBase:
    _systemName = []
    _oldSystemName = []
    _mergeTestSystemName = "mergeTest"
    _mergeTestTimeout = 1

    def __init__(self):
        self._mergeTestTimeout = clusterTest.getConfig().getint("General","mergeTestTimeout")

    # This function is used to generate unique system name but random.  It
    # will gaurantee that the generated name is UNIQUE inside of the system
    def _generateRandomSystemName(self):
        ret = []
        s = set()
        for i in xrange(len(clusterTest.clusterTestServerList)):
            length = random.randint(16,30)
            while True:
                name = BasicGenerator.generateRandomString(length)
                if name in s or name == self._mergeTestSystemName:
                    continue
                else:
                    s.add(name)
                    ret.append(name)
                    break
        return ret

    # This function is used to store the old system name of each server in
    # the clusters
    def _storeClusterOldSystemName(self):
        for s in clusterTest.clusterTestServerList:
            print "Connection to http://%s/ec2/testConnection" % (s)
            response = urllib2.urlopen("http://%s/ec2/testConnection" % (s))
            if response.getcode() != 200:
                return False
            jobj = SafeJsonLoads(response.read(), s, 'testConnection')
            if jobj is None:
                return False
            self._oldSystemName.append(jobj["systemName"])
            response.close()
        return True

    def _setSystemName(self,addr,name):
        print "Connection to http://%s/api/configure" % (addr)
        response = urllib2.urlopen("http://%s/api/configure?%s" % (addr,urllib.urlencode({"systemName":name})))
        if response.getcode() != 200 :
            return (False,"Cannot issue changeSystemName with HTTP code:%d to server:%s" % (response.getcode()),addr)
        response.close()
        return (True,"")

    # This function is used to set the system name to randome
    def _setClusterSystemRandom(self):
        # Store the old system name here
        self._storeClusterOldSystemName()
        testList = self._generateRandomSystemName()
        for i in xrange(len(clusterTest.clusterTestServerList)):
            self._setSystemName(clusterTest.clusterTestServerList[i],testList[i])

    def _setClusterToMerge(self):
        for s in clusterTest.clusterTestServerList:
            self._setSystemName(s,self._mergeTestSystemName)

    def _rollbackSystemName(self):
        for i in xrange(len(clusterTest.clusterTestServerList)):
            self._setSystemName(clusterTest.clusterTestServerList[i],self._oldSystemName[i])


# This class represents a single server with a UNIQUE system name.
# After we initialize this server, we will make it executes certain
# type of random data generation, after such generation, the server
# will have different states with other servers
class PrepareServerStatus(BasicGenerator):
    _minData = 10
    _maxData = 20

    getterAPI = ["getResourceParams",
        "getMediaServers",
        "getMediaServersEx",
        "getCameras",
        "getUsers",
        "getServerUserAttributes",
        "getCameraUserAttributes"]

    _mergeTest = None

    def __init__(self,mt):
        self._mergeTest = mt

    # Function to generate method and class matching
    def _generateDataAndAPIList(self,addr):

        def cameraFunc(num):
            gen = CameraDataGenerator()
            return gen.generateCameraData(num,addr)

        def userFunc(num):
            gen = UserDataGenerator()
            return gen.generateUserData(num)

        def mediaServerFunc(num):
            gen = MediaServerGenerator()
            return gen.generateMediaServerData(num)

        return [("saveCameras",cameraFunc),
                ("saveUser",userFunc),
                ("saveMediaServer",mediaServerFunc)]

    def _sendRequest(self,addr,method,d):
        req = urllib2.Request("http://%s/ec2/%s" % (addr,method), \
              data=d,
              headers={'Content-Type': 'application/json'})

        with self._mergeTest._lock:
            print "Connection to http://%s/ec2/%s" % (addr,method)
            response = urllib2.urlopen(req)

        if response.getcode() != 200 :
            return (False,"Cannot issue %s with HTTP code:%d to server:%s" % (method,response.getcode(),addr))

        response.close()

        return (True,"")

    def _generateRandomStates(self,addr):
        api_list = self._generateDataAndAPIList(addr)
        for api in api_list:
            num = random.randint(self._minData,self._maxData)
            data_list = api[1](num)
            for data in data_list:
                ret,reason = self._sendRequest(addr,api[0],data[0])
                if ret == False:
                    return (ret,reason)
                clusterTest.unittestRollback.addOperations(api[0],addr,data[1])

        return (True,"")

    def main(self,addr):
        ret,reason = self._generateRandomStates(addr)
        if ret == False:
            raise Exception("Cannot generate random states:%s" % (reason))


# This class is used to control the whole merge test
class MergeTest_Resource(MergeTestBase):
    _lock = threading.Lock()

    def _prolog(self):
        print "Merge test prolog : Test whether all servers you specify has the identical system name"
        oldSystemName = None
        oldSystemNameAddr = None

        # Testing whether all the cluster server has identical system name
        for s in clusterTest.clusterTestServerList:
            print "Connection to http://%s/ec2/testConnection" % (s)
            response = urllib2.urlopen("http://%s/ec2/testConnection" % (s))
            if response.getcode() != 200:
                return False
            jobj = SafeJsonLoads(response.read(), s, 'testConnection')
            if jobj is None:
                return False
            if oldSystemName == None:
                oldSystemName = jobj["systemName"]
                oldSystemNameAddr = s
            else:
                systemName = jobj["systemName"]
                if systemName != oldSystemName:
                    print "The merge test cannot start!"
                    print "Server:%s has system name:%s" % (oldSystemName,oldSystemNameAddr)
                    print "Server:%s has system name:%s" % (s,jobj["systemName"])
                    print "Please make all the server has identical system name before running merge test"
                    return False
            response.close()

        print "Merge test prolog pass"
        return True

    def _epilog(self):
        print "Merge test epilog, change all servers system name back to its original one"
        self._rollbackSystemName()
        print "Merge test epilog done"

    # First phase will make each server has its own status
    # and also its unique system name there

    def _phase1(self):
        print "Merge test phase1: generate UNIQUE system name for each server and do modification"
        # 1.  Set cluster system name to random name
        self._setClusterSystemRandom()

        # 2.  Start to generate server status and data
        worker = ClusterWorker(clusterTest.threadNumber,len(clusterTest.clusterTestServerList))

        for s in clusterTest.clusterTestServerList:
            worker.enqueue(PrepareServerStatus(self).main,(s,))

        worker.join()
        print "Merge test phase1 done, now sleep %s seconds and wait for sync" % self._mergeTestTimeout
        time.sleep(self._mergeTestTimeout)

    def _phase2(self):
        print "Merge test phase2: set ALL the servers with system name :mergeTest"
        self._setClusterToMerge()
        print "Merge test phase2: wait %s seconds for sync" % self._mergeTestTimeout
        # Wait until the synchronization time out expires
        time.sleep(self._mergeTestTimeout)
        # Do the status checking of _ALL_ API
        for api in PrepareServerStatus.getterAPI:
            ret , reason = clusterTest.checkMethodStatusConsistent("%s?format=json" % (api))
            if ret == False:
                return (ret,reason)
        print "Merge test phase2 done"
        return (True,"")

    def test(self):
        print "================================\n"
        print "Server Merge Test: Resource Start\n"
        if not self._prolog():
            print "FAIL: Merge Test: Resource prolog failed!"
            return False
        self._phase1()
        ret,reason = self._phase2()
        if not ret:
            print "FAIL: %s" % reason
        self._epilog()
        print "Server Merge Test: Resource End%s\n" % ('' if ret else ": test FAILED")
        print "================================\n"
        return ret

# This merge test is used to test admin's password
# Steps:
# Change _EACH_ server into different system name
# Modify _EACH_ server's password into a different one
# Reconnect to _EACH_ server with _NEW_ password and change its system name back to mergeTest
# Check _EACH_ server's status that with a possible password in the list and check getMediaServer's Status
# also _ALL_ the server must be Online

# NOTES:
# I found a very radiculous truth, that if one urllib2.urlopen failed with authentication error, then the
# opener will be screwed up, and you have to reinstall that openner again. This is really stupid truth .

class MergeTest_AdminPassword(MergeTestBase):
    _newPasswordList = dict() # list contains key:serverAddr , value:password
    _oldClusterPassword = None # old cluster user password , it should be 123 always
    _username = None # User name for cluster, it should be admin
    _clusterSharedPassword = None
    _adminList = dict() # The dictionary for admin user on each server

    def __init__(self):
        # load the configuration file for username and oldClusterPassword
        config_parser = clusterTest.getConfig()
        self._oldClusterPassword = config_parser.get("General","password")
        self._username = config_parser.get("General","username")

    def _generateUniquePassword(self):
        ret = []
        s = set()
        for server in clusterTest.clusterTestServerList:
            # Try to generate a unique password
            pwd = BasicGenerator.generateRandomString(20)
            if pwd in s:
                continue
            else:
                # The password is new password
                ret.append((server,pwd))
                self._newPasswordList[server]=pwd

        return ret
    # This function MUST be called after you change each server's
    # password since we need to update the installer of URLLIB2

    def _setUpNewAuthentication(self, pwdlist):
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        for entry in pwdlist:
            ManagerAddPassword(passman, entry[0], self._username, entry[1])
        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPDigestAuthHandler(passman)))

    def _setUpClusterAuthentication(self, password):
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        for s in clusterTest.clusterTestServerList:
            ManagerAddPassword(passman, s, self._username, password)
        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPDigestAuthHandler(passman)))

    def _restoreAuthentication(self):
        self._setUpClusterAuthentication(self._oldClusterPassword)

    def _merge(self):
        self._setClusterToMerge()
        time.sleep(self._mergeTestTimeout)

    def _checkPassword(self,pwd,old_server,login_server):
        print "Password:%s that initially modified on server:%s can log on to server:%s in new cluster"%(pwd,old_server,login_server)
        print "Notes,the above server can be the same one, however since this test is after merge, it still makes sense"
        print "Now test whether it works on the cluster"
        for s in clusterTest.clusterTestServerList:
            if s == login_server:
                continue
            else:
                response = None
                try:
                    response = urllib2.urlopen("http://%s/ec2/testConnection"%(s))
                except urllib2.URLError,e:
                    print "This password cannot log on server:%s"%(s)
                    print "This means this password can be used partially on cluster which is not supposed to happen"
                    print "The cluster is not synchronized after merge"
                    print "Error:%s"%(e)
                    return False

        print "This password can be used on the whole cluster"
        return True

    # This function is used to probe the correct password that _CAN_ be used to log on each server
    def _probePassword(self):
        possiblePWD = None
        for entry in self._newPasswordList:
            pwd = self._newPasswordList[entry]
            # Set Up the Authencation here
            self._setUpClusterAuthentication(pwd)
            for server in clusterTest.clusterTestServerList:
                response = None
                try:
                    response = urllib2.urlopen("http://%s/ec2/testConnection"%(server))
                except urllib2.URLError,e:
                    # Every failed urllib2.urlopen will screw up the opener
                    self._setUpClusterAuthentication(pwd)
                    continue # This password doesn't work

                if response.getcode() != 200:
                    response.close()
                    continue
                else:
                    possiblePWD = pwd
                    break
            if possiblePWD != None:
                if self._checkPassword(possiblePWD,entry,server):
                    self._clusterSharedPassword = possiblePWD
                    return True
                else:
                    return False
        print "No password is found while probing the cluster"
        print "This means after the merge,all the password originally on each server CANNOT be used to log on any server after merge"
        print "This means cluster is not synchronized"
        return False

    # This function is used to test whether all the server gets the exactly same status
    def _checkAllServerStatus(self):
        self._setUpClusterAuthentication(self._clusterSharedPassword)
        # Now we need to set up the check
        ret,reason = clusterTest.checkMethodStatusConsistent("getMediaServersEx?format=json")
        if not ret:
            print reason
            return False
        else:
            return True

    def _checkOnline(self,uidset,responseObj,serverAddr):
        if responseObj is None:
            return False
        for ele in responseObj:
            if ele["id"] in uidset:
                if ele["status"] != "Online":
                    # report the status
                    print "Login at server:%s"%(serverAddr)
                    print "The server:(%s) with name:%s and id:%s status is Offline"%(ele["networkAddresses"],ele["name"],ele["id"])
                    print "It should be Online after the merge"
                    print "Status check failed"
                    return False
        print "Status check for server:%s pass!"%(serverAddr)
        return True

    def _checkAllOnline(self):
        uidSet = set()
        # Set up the UID set for each registered server
        for uid in clusterTest.clusterTestServerUUIDList:
            uidSet.add(uid[0])

        # For each server test whether they work or not
        for s in clusterTest.clusterTestServerList:
            print "Connection to http://%s/ec2/getMediaServersEx?format=json"%(s)
            response = urllib2.urlopen("http://%s/ec2/getMediaServersEx?format=json"%(s))
            if response.getcode() != 200:
                print "Connection failed with HTTP code:%d"%(response.getcode())
                return False
            if not self._checkOnline(uidSet, SafeJsonLoads(response.read(), s, 'getMediaServersEx'),s):
                return False

        return True

    def _fetchAdmin(self):
        for s in clusterTest.clusterTestServerList:
            response = urllib2.urlopen("http://%s/ec2/getUsers"%(s))
            obj = SafeJsonLoads(response.read(), s, 'getUsers')
            if obj is None:
                return None
            for entry in obj:
                if entry["isAdmin"]:
                    self._adminList[s] = (entry["id"],entry["name"],entry["email"])
        return True

    def _setAdminPassword(self,ser,pwd,verbose=True):
        oldAdmin = self._adminList[ser]
        d = UserDataGenerator().createManualUpdateData(oldAdmin[0],oldAdmin[1],pwd,True,oldAdmin[2])
        req = urllib2.Request("http://%s/ec2/saveUser" % (ser), \
                data=d, headers={'Content-Type': 'application/json'})
        try:
            response =urllib2.urlopen(req)
        except:
            if verbose:
                print "Connection http://%s/ec2/saveUsers failed"%(ser)
                print "Cannot set admin password:%s to server:%s"%(pwd,ser)
            return False

        if response.getcode() != 200:
            response.close()
            if verbose:
                print "Connection http://%s/ec2/saveUsers failed"%(ser)
                print "Cannot set admin password:%s to server:%s"%(pwd,ser)
            return False
        else:
            response.close()
            return True

    # This rollback is bit of tricky since it NEEDS to rollback partial password change
    def _rollbackPartialPasswordChange(self,pwdlist):
        # Now rollback the newAuth part of the list
        for entry in pwdlist:
            if not self._setAdminPassword(entry[0],self._oldClusterPassword):
                print "----------------------------------------------------------------------------------"
                print "+++++++++++++++++++++++++++++++++++ IMPORTANT ++++++++++++++++++++++++++++++++++++"
                print "Server:%s admin password cannot rollback,please set it back manually!"%(entry[0])
                print "It's current password is:%s"%(entry[1])
                print "It's old password is:%s"(self._oldClusterPassword)
                print "----------------------------------------------------------------------------------"
        # Now set back the authentcation
        self._restoreAuthentication()

    # This function is used to change admin's password on each server
    def _changePassword(self):
        pwdlist = self._generateUniquePassword()
        uGen = UserDataGenerator()
        idx = 0
        for entry in pwdlist:
            pwd = entry[1]
            ser = entry[0]
            if self._setAdminPassword(ser,pwd):
                idx = idx+1
            else:
                # Before rollback we need to setup the authentication
                partialList = pwdlist[:idx]
                self._setUpNewAuthentication(partialList)
                # Rollback the password paritally
                self._rollbackPartialPasswordChange(partialList)
                return False
        # Set Up New Authentication
        self._setUpNewAuthentication(pwdlist)
        return True

    def _rollback(self):
        # rollback the password to the old states
        self._rollbackPartialPasswordChange(
            [(s,self._oldClusterPassword) for s in clusterTest.clusterTestServerList])

        # rollback the system name
        self._rollbackSystemName()

    def _failRollbackPassword(self):
        # The current problem is that we don't know which password works so
        # we use a very conservative way to do the job. We use every password
        # that may work to change the whole cluster
        addrSet = set()

        for server in self._newPasswordList:
            pwd = self._newPasswordList[server]
            authList = [(s,pwd) for s in clusterTest.clusterTestServerList]
            self._setUpNewAuthentication(authList)

            # Now try to login on to the server and then set back the admin
            check = False
            for ser in clusterTest.clusterTestServerList:
                if ser in addrSet:
                    continue
                check = True
                if self._setAdminPassword(ser,self._oldClusterPassword,False):
                    addrSet.add(ser)
                else:
                    self._setUpNewAuthentication(authList)

            if not check:
                return True

        if len(addrSet) != len(clusterTest.clusterTestServerList):
            print "There're some server's admin password I cannot prob and rollback"
            print "Since it is a failover rollback,I cannot guarantee that I can rollback the whole cluster"
            print "There're possible bugs in the cluster that make the automatic rollback impossible"
            print "The following server has _UNKNOWN_ password now"
            for ser in clusterTest.clusterTestServerList:
                if ser not in addrSet:
                    print "The server:%s has _UNKNOWN_ password for admin"%(ser)
            return False
        else:
            return True

    def _failRollback(self):
        print "==========================================="
        print "Start Failover Rollback"
        print "This rollback will _ONLY_ happen when the merge test failed"
        print "This rollback cannot guarantee that it will rollback everything"
        print "Detail information will be reported during the rollback"
        if self._failRollbackPassword():
            self._restoreAuthentication()
            self._rollbackSystemName()
            print "Failover Rollback Done!"
        else:
            print "Failover Rollback Failed!"
        print "==========================================="

    def test(self):
        print "==========================================="
        print "Merge Test:Admin Password Test Start!"
        # At first, we fetch each system's admin information
        if self._fetchAdmin() is None:
            print "Merge Test:Fetch Admins list failed"
            return False
        # Change each system into different system name
        print "Now set each server node into different and UNIQUE system name\n"
        self._setClusterSystemRandom()
        # Change the password of _EACH_ servers
        print "Now change each server node's admin password to a UNIQUE password\n"
        if not self._changePassword():
            print "Merge Test:Admin Password Test Failed"
            return False
        print "Now set the system name back to mergeTest and wait for the merge\n"
        self._merge()
        # Now start to probing the password
        print "Start to prob one of the possible password that can be used to LOG to the cluster\n"
        if not self._probePassword():
            print "Merge Test:Admin Password Test Failed"
            self._failRollback()
            return False
        print "Check all the server status\n"
        # Now start to check the status
        if not self._checkAllServerStatus():
            print "Merge Test:Admin Password Test Failed"
            self._failRollback()
            return False
        print "Check all server is Online or not"
        if not self._checkAllOnline():
            print "Merge Test:Admin Password Test Failed"
            self._failRollback()
            return False

        print "Lastly we do rollback\n"
        self._rollback()

        print "Merge Test:Admin Password Test Pass!"
        print "==========================================="
        return True


class MergeTest(object):

    def __init__(self, needCleanUp=False):
        self._CleanUp = needCleanUp

    def run(self):
        try:
            if not MergeTest_Resource().test():
                return False
            # The following merge test ALWAYS fail and I don't know it is my problem or not
            # Current it is disabled and you could use a seperate command line to run it
            #MergeTest_AdminPassword().test()
            return True
        finally:
            if self._CleanUp:
                doCleanUp()



# ===================================
# Performance test function
# only support add/remove ,value can only be user and media server
# ===================================

class PerformanceOperation():
    _lock = threading.Lock()

    def _filterOutId(self,list):
        ret = []
        for i in list:
            ret.append(i[0])
        return ret

    def _sendRequest(self,methodName,d,server):
        req = urllib2.Request("http://%s/ec2/%s" % (server,methodName), data=d,
                              headers={'Content-Type': 'application/json'})

        response = None

        with self._lock:
            response = urllib2.urlopen(req)

        # Do a sligtly graceful way to dump the sample of failure
        if response.getcode() != 200:
            self._dumpFailedRequest(d,methodName) #FIXME WTF?! looks like this was copy-pasted but the referred method wasn't!

        if response.getcode() != 200:
            print "%s failed with statusCode %d" % (methodName,response.getcode())
        else:
            print "%s OK\r\n" % (methodName)

        response.close()

    def _getUUIDList(self,methodName):
        ret = []
        for s in clusterTest.clusterTestServerList:
            data = []

            response = urllib2.urlopen("http://%s/ec2/%s?format=json" % (s,methodName))

            if response.getcode() != 200:
                return None

            json_obj = SafeJsonLoads(response.read(), s, methodName)
            if json_obj is None:
                return None
            for entry in json_obj:
                if "isAdmin" in entry and entry["isAdmin"] == True:
                    continue # Skip the admin
                data.append(entry["id"])

            response.close()

            ret.append((s,data))

        return ret

    # This function will retrieve data that has name prefixed with ec2_test as
    # prefix
    # This sort of resources are generated by our software .

    def _getFakeUUIDList(self,methodName):
        ret = []
        for s in clusterTest.clusterTestServerList:
            data = []

            response = urllib2.urlopen("http://%s/ec2/%s?format=json" % (s,methodName))

            if response.getcode() != 200:
                return None

            json_obj = SafeJsonLoads(response.read(), s, methodName)
            if json_obj is None:
                return None
            for entry in json_obj:
                if "name" in entry and entry["name"].startswith("ec2_test"):
                    if "isAdmin" in entry and entry["isAdmin"] == True:
                        continue
                    data.append(entry["id"])
            response.close()
            ret.append((s,data))
        return ret

    def _sendOp(self,methodName,dataList,addr):
        worker = ClusterWorker(clusterTest.threadNumber,len(dataList))
        for d in dataList:
            worker.enqueue(self._sendRequest,(methodName,d,addr))

        worker.join()

    _resourceRemoveTemplate = """
        {
            "id":"%s"
        }
    """
    def _removeAll(self,uuidList):
        data = []
        for entry in uuidList:
            for uuid in entry[1]:
                data.append(self._resourceRemoveTemplate % (uuid))
            self._sendOp("removeResource",data,entry[0])

    def _remove(self,uuid):
        self._removeAll([("127.0.0.1:7001",[uuid])])


class UserOperation(PerformanceOperation):
    def add(self,num):
        gen = UserDataGenerator()
        for s in clusterTest.clusterTestServerList:
            self._sendOp("saveUser",
                         self._filterOutId(gen.generateUserData(num)),s)

        return True

    def remove(self,who):
        self._remove(who)
        return True

    def removeAll(self):
        uuidList = self._getUUIDList("getUsers?format=json")
        if uuidList == None:
            return False
        self._removeAll(uuidList)
        return True

    def removeAllFake(self):
        uuidList = self._getFakeUUIDList("getUsers?format=json")
        if uuidList == None:
            return False
        self._removeAll(uuidList)
        return True


class MediaServerOperation(PerformanceOperation):
    def add(self,num):
        gen = MediaServerGenerator()
        for s in clusterTest.clusterTestServerList:
            self._sendOp("saveMediaServer",
                         self._filterOutId(gen.generateMediaServerData(num)),s)
        return True

    def remove(self, uuid):
        self._remove(uuid)
        return True

    def removeAll(self):
        uuidList = self._getUUIDList("getMediaServersEx?format=json")
        if uuidList == None:
            return False
        self._removeAll(uuidList)
        return True

    def removeAllFake(self):
        uuidList = self._getFakeUUIDList("getMediaServersEx?format=json")
        if uuidList == None:
            return False
        self._removeAll(uuidList)
        return True


class CameraOperation(PerformanceOperation):
    def add(self,num):
        gen = CameraDataGenerator()
        for s in clusterTest.clusterTestServerList:
            self._sendOp("saveCameras",
                         self._filterOutId(gen.generateCameraData(num,s)),s)
        return True

    def remove(self,uuid):
        self._remove(uuid)
        return True

    def removeAll(self):
        uuidList = self._getUUIDList("getCameras?format=json")
        if uuidList == None:
            return False
        self._removeAll(uuidList)
        return True

    def removeAllFake(self):
        uuidList = self._getFakeUUIDList("getCameras?format=json")
        if uuidList == None:
            return False
        self._removeAll(uuidList)
        return True


def doClearAll(fake=False):
    if fake:
        CameraOperation().removeAllFake()
        UserOperation().removeAllFake()
        MediaServerOperation().removeAllFake()
    else:
        CameraOperation().removeAll()
        UserOperation().removeAll()
        MediaServerOperation().removeAll()


def runMiscFunction(argc, argv):
    if argc not in (2, 3):
        return (False,"2/1 parameters are needed")

    l = argv[1].split('=')

    if l[0] != '--add' and l[0] != '--remove':
        return (False,"Unknown first parameter options")

    t = globals()["%sOperation" % (l[1])]

    if t == None:
        return (False,"Unknown target operations:%s" % (l[1]))
    else:
        t = t()

    if l[0] == '--add':
        if argc != 3 :
            return (False,"--add must have --count option")
        l = argv[2].split('=')
        if l[0] == '--count':
            num = int(l[1])
            if num <= 0 :
                return (False,"--count must be positive integer")
            if t.add(num) == False:
                return (False,"cannot perform add operation")
        else:
            return (False,"--add can only have --count options")
    elif l[0] == '--remove':
        if argc == 3:
            l = argv[2].split('=')
            if l[0] == '--id':
                if t.remove(l[1]) == False:
                    return (False,"cannot perform remove UID operation")
            elif l[0] == '--fake':
                if t.removeAllFake() == False:
                    return (False,"cannot perform remove UID operation")
            else:
                return (False,"--remove can only have --id options")
        elif argc == 2:
            if t.removeAll() == False:
                return (False,"cannot perform remove all operation")
    else:
        return (False,"Unknown command:%s" % (l[0]))

    return True


# ===================================
# Perf Test
# ===================================
class SingleResourcePerfGenerator:
    def generateUpdate(self,id,parentId):
        pass

    def generateCreation(self,parentId):
        pass

    def saveAPI(self):
        pass

    def updateAPI(self):
        pass

    def getAPI(self):
        pass

    def resourceName(self):
        pass

class SingleResourcePerfTest:
    _creationProb = 0.333
    _updateProb = 0.5
    _resourceList = []
    _lock = threading.Lock()
    _globalLock = None
    _resourceGen = None
    _serverAddr = None
    _initialData = 10
    _deletionTemplate = """
        {
            "id":"%s"
        }
    """

    def __init__(self,glock,gen,addr):
        self._globalLock = glock
        self._resourceGen = gen
        self._serverAddr = addr
        self._initializeResourceList()

    def _initializeResourceList(self):
        for _ in xrange(self._initialData):
            self._create()

    def _create(self):
        d = self._resourceGen.generateCreation(self._serverAddr)
        # Create the resource in the remote server
        response = None

        with self._globalLock:
            req = urllib2.Request("http://%s/ec2/%s" % (self._serverAddr,self._resourceGen.saveAPI()),
                data=d[0], headers={'Content-Type': 'application/json'})
            try:
                response = urllib2.urlopen(req)
            except urllib2.URLError,e:
                return False

        if response.getcode() != 200:
            response.close()
            return False
        else:
            response.close()
            clusterTest.unittestRollback.addOperations("saveCameras",self._serverAddr,d[1])
            with self._lock:
                self._resourceList.append(d[1])
                return True

    def _remove(self):
        id = None
        # Pick up a deleted resource Id
        with self._lock:
            if len(self._resourceList) == 0:
                return True
            idx = random.randint(0,len(self._resourceList) - 1)
            id = self._resourceList[idx]
            # Do the deletion from the list FIRST
            del self._resourceList[idx]

        # Do the deletion on remote machine
        with self._globalLock:
            req = urllib2.Request("http://%s/ec2/removeResource" % (self._serverAddr),
                data=self._deletionTemplate % (id), headers={'Content-Type': 'application/json'})
            try:
                response = urllib2.urlopen(req)
            except urllib2.URLError,e:
                return False

            if response.getcode() != 200:
                response.close()
                return False
            else:
                return True

    def _update(self):
        id = None
        with self._lock:
            if len(self._resourceList) == 0:
                return True
            idx = random.randint(0,len(self._resourceList) - 1)
            id = self._resourceList[idx]
            # Do the deletion here in order to ensure that another thread will NOT
            # delete it
            del self._resourceList[idx]

        # Do the updating on the remote machine here
        d = self._resourceGen.generateUpdate(id,self._serverAddr)

        with self._globalLock:
            req = urllib2.Request("http://%s/ec2/%s" % (self._serverAddr,self._resourceGen.updateAPI()),
                data=d, headers={'Content-Type': 'application/json'})
            try:
                response = urllib2.urlopen(req)
            except urllib2.URLError,e:
                return False
            if response.getcode() != 200:
                response.close()
                return False
            else:
                return True

        # Insert that resource _BACK_ to the list
        with self._lock:
            self._resourceList.append(id)

    def _takePlace(self,prob):
        if random.random() <= prob:
            return True
        else:
            return False

    def runOnce(self):
        if self._takePlace(self._creationProb):
            return (self._create(),"Create")
        elif self._takePlace(self._updateProb):
            return (self._update(),"Update")
        else:
            return (self._remove(),"Remove")

class CameraPerfResourceGen(SingleResourcePerfGenerator):
    _gen = CameraDataGenerator()

    def generateUpdate(self,id,parentId):
        return self._gen.generateUpdateData(id,parentId)[0]

    def generateCreation(self,parentId):
        return self._gen.generateCameraData(1,parentId)[0]

    def saveAPI(self):
        return "saveCameras"

    def updateAPI(self):
        return "saveCameras"

    def getAPI(self):
        return "getCameras"

    def resourceName(self):
        return "Camera"

class UserPerfResourceGen(SingleResourcePerfGenerator):
    _gen = UserDataGenerator()

    def generateUpdate(self,id,parentId):
        return self._gen.generateUpdateData(id)[0]

    def generateCreation(self,parentId):
        return self._gen.generateUserData(1)[0]

    def saveAPI(self):
        return "saveUser"

    def getAPI(self):
        return "getUsers"

    def resourceName(self):
        return "User"

class PerfStatistic:
    createOK = 0
    createFail=0
    updateOK =0
    updateFail=0
    removeOK = 0
    removeFail=0

class PerfTest:
    _globalLock = threading.Lock()
    _statics = dict()
    _perfList = []
    _exit = False
    _threadPool = []

    def _onInterrupt(self,a,b):
        self._exit = True

    def _initPerfList(self,type):
        for s in clusterTest.clusterTestServerList:
            if type[0] :
                self._perfList.append((s,SingleResourcePerfTest(self._globalLock,UserPerfResourceGen(),s)))

            if type[1]:
                self._perfList.append((s,SingleResourcePerfTest(self._globalLock,CameraPerfResourceGen(),s)))

            self._statics[s] = PerfStatistic()

    def _threadMain(self):
        while not self._exit:
            for entry in self._perfList:
                serverAddr = entry[0]
                object = entry[1]
                ret,type = object.runOnce()
                if type == "Create":
                    if ret:
                        self._statics[serverAddr].createOK = self._statics[serverAddr].createOK + 1
                    else:
                        self._statics[serverAddr].createFail= self._statics[serverAddr].createFail + 1
                elif type == "Update":
                    if ret:
                        self._statics[serverAddr].updateOK = self._statics[serverAddr].updateOK + 1
                    else:
                        self._statics[serverAddr].updateFail = self._statics[serverAddr].updateFail + 1
                else:
                    if ret:
                        self._statics[serverAddr].removeOK = self._statics[serverAddr].removeOK + 1
                    else:
                        self._statics[serverAddr].removeFail = self._statics[serverAddr].removeFail + 1

    def _initThreadPool(self,threadNumber):
        for _ in xrange(threadNumber):
            th = threading.Thread(target=self._threadMain)
            th.start()
            self._threadPool.append(th)

    def _joinThreadPool(self):
        for th in self._threadPool:
            th.join()

    def _parseParameters(self,par):
        sl = par.split(',')
        ret = [False,False,False]
        for entry in sl:
            if entry == 'Camera':
                ret[1] = True
            elif entry == 'User':
                ret[0] = True
            elif entry == 'MediaServer':
                ret[2] = True
            else:
                continue
        return ret

    def run(self, par):
        ret = self._parseParameters(par)
        if not ret[0] and not ret[1] and not ret[2]:
            return False
        # initialize the performance test list object
        print "Start to prepare performance data"
        print "Please wait patiently"
        self._initPerfList(ret)
        # start the thread pool to run the performance test
        print "======================================"
        print "Performance Test Start"
        print "Hit CTRL+C to interrupt it"
        self._initThreadPool(clusterTest.threadNumber)
        # Waiting for the user to stop us
        signal.signal(signal.SIGINT,self._onInterrupt)
        while not self._exit:
            try:
                time.sleep(0)
            except:
                break
        # Join the thread now
        self._joinThreadPool()
        # Print statistics now
        print "==================================="
        print "Performance Test Done"
        for key,value in self._statics.iteritems():
            print "---------------------------------"
            print "Server:%s" % (key)
            print "Resource Create Success: %d" % (value.createOK)
            print "Resource Create Fail:    %d" % (value.createFail)
            print "Resource Update Success: %d" % (value.updateOK)
            print "Resource Update Fail:    %d" % (value.updateFail)
            print "Resource Remove Success: %d" % (value.removeOK)
            print "Resource Remove Fail:    %d" % (value.removeFail)
            print "---------------------------------"
        print "===================================="


def runPerfTest(argv):
    l = argv[2].split('=')
    PerfTest().run(l[1])
    doCleanUp()


def doCleanUp():
    selection = '' if clusterTest.auto_rollback else 'x'
    if not clusterTest.auto_rollback:
        try :
            selection = raw_input("Press Enter to continue ROLLBACK or press x to SKIP it...")
        except:
            pass

    if len(selection) == 0 or selection[0] != 'x':
        print "Now do the rollback, do not close the program!"
        clusterTest.unittestRollback.doRollback(quiet=clusterTest.auto_rollback)
        print "++++++++++++++++++ROLLBACK DONE+++++++++++++++++++++++"
    else:
        print "Skip ROLLBACK,you could use --recover to perform manually rollback"


def print_tests(suit, shift='    '):
    for test in suit:
        if isinstance(test, unittest.TestSuite):
            print "DEBUG:%s[%s]:" % (shift, type(test))
            print_tests(test, shift+'    ')
        else:
            print "DEBUG:%s%s" % (shift, test)


def CallTest(testClass):
    ###if not clusterTest.openerReady:
    ###    clusterTest.setUpPassword()
    # this print is used by FunctestParser.parse_timesync_start
    print "%s suits: %s" % (testClass.__name__, ', '.join(testClass.iter_suits()))
    return RunBoxTests(testClass, clusterTest.getConfig())


# These are the old legasy tests, just organized a bit
SimpleTestKeys = {
    '--sys-name': SystemNameTest,
    '--rtsp-test': RtspTestSuit,
    '--rtsp-perf': RtspPerf,
}

# Tests to be run on the vargant boxes, separately or within the autotest sequence
BoxTestKeys = {
    '--timesync': TimeSyncTest,
    '--bstorage': BackupStorageTest,
    '--msarch': MultiserverArchiveTest,
    '--natcon': NatConnectionTest,
    '--stream': StreamingTest
}


def DoTests(argv):
    print "The automatic test starts, please wait for checking cluster status, test connection and APIs and do proper rollback..."
    # initialize cluster test environment

    argc = len(argv)
    ret, reason = clusterTest.init()
    if ret == False:
        print "Failed to initialize the cluster test object: %s" % (reason)
        return

    if argc == 2:
        if argv[1] in BoxTestKeys:
            CallTest(BoxTestKeys[argv[1]])
            return
        if argv[1] in SimpleTestKeys:
            SimpleTestKeys[argv[1]](clusterTest).run()
            return

    ret, reason = clusterTest.initial_tests()
    if ret == False:
        print "The initial cluster test failed: %s" % (reason)
        return

    if argc == 2 and argv[1] == '--sync':
        return # done here, since we just need to test whether
               # all the servers are on the same page

    if argc == 1:
        the_test = unittest.main(exit=False, argv=argv[:1])

        if the_test.result.wasSuccessful():
            print "Main tests passed OK"
            if MergeTest().run():
                SystemNameTest(clusterTest).run()
        if not clusterTest.do_main_only:
            if not clusterTest.skip_timesync:
                CallTest(TimeSyncTest)
            if not clusterTest.skip_backup:
                CallTest(BackupStorageTest)
            if not clusterTest.skip_mservarc:
                CallTest(MultiserverArchiveTest)
            if not clusterTest.skip_streming:
                CallTest(StreamingTest)

        print "\nALL AUTOMATIC TEST ARE DONE\n"
        doCleanUp()
        print "\nFunctest finnished\n"

    elif (argc == 2 or argc == 3) and argv[1] == '--clear':
        if argc == 3:
            if argv[2] == '--fake':
                doClearAll(True)
            else:
                print "Unknown option: %s in --clear" % (argv[2])
        else:
            doClearAll(False)
        clusterTest.unittestRollback.removeRollbackDB()
    elif argc == 2 and argv[1] == '--perf':
        PerfTest().start()
        doCleanUp()
    else:
        if argv[1] == '--merge-test':
            MergeTest(True).run()
        elif argv[1] == '--merge-admin':
            MergeTest_AdminPassword().test()
            clusterTest.unittestRollback.removeRollbackDB()
        elif argc == 3 and argv[1] == '--perf':
            runPerfTest()
        else:
            runMiscFunction(argc, argv)


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf8')
    argv = clusterTest.preparseArgs(sys.argv)
    if len(argv) >= 2 and argv[1] in ('--help', '-h'):
        showHelp(argv)
    elif len(argv) == 2 and argv[1] == '--recover':
        UnitTestRollback().doRecover()
    else:
        DoTests(argv)
