# -*- coding: utf-8 -*-
""" The PipeReader class to read Popen's pipe asynchroniously.
POSIX and Win32 implementations are provided.
"""
__author__ = 'Danil Lavrentyuk'
import os
import time

#__all__ = ['PIPE_NONE', 'PIPE_READY', 'PIPE_EOF', 'PIPE_HANG', 'PIPE_ERROR', 'PipeReader']

PIPE_NONE = 0
PIPE_READY = 1
PIPE_EOF = 2
PIPE_HANG = 3
PIPE_ERROR = 4

class PipeReaderBase(object):
    def __init__(self):
        self.fd = None
        self.proc = None
        self.buf = ''
        self.state = PIPE_NONE

    def register(self, proc):
        if self.fd is not None and self.fd != self.fd:
            raise RuntimeError("PipeReader: double fd register")
        self.proc = proc
        self.buf = ''
        self.fd = proc.stdout
        self.state = PIPE_READY # new fd -- new process, so the reader is ready again

    def unregister(self):
        if self.fd is None:
            raise RuntimeError("PipeReader.unregister: fd was not registered")
        self._unregister()
        self.fd = None
        self.proc = None

    def _unregister(self):
        raise NotImplementedError()

    def read_ch(self, timeout=0):
        # ONLY two possible results:
        # 1) return the next character
        # 2) return '' and change self.state
        raise NotImplementedError()

    def readline(self, timeout=0):
        if self.state != PIPE_READY:
            return None
#        while self.proc.poll() is None:
        while True:
            ch = self.read_ch(timeout)
            if ch is None or ch == '':
                if self.proc.poll() is not None:
                    break
                return self.buf
            if ch == '\n' or ch == '\r': # use all three: \n, \r\n, \r
                if len(self.buf) > 0:
                    #debug('::'+self.buf)
                    try:
                        return self.buf
                    finally:
                        self.buf = ''
                else:
                    pass # all empty lines are skipped (so \r\n doesn't produce fake empty line)
            else:
                self.buf += ch
        self.state = PIPE_EOF
        return self.buf


if os.name == 'posix':
    import select
    READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
    READY = select.POLLIN | select.POLLPRI

    class PipeReader(PipeReaderBase):
        def __init__(self):
            super(PipeReader, self).__init__()
            self.poller = select.poll()

        def register(self, proc):
            super(PipeReader, self).register(proc)
            self.poller.register(self.fd, READ_ONLY)

        def _unregister(self):
            self.poller.unregister(self.fd)

        def read_ch(self, timeout=0):
            res = self.poller.poll(timeout)
            if res:
                if res[0][1] & READY:
                    return self.fd.read(1)
                # EOF
                self.state = PIPE_EOF
            else:
                self.state = PIPE_HANG
            return ''

else:
    import msvcrt
    import pywintypes
    import win32pipe

    class PipeReader(PipeReaderBase):

        def register(self, proc):
            super(PipeReader, self).register(proc)
            self.osf = msvcrt.get_osfhandle(self.fd)

        def read_ch(self, timeout=0):
            endtime = (time.time() + timeout) if timeout > 0 else 0
            while self.proc.poll() is None:
                try:
                    _, avail, _ = win32pipe.PeekNamedPipe(self.osf, 1)
                except pywintypes.error:
                    self.state = PIPE_ERROR
                    return ''
                if avail:
                    return os.read(self.fd, 1)
                if endtime:
                    t = time.time()
                    if endtime > t:
                        time.sleep(min(0.01, endtime - t))
                    else:
                        self.state = PIPE_HANG
                        return ''


    def check_poll_res(res):
        return bool(res)
