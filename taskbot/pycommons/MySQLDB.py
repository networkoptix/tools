# $Id$
# Artem V. Nikitin
# MySQL taskbot backend

from Shutdown import shutdown
import mysql.connector as db
import os, re

MY_CNF_FILE=os.environ['HOME'] + '/.my.cnf'
MY_CNF_GROUP='mysql'

def get_db_hostname(config = None):
  if config:
    return config['host']
  else:
    with open(MY_CNF_FILE) as fcfg:
      for line in fcfg:
        m = re.search(r'^host=(.+)', line)
        if m:
          return m.group(1)
      fcfg.close()
  return 'localhost'
 
class MySQLDB:

  def __init__(self, config):
    self.__config = config
    self.__reconnect()

  def __reconnect(self):
    self.__disconnect()
    if self.__config:
      self.__conn = db.connect(**self.__config)
    else:
      self.__conn = db.connect(
        option_files=MY_CNF_FILE,
        option_groups=MY_CNF_GROUP)
      self.__cursor = self.__conn.cursor()

  def __disconnect(self):
    self.__cursor = None
    self.__conn = None

  @property
  def connected(self):
    return self.__conn and self.__cursor

  @property
  def cursor( self ):
    return self.__cursor
    
  def execute(self, query, values):
    self.__cursor.execute(query, values)
    return self.__cursor.lastrowid

  def safe_execute(self, query, values):
    try:
      return True, self.execute(query, values)
    except db.errors.DatabaseError:
      return False, None

  def query(self, query, values):
    self.__cursor.execute(query, values)
    return self.__cursor.fetchone()

  def ensure_connect(self):
    try:
      self.__conn.ping()
    except db.errors.Error:
      self.__reconnect()

  def commit(self):
    self.__conn.commit()

  def close(self):
    self.__cursor.close()
    self.__conn.close()
