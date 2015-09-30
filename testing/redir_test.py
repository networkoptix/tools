__author__ = 'Danil Lavrentyuk'
"""Test inter-server redirects."""

import urllib2
import json
import time
from functest_util import JsonDiff, compareJson

MAIN_HOST = 'http://192.168.109.12:7001'
SEC_HOST = 'http://192.168.109.13:7001'
IDS = {}

CHECK_URI = ''

USER = 'admin'
PWD = '123'


def prepare_loader():
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    for h in (MAIN_HOST, SEC_HOST):
        passman.add_password(None, "%s/ec2" % h, USER, PWD)
        passman.add_password(None, "%s/api" % h, USER, PWD)
    urllib2.install_opener(urllib2.build_opener(urllib2.HTTPDigestAuthHandler(passman)))


def safe_request_json(req):
    try:
        return json.loads(urllib2.urlopen(req).read())
    except Exception, e:
        if isinstance(req, urllib2.Request):
            req = req.get_full_uri()
        print "FAIL: error requesting '%s': %s" % (req, e)
        return None


def unquote_guid(guid):
    return guid[1:-1] if guid[0] == '{' and guid[-1] == '}' else guid


def get_server_guid(host):
    #req = urllib2.Request("%s/api/moduleInformation" % host)
    info = safe_request_json("%s/api/moduleInformation" % host)
    if info and (u'id' in info['reply']):
        IDS[host] = unquote_guid(info['reply']['id'])
        print "%s - %s" % (host, IDS[host])


def perform_request(peer, redirect_to=None):
    if redirect_to:
        print "Requesting %s with redirect to %s" % (peer, redirect_to)
    else:
        print "Requesting %s" % (peer,)
    req = urllib2.Request('%s/ec2/getResourceParams' % peer)
    if redirect_to:
        req.add_header('X-server-guid', IDS[redirect_to])
    response = urllib2.urlopen(req)
    data = response.read()
    content_len = int(response.info()['Content-Length'])
    if content_len != len(data):
        print "FAIL: Resulting data len: %s. Content-Length: %s" % (len(data), content_len)
    return (json.loads(data), content_len)
    #print "Resulting data len: %s" % len(data)

if __name__ == '__main__':
    prepare_loader()
    for h in (MAIN_HOST, SEC_HOST):
        get_server_guid(h)
    time.sleep(1)
    (data1, len1) = perform_request(MAIN_HOST)
    time.sleep(1)
    (data2, len2) = perform_request(MAIN_HOST, SEC_HOST)
    diff = compareJson(data1, data2)
    if len1 != len2:
        print "FAIL: Different data lengths: %s and %s" % (len1, len2)
    elif diff.hasDiff():
        print "FAIL: Diferent responses: %s" % diff.errorInfo()
    else:
        print "Test complete. Responses are the same."



