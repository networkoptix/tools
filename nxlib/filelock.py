# -*- coding: utf-8 -*-
"File based interprocess Lock class."

import time
import os

# needs win32all to work on Windows
if os.name == 'nt':
    import win32con, win32file, pywintypes
    LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
    LOCK_SH = 0 # the default
    LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY
    _overlapped = pywintypes.OVERLAPPED()

    def _lock(lockfile, flags):
        hfile = win32file._get_osfhandle(lockfile.fileno())
        win32file.LockFileEx(hfile, flags, 0, 0xffff0000, _overlapped)

    def _unlock(lockfile):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.UnlockFileEx(hfile, 0, 0xffff0000, _overlapped)
elif os.name == 'posix':
    from fcntl import LOCK_EX, LOCK_SH, LOCK_NB, LOCK_UN, flock

    def _lock(lockfile, flags):
        flock(lockfile, flags)

    def _unlock(lockfile):
        flock(lockfile, LOCK_UN)
else:
    raise RuntimeError("PortaLocker only defined for nt and posix platforms")


class Lock(object):
    def __init__(self, filename):
        self.filename = filename
        # This will create it if it does not exist already
        self.handle = open(filename, 'w')
    
    def acquire(self, timeout=None, sleep_quantum=0.1):
        """Nonblocking lock acquire method.
            timeout = None  - wait endlessly
            timeout = 0     - check and return immediately
            timeout > 0     - wait no more then timeout seconds
           If timeout is not None, sleep_quantum is a sleeping period
           between checks.
        """
        if timeout is None:
            try:
               _lock(self.handle, LOCK_EX)
            except Exception:
               return False
            return True

        end = 0 if timeout == 0 else time.time() + timeout
        while True:
            try:
                _lock(self.handle, LOCK_EX|LOCK_NB)
                return True
            except IOError:
                pass
            if end < time.time():
                return False
            time.sleep(sleep_quantum)
        
    def release(self):
        _unlock(self.handle)
        
    def __del__(self):
        self.handle.close()

if __name__ == '__main__':

    lock = Lock("./lock.tmp")

    if lock.acquire(timeout=5):
        end = time.time() + 20
        print "Sleep..."
        while True:
            time.sleep(1)
            n = end - time.time()
            if n <= 0:
                break
            print "%.1f" % n
        #flock(lock_file , LOCK_UN)
        #lock_file.close()
        lock.release()
    else:
        print "Already locked!"
