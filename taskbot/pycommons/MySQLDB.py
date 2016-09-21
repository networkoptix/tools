# $Id$
# Artem V. Nikitin
# MySQL taskbot backend

import mysql.connector as db
import os

MY_CNF_FILE=os.environ['HOME'] + '/.my.cnf'
MY_CNF_GROUP='mysql'

class MySQLDB:

  def __init__(self, config):
    self.__config__ = config
    self.__reconnect()

  def __reconnect(self):
    if self.__config__:
      self.__conn__ = db.connect(self.__config__)
    else:
      self.__conn__ = db.connect(
        option_files=MY_CNF_FILE,
        option_groups=MY_CNF_GROUP)
    self.__cursor__ = self.__conn__.cursor()

  @property
  def cursor( self ):
    return self.__cursor__
    
  def execute(self, query, values):
    self.__cursor__.execute(query, values)
    return self.__cursor__.lastrowid

  def safe_execute(self, query, values):
    try:
      return True, self.execute(query, values)
    except db.errors.DatabaseError:
      return False, None

  def query(self, query, values):
    self.__cursor__.execute(query, values)
    return self.__cursor__.fetchone()

  def ensure_connect(self):
    try:
      self.__conn__.ping()
    except db.errors.Error:
      self.__reconnect()

  def commit(self):
    self.__conn__.commit()

  def close(self):
    self.__cursor__.close()
    self.__conn__.close()

    


    

  
    
