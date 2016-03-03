# -*- coding: utf-8 -*-
__author__ = 'Danil Lavrentyuk'
"""Test inter-server redirects."""

import sys
import urllib2
from httplib import HTTPException
import json
import time
from functest_util import JsonDiff, compareJson, get_server_guid

MAIN_HOST = '192.168.109.8:7001'
SEC_HOST = '192.168.109.9:7001'
#FIXME USE CONFIG!!!!
IDS = {}

CHECK_URI = ''

USER = 'admin'
PWD = '123'


def prepare_loader():
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    for h in (MAIN_HOST, SEC_HOST):
        passman.add_password(None, "http://%s/ec2" % h, USER, PWD)
        passman.add_password(None, "http://%s/api" % h, USER, PWD)
    urllib2.install_opener(urllib2.build_opener(urllib2.HTTPDigestAuthHandler(passman)))


def perform_request(peer, redirect_to=None):
    if redirect_to:
        print "Requesting %s with redirect to %s" % (peer, redirect_to)
    else:
        print "Requesting %s" % (peer,)
    req = urllib2.Request('http://%s/ec2/getResourceParams' % peer)
    if redirect_to:
        req.add_header('X-server-guid', IDS[redirect_to])
    response = urllib2.urlopen(req)
    data = response.read()
    content_len = int(response.info()['Content-Length'])
    if content_len != len(data):
        print "FAIL: Resulting data len: %s. Content-Length: %s" % (len(data), content_len)
    return (json.loads(data), content_len)
    #print "Resulting data len: %s" % len(data)


def proxy_test():
    global MAIN_HOST, SEC_HOST
    try:
        MAIN_HOST = sys.argv[1]
        SEC_HOST = sys.argv[2]
    except IndexError:
        pass
    try:
        prepare_loader()
        for h in (MAIN_HOST, SEC_HOST):
            guid = get_server_guid(h)
            if guid is not None:
                IDS[h] = guid
                print "%s - %s" % (h, guid)
            else:
                print "FAIL: Can't get server %s guid!" % h
                return False
        time.sleep(1)
        try:
            (data1, len1) = perform_request(MAIN_HOST)
        except HTTPException, e:
            print "FAIL: error requesting %s: %s: %s" % ((MAIN_HOST,) + sys.exc_info()[0:2])
            return False
        time.sleep(1)
        try:
            (data2, len2) = perform_request(MAIN_HOST, SEC_HOST)
        except HTTPException, e:
            print "FAIL: error requesting %s through %s: %s: %s" % ((SEC_HOST, MAIN_HOST) + sys.exc_info()[0:2])
            return False
        diff = compareJson(data1, data2)
        if len1 != len2:
            print "FAIL: Different data lengths: %s and %s" % (len1, len2)
        elif diff.hasDiff():
            print "FAIL: Diferent responses: %s" % diff.errorInfo()
        else:
            print "Test complete. Responses are the same."
    except:
        print "FAIL: %s: %s:\n%s" % sys.exc_info()
        raise
    return True


if __name__ == '__main__':
    if not proxy_test():
        exit(1)


