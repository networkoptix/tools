#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Clear taskbot database

import mysql.connector as db
from optparse import OptionParser
import os, time, sys

MY_CNF_FILE=os.environ['HOME'] + '/.my.cnf'
MY_CNF_GROUP='mysql'

def secs2str( sec ):
  if sec == 0: return '0'
  return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(sec))

def main():

  usage = "usage: %prog [options]"
  parser = OptionParser(usage)
  
  parser.add_option("--host", 
                    help="Taskbot database host")
  parser.add_option("--user", 
                    help="Taskbot database user")
  parser.add_option("--password", 
                    help="Taskbot database user")
  parser.add_option("--days", type=int,
                    help="Days to keep taskbot history")
  parser.add_option("-v", action="count", dest="verbose",
                    help="Verbose option")

  db_options = ['host', 'user', 'password']
  (options, args) = parser.parse_args()
  db_options_count = len(filter(lambda x: getattr(options, x), db_options))

  if not options.days:
    print >> sys.stderr, "%s: --days parameter required" % sys.argv[0]
    parser.print_help()
    exit(1)
  
  if args:
    print >> sys.stderr, "%s: invalid args: %s" % (sys.argv[0], args)
    parser.print_help()
    exit(1)
  
  if db_options_count == 0:
    conn = db.connect(
      user = options.user,
      password = options.password,
      host = options.host,
      database = options.user)
  elif db_options_count == 3:
    conn = db.connect(
      option_files=MY_CNF_FILE,
      option_groups=MY_CNF_GROUP)
  else:
    print >> sys.stderr, "%s: invalid database options" % sys.argv[0]
    parser.print_help()
    exit(1)

  start_time = time.time() - options.days * 24 * 60 * 60;

  cursor = conn.cursor()

  # Verbose
  cursor.execute(""" SELECT COUNT(id), IFNULL(MIN(id), 0), IFNULL(MAX(id), 0)
    FROM task
    WHERE start < %s""", (start_time, ))
  
  (tasks_count, min_task_id, max_task_id) = cursor.fetchone()
  start_min = start_max = 0
                          
  if (min_task_id):
    cursor.execute("SELECT start FROM task WHERE  id =  %s", (min_task_id, ))

    (start_min, ) = cursor.fetchone()
     
  if max_task_id:
    cursor.execute("SELECT start FROM task WHERE  id =  %s", (max_task_id, ))
    (start_max, ) =  cursor.fetchone()

  t_min = secs2str(start_min)
  t_max = secs2str(start_max)

  # Remove data

  for i in range(min_task_id, max_task_id): 
    remove_task_sql = "DELETE FROM task where id = %d" % i
    if options.verbose > 0:
      print remove_task_sql
    if options.verbose != 1:
      cursor.execute(remove_task_sql)
  conn.commit()
  conn.close()

  if options.verbose == 2 and tasks_count:
    print "Remove %d tasks from %d (%s) to %d (%s)" % \
      (tasks_count, min_task_id, t_min, max_task_id, t_max)
    
    print "Data was successfully removed";

main()
