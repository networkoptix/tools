#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Danil Lavrentyuk'
""" Server stress test scrtipt. Trying to make large number of requests to see if
"""
import sys, os, threading
import argparse
import requests
from requests.exceptions import SSLError
import signal
import time
import traceback as TB

DEFAULT_THREADS = 10
AUTH = ('admin', '123')
URI = "/api/gettime" # "/ec2/getCurrentTime", /api/moduleInformation, /api/ping, /api/statistics,
# /ec2/getSettings, /api/moduleInformation, /api/logLevel, /api/iflist, /api/systemSettings
URI_HEAVY = "/ec2/getResourceTypes" # /ec2/getFullInfo
URI = URI_HEAVY
DEFAULT_HOST = "192.168.109.12"
DEFAULT_PORT = 7001
HOST = ""
PROTO = 'http'
REPORT_PERIOD = 1.0


class StressTest(object):
    """ Produces many requsests to the server.
    """
    server = None

    def __init__(self, num, master):
        self._id = num
        self._master = master
        self._session = requests.Session()
        self._url = "%s://%s%s" % (PROTO, HOST, URI)
        kwargs = dict(url=self._url, auth=AUTH)
        #if PROTO == 'https':
        #    kwargs['verify'] = False
        self._prep = self._session.prepare_request(requests.Request('GET', **kwargs))

    def getId(self):
        return "%s.%d" % (self.__class__.__name__, self._id)

    def _req(self):
        kwargs = {'verify': False} if PROTO == 'https' else dict()
        try:
            res = self._session.send(self._prep,  **kwargs)
            if res.status_code != 200:
                return 'Code: %s' % res.status_code
            else:
                return None # means success!
        except SSLError:
            print "Exception: %s" % (TB.format_exc(),)
            raise
        except Exception, e:
            print "Exception: %s" % (TB.format_exc(),)
            return "Exception %s" % (e.__class__.__name__,)

    def run(self):
        while not self._master.stopping():
            res = self._req()
            self._master.report(res)


class StressTestRunner(object):
    """ Hold a container of test runners and runs them in threads.
    """
    _stop = False
    _threadNum = DEFAULT_THREADS

    def __init__(self, thread_num):
        self._threads = []
        self._workers = []
        self._oks = 0 # successes
        self._fails = dict() # failures, groupped by error message
        self._threadNum = thread_num
        self._sumsLock = threading.Lock()
        signal.signal(signal.SIGINT,self._onInterrupt)
        self._createWorkers()

    def _onInterrupt(self, _signum, _stack):
        self._stop = True
        print "Finishing work..."

    def stopping(self):
        return self._stop

    def report(self, result):
        self._sumsLock.acquire()
        if result is None:
            self._oks += 1
        else:
            if result in self._fails:
                self._fails[result] += 1
            else:
                self._fails[result] = 1
        self._sumsLock.release()

    def print_totals(self):
        self._sumsLock.acquire()
        passed = time.time() - self.start
        oks = self._oks
        total = self._oks + sum(self._fails.itervalues())
        self._sumsLock.release()
        print "[%d] total %d, OKs %d (%.1f%%), request speed %.1f req/sec\n" % (
            int(round(passed)), total, oks, ((oks * 100.0)/total) if total else 0, (total/passed) if passed else 0
        ),


    def _createWorkers(self):
        self._workers = [StressTest(n, self) for n in xrange(self._threadNum)]


    def run(self):
        print "Testing with %s parallel workers. Protocol: %s" % (len(self._workers), PROTO)
        self._threads = [threading.Thread(target=w.run, name=w.getId()) for w in self._workers]
        self.start = time.time()
        for t in self._threads:
            t.start()
        while not self._stop:
            time.sleep(REPORT_PERIOD)
            self.print_totals()
        for t in self._threads:
            if t.isAlive():
                t.join()
        print "===========================\nFinal result:"
        self.print_totals()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-T', '--threads', type=int, help="Number of threads to use. Default: %s" % DEFAULT_THREADS, default=DEFAULT_THREADS)
    parser.add_argument('-H', '--host', help="Server hostname or IP. May include portnumber too.", default=DEFAULT_HOST)
    parser.add_argument('-P', '--port', type=int, help="Server port number", default=DEFAULT_PORT)
    global PROTO
    parser.add_argument('-p', '--proto', choices=('http', 'https'), help="Protocol using (http or https, %s is default)" % PROTO, default=PROTO)
    global REPORT_PERIOD
    parser.add_argument('-r', '--reports', type=float, help="Counters report preriod, seconds. Default = %.1f" % REPORT_PERIOD)
    args = parser.parse_args()
    #if args.host and args.port:
    if args.reports is not None:
        if args.reports > 0:
            REPORT_PERIOD = args.reports
        else:
            print "ERROR: Wrong report period value: %s" % args.reports
            sys.exit(1)
    host = args.host.split(':', 1)
    if len(host) > 1:
        if host[1] != str(args.port):
            print "ERROR: Hostname contains a port number %s and it's not equal to the option --port value %s" % (host[1], args.port)
            sys.exit(1)
        # else no changes to args.host required
    else:
        args.host = '%s:%s' % (host[0], args.port)
    global HOST
    HOST = args.host
    PROTO = args.proto
    return args


if __name__ == '__main__':
    args = parse_args()
    StressTestRunner(args.threads).run()
