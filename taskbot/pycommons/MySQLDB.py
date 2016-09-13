# $Id$
# Artem V. Nikitin
# MySQL taskbot backend

import mysql.connector as db
import os

MY_CNF_FILE=os.environ['HOME'] + '/.my.cnf'
MY_CNF_GROUP='mysql'

class MySQLDB:

  START_TASK = \
    """INSERT INTO task (root_task_id, parent_task_id, branch_id, 
    description, is_command, start, finish)
    VALUES (%s, %s, %s, %s, %s, %s, 0)"""

  FINISH_TASK = \
    """UPDATE task SET finish = %s, error_message = %s
    WHERE id = %s"""
  
  FINISH_COMMAND = \
    """INSERT INTO command (task_id, stdout_gzipped, stdout,
    stderr_gzipped, stderr, exit_status)
    VALUES (%s, %s, %s, %s, %s, %s)"""

  CREATE_RUNNING_TASK = \
    """INSERT INTO running_task (task_id, host, pid, user)
    VALUES (%s, %s, %s, %s)"""

  DELETE_RUNNING_TASK = \
    """DELETE FROM running_task
    WHERE task_id = %s"""

  SELECT_PARENT_TASK = \
    """SELECT MAX(task_id) FROM running_task
    WHERE host = %s AND pid = %s"""
  
  SELECT_ROOT_TASK = \
    """SELECT root_task_id FROM task
    WHERE id = %s"""

  SELECT_BRANCH = \
    """SELECT id FROM branch
    WHERE description = %s"""


  def __init__(self, config):
    if config:
      self.__conn__ = db.connect(config)
    else:
      self.__conn__ = db.connect(
        option_files=MY_CNF_FILE,
        option_groups=MY_CNF_GROUP)
    self.__cursor__ = self.__conn__.cursor()
    
  def execute(self, query, values):
    self.__cursor__.execute(query, values)
    return self.__cursor__.lastrowid

  def query(self, query, values):
    self.__cursor__.execute(query, values)
    return self.__cursor__.fetchone()

  def ping(self):
    self.__conn__.ping()

  def commit(self):
    self.__conn__.commit()

  def close(self):
    self.__cursor__.close()
    self.__conn__.close()


    

  
    
