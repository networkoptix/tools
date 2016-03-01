# -*- coding: utf-8 -*-
"""
Connection behind NAT test
"""
__author__ = 'Danil Lavrentyuk'

import os, os.path, sys, time
import subprocess
import unittest

import urllib2 # FIXME remove it

from functest_util import checkResultsEqual
from testboxes import *

NUM_NAT_SERV = 2  # 2 mediaservers are used: 1st before NAT, 2rd - behind NAT
                  # there is no mediaserver on the box with NAT

class NatConnectionTestError(FuncTestError):
    pass

class NatConnectionTest(FuncTestCase):

    _test_name = "NAT Connection"
    _suits = (
        ('NatConnectionTests', [
            'VMPreparation',
            'TestDataSynchronization',
            'TestRTSP',
            'TestHTTPForwarding',
         ]),
    )
    num_serv_t = NUM_NAT_SERV # the 1st server should be "before" NAT, the 2nd - behind NAT


    #def _get_init_script(self, boxnum):
    #    return '/vagrant/nc_init.sh',

    ################################################################

    def VMPreparation(self):
        "Join servers into one system"
        url = """
        http://192.168.110.3:7001/api/mergeSystems?url=http://192.168.109.8:7001&password=123&currentPassword=123&takeRemoteSetting=false&oneServer=false&ignoreIncompatible=false
        """
        #FIXME - this request should've be done before the initial functest's requests
        #
        # get server's IDs
        self._wait_servers_up()

    _sync_test_requests = ["getResourceParams", "getMediaServersEx", "getCamerasEx", "getUsers"]

    def TestDataSynchronization(self):
        for method in self._sync_test_requests:
            responseList = []
            for server in self.sl:
                print "Connection to http://%s/ec2/%s" % (server, method)
                responseList.append((urllib2.urlopen("http://%s/ec2/%s" % (server, method)),server))
            # checking the last response validation
            ret, reason = checkResultsEqual(responseList,method)
            self.assertTrue(ret, reason)

    #TODO implement it leter
    @unittest.skip("Not implememted")
    def TestRTSP(self):
        pass

    _func_to_forward = 'api/moduleInformation'

    def TestHTTPForwarding(self):
        "Uses request, returning different data for diаferent servers. Checks direct and proxied requests."
        direct_answer1 = self._server_request(1, self._func_to_forward)
        fwd_answer1 = self._server_request(0, self._func_to_forward, headers={'X-server-guid': self.guids[1]})
        self.assertEqual(direct_answer1, fwd_answer1, "Request inner server through outer returns different result then direct request")
        direct_answer2 = self._server_request(0, self._func_to_forward)
        fwd_answer2 = self._server_request(1, self._func_to_forward, headers={'X-server-guid': self.guids[0]})
        self.assertEqual(direct_answer2, fwd_answer2, "Request outer server through inner returns different result then direct request")
        self.assertNotEqual(direct_answer1, direct_answer2, "Both servers return the same moduleInformation data")


