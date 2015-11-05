"""Contains common tools to handle virtual boxes based mediaserver functional testing.
"""
__author__ = 'Danil Lavrentyuk'
import subprocess
import unittest

from functest_util import ClusterLongWorker

__all__ = ['boxssh', 'FuncTestCase', 'FuncTestError']

class FuncTestError(AssertionError):
    pass


def boxssh(box, command):
    return subprocess.check_output(
        ['./vssh.sh', box, 'sudo'] + list(command),
        shell=False, stderr=subprocess.STDOUT
    )


class FuncTestCase(unittest.TestCase):
    """A base class for mediaserver functional tests using virtual boxes
    """
    config = None
    num_serv = None
    _configured = False
    _stopped = set()
    _worker = None

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

    def setUp(self):
        "Just prints \n after unittest module prints a test name"
        print
    #    print "*** Setting up: %s" % self._testMethodName  # may be used for debug ;)
    ####################################################
