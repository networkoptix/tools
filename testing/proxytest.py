# -*- coding: utf-8 -*-
__author__ = 'Danil Lavrentyuk'
"""Test inter-server redirects."""

import sys
import urllib2
from httplib import HTTPException
import json
import time
from functest_util import JsonDiff, compareJson, get_server_guid
import traceback

_MAIN_HOST = '192.168.109.8:7001'
_SEC_HOST = '192.168.109.9:7001'
#FIXME USE CONFIG!!!!

#CHECK_URI = ''

_USER = 'admin'
_PWD = 'admin'


def _prepareLoader(hosts):
    try:
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        for h in (hosts):
            passman.add_password(None, "http://%s/ec2" % h, _USER, _PWD)
            passman.add_password(None, "http://%s/api" % h, _USER, _PWD)
        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPDigestAuthHandler(passman)))
    except Exception:
        print "FAIL: can't install a password manager: %s" % (traceback.format_exc(),)
        return False
    return True

def _performRequest(peer, redirectToID=None):
    if redirectToID:
        print "Requesting %s with redirect to %s" % (peer, redirectToID)
    else:
        print "Requesting %s" % (peer,)
    req = urllib2.Request('http://%s/ec2/getResourceParams' % peer)
    if redirectToID:
        req.add_header('X-server-guid', redirectToID)
    response = urllib2.urlopen(req)
    data = response.read()
    content_len = int(response.info()['Content-Length'])
    if content_len != len(data):
        print "FAIL: Resulting data len: %s. Content-Length: %s" % (len(data), content_len)
    return (json.loads(data), content_len)
    #print "Resulting data len: %s" % len(data)


def ProxyTest(mainHost, secHost):
    ids = {}
    print "\n======================================="
    print "Proxy Test Start"
    try:
        for h in (mainHost, secHost):
            guid = get_server_guid(h)
            if guid is not None:
                ids[h] = guid
                print "%s - %s" % (h, guid)
            else:
                print "FAIL: Can't get server %s guid!" % h
                return False
        time.sleep(1)
        try:
            (data1, len1) = _performRequest(mainHost)
        except HTTPException:
            print "FAIL: error requesting %s: %s" % (mainHost, traceback.format_exc())
            return False
        time.sleep(1)
        try:
            (data2, len2) = _performRequest(mainHost, ids[secHost])
        except HTTPException:
            print "FAIL: error requesting %s through %s: %s" % (secHost, mainHost, traceback.format_exc())
            return False
        diff = compareJson(data1, data2)
        if len1 != len2:
            print "FAIL: Different data lengths: %s and %s" % (len1, len2)
        elif diff.hasDiff():
            print "FAIL: Diferent responses: %s" % diff.errorInfo()
        else:
            print "Test complete. Responses are the same."
            return True
    except Exception:
        print "FAIL: %s: %s:\n%s" % sys.exc_info()
    finally:
        print "======================================="
    return False


if __name__ == '__main__':
    try:
        _MAIN_HOST = sys.argv[1]
        _SEC_HOST = sys.argv[2]
    except IndexError:
        pass
    if not _prepareLoader((_MAIN_HOST, _SEC_HOST)):
        exit(1)
    if not ProxyTest(_MAIN_HOST, _SEC_HOST):
        exit(1)


