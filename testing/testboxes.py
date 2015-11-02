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


class FuncTestCase(unittest.TestCase): # a base class for mediaserver functional tests
    config = None
    num_serv = None
    _configured = False

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


