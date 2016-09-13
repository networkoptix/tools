# $Id: Shutdown.py 28969 2009-04-10 10:09:40Z artem_nikitin $
# Artem V. Nikitin
# global shutdown flag with condition registering/signalling

from threading import *


class ShuttingDown(Exception): pass


class Shutdown:

  def __init__( self ):
    self.flag = False
    self.cond = Condition()
    self.conds = []

  def _raise( self ):
    raise ShuttingDown('Server is shutting down')

  def check( self ):
    if self.get(): self._raise()

  def get( self ):
    self.cond.acquire()
    try:
      return self.flag
    finally:
      self.cond.release()

  def set( self ):
    self.cond.acquire()
    try:
      self.flag = True
      self.cond.notifyAll()
      conds = self.conds[:]  # get copy to avoid race conditions
    finally:
      self.cond.release()
    for cond in conds:
      cond.acquire()  # must be acquired for notify
      cond.notifyAll()
      cond.release()

  def clear( self ):
    self.cond.acquire()
    try:
      self.flag = False
    finally:
      self.cond.release()

  def wait( self ):
    self.cond.acquire()
    try:
      while not self.flag:
        self.cond.wait(1)  # 1 sec cycle to allow signal processing
    finally:
      self.cond.release()

  # registering then unregistering one condition multiple times is ok
  # cond must be threading.Condition
  def regCondition( self, cond ):
    self.cond.acquire()
    try:
      self.conds.append(cond)
    finally:
      self.cond.release()

  def unregCondition( self, cond ):
    self.cond.acquire()
    try:
      self.conds.remove(cond)
    finally:
      self.cond.release()

  def sigHandler( self, sigNum, frame ):
    if not self.flag: self.set()


# time.sleep replacer - to react to shutdown
class Sleeper:

  def __init__( self ):
    self.cond = Condition()

  def sleep( self, time ):
    if time == 0: return
    shutdown.regCondition(self.cond)
    try:
      shutdown.check()
      self.cond.acquire()  # must be locked for wait
      self.cond.wait(time)
      self.cond.release()
      shutdown.check()
    finally:
      shutdown.unregCondition(self.cond)

    
# global shutdown flag
shutdown = Shutdown()
sleeper = Sleeper()
sleep = sleeper.sleep
