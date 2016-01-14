__author__ = 'Danil Lavrentyuk'
"""
Crash Inspector regulary analizes crash reports, finds crashed function names,
manages a know crashes list and creates tickets for new crashes.
"""
import time
import signal

CHECK_PERIOD = 60 # seconds
PID_FILE = '/tmp/crashmonitor.pid'

class las

class CrashMonitor(object):
    """
    Recurrent crash server checker. New crashes loader.
    """
    def __init__(self):
        self.check_pid_file()
        # Setup the interruption handler
        signal.signal(signal.SIGINT,self._onInterrupt)


    def check_pid_file(self):

        import atexit
        atexit.register ()

    def _onInterrupt(self, _signum, _stack):
        self._stop = True

    def updateCrashes(self):

    def run(self):
        while not self._stop:
            self.updateCrashes()
            time.sleep(CHECK_PERIOD)



if __name__ == '__main__':
    CrashMonitor().run()
