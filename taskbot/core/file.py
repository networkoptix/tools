#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Taskbot script for collect files
# Insert files to 'file' DB table.

import os, sys
import fnmatch
from optparse import OptionParser

pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../pycommons')
sys.path.insert(0, pycommons)
from MySQLDB import MySQLDB, get_db_hostname
from Utils import *

def get_file_list(options):
  files_list = {}
  def match(path, masks, default):
    if not masks:
      return default
    for m in masks:
      if fnmatch.fnmatch(path, m):
        return True
    return False
  for root, dirs, files in os.walk(options.path):
    for file in files:
      if match(file, options.mask, True) and \
         not match(file, options.exclude, False) :
        full_path = os.path.join(root, file)
        size = os.stat(full_path).st_size
        if options.empty or size:
          files_list[full_path] = size
  return files_list

def main():
  usage = "usage: %prog [options] CONFIG"
  parser = OptionParser(usage)
  parser.add_option("-t", "--task", type="int", default=0,
                    help="Is the task ID to link the file to." \
                    "If not defined, uses root task id "\
                    "of current taskbot run.")

  parser.add_option("--path",
                    help="Path where to find source files.")

  parser.add_option("--mask", action = "append", default=[],
                    help="Regex mask for saving files. " \
                    "Script will save files that match " \
                    "MASK regular expression only")

  parser.add_option("--exclude", action = "append", default=[],
                    help="Regex mask for excluding files. " \
                    "Script will not save files that match MASK.")

  parser.add_option("--empty", 
                    help="By default script doesn't save empty files. " \
                    "This option allows to save empty files that metches MASK")

  parser.add_option("--trace", default=False, action="store_true",
                    help="Trace execution.  Print every command, " \
                    "its stdout and stderr, and its " \
                    "exit status.  Default is notrace.")

  (options, args) = parser.parse_args()

  if not options.path:
    parser.print_help()
    parser.error('Source path is required')

  if len(args) == 0:
    parser.print_help()
    parser.error('CONFIG is required')

  config = read_config(args[0])
  db_config = config.get('db_config', None)
  db = MySQLDB(db_config)
  db_hostname = get_db_hostname(db_config)

  (max_allowed_packet,) = db.query("SELECT @@global.max_allowed_packet", ());

  task_id = options.task

  if not task_id and os.environ.get('TASKBOT_PARENT_PID'):
    res = db.query("""SELECT MAX(task_id)
      FROM running_task
      WHERE host = %s AND pid = %s""",
    (get_host_name(), os.environ['TASKBOT_PARENT_PID']))
    if res:
      task_id = res[0]

  if not task_id:
    print >> sys.stderr, "%s task_id is not detected" % sys.argv[0]
    sys.exit(1)

  for file, size in  get_file_list(options).items():
    if size >= max_allowed_packet:
      print >> sys.stderr, "%s can't store '%s', because its size %d > %d (max_allowed_packet)" % \
            (sys.argv[0], file, size, max_allowed_packet)
      continue
    with open(file) as fp:
      db.execute("""INSERT INTO file (task_id, name, fullpath, content)
      VALUES (%s, %s, %s, %s)""", (
        task_id, os.path.basename(file),
        file,
        fp.read()))
      
  db.commit()

if __name__ == "__main__":
  main()


