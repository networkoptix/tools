# $Id: MTValue.py 71579 2011-02-22 13:46:57Z artem_nikitin $
# Artem V. Nikitin
# multi-thread-safe value and flag

from Condition import Condition
from threading import Lock


class MTValue:

  def __init__( self, val = None, mutex = None ):
    self._mutex = mutex or Lock()
    self._val = val

  def set( self, val = None ):
    self._mutex.acquire()
    self._val = val
    self._mutex.release()

  def get( self ):
    self._mutex.acquire()
    try:
      return self._val
    finally:
      self._mutex.release()


class MTFlag(MTValue):

  def __init__( self, val = False, pred = bool ):
    MTValue.__init__(self, val)
    self._cond = Condition(self._mutex)
    self._pred = pred

  def set( self, val = True ):
    self._mutex.acquire()
    self._val = val
    if self._pred(val):
      self._cond.notifyAll()
    self._mutex.release()

  # timeout in in sec, float
  def wait( self, timeOut = None ):
    self._mutex.acquire()
    try:
      while not self._pred(self._val):
        if not self._cond.wait(timeOut): return None  # timed out
      return self._val  # it can be not boolean
    finally:
      self._mutex.release()


class MTCounter(MTValue):

  def __init__( self, val = 0 ):
    MTValue.__init__(self, 0)
    self._cond = Condition(self._mutex)
    self._val = 0

  def next( self ):
    self._mutex.acquire()
    try:
      self._val += 1
      self._cond.notifyAll()
      return self._val
    finally:
      self._mutex.release()

  def incr( self ):
    self._mutex.acquire()
    try:
      self._val += 1
      self._cond.notifyAll()
    finally:
      self._mutex.release()

  # timeout in in sec, float
  def wait( self, count, timeOut = None ):
    self._mutex.acquire()
    try:
      while self._val < count:
        if not self._cond.wait(timeOut): return None  # timed out
      return True
    finally:
      self._mutex.release()
