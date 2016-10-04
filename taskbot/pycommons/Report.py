# $Id$
# Arem V. Nikitin
# Report base class

import os, zlib, urllib
from MySQLDB import MySQLDB
from Utils import *

class Report:

  class Task:
    def __init__(self,
                 task_id, parent_task_id,
                 description,
                 is_command=False, start=None,
                 finish=None, error_message=None):
      self.id = task_id
      self.parent_task_id = parent_task_id
      self.description = description
      self.is_command = is_command
      self.start = start
      self.finish = finish
      self.error_message = error_message

    def __str__(self):
      return "Task#%s: %s" % (self.id, self.description)
    
    def __repr__(self):
      return self.__str__()

  class Platform:
    def __init__(self, platform_id, host, description):
      self.id = platform_id
      self.host = host
      self.description = description

    def __str__(self):
      return "Platform#%s: %s (%s)" % \
             (self.id, self.host, self.description)
    
    def __repr__(self):
      return self.__str__()
    
      
  def __init__(self, config, root_task = None):
    self.__config__ = read_config(config) # Takbot config
    Compressor.gzip_threshold = self.__config__.get('gzip_threshold', 0)
    Compressor.gzip_ratio = self.__config__.get('gzip_ratio', 0)
    self.__db__ =  MySQLDB(self.__config__.get('db_config', None)) # Takbot database
    self.__platform__ = self.__find_platform()
    self.__branch__ = self.__find_branch()
    self.__root_task__ = root_task or self.__find_root_by_pid() or self.__find_last_root()
    self.__link_task_id__ = self.__root_task__.id

  # Raw report SQL
  def __find_platform(self):
    return Report.Platform(
      *self.__db__.query(
        """SELECT id, host, description FROM platform
        WHERE host = %s""", (get_host_name(), )))

  def __find_branch(self):
    return self.__db__.query("""SELECT id FROM branch
      WHERE description = %s""", (os.environ['TASKBOT_BRANCHNAME'], ))[0]

  def __find_last_root(self):
    res = \
        self.__db__.query("""SELECT id, parent_task_id, description,
          is_command, start, finish, error_message
          FROM task
          WHERE id = (SELECT MAX(id)
            FROM task
            WHERE platform_id = %s
            AND branch_id = %s
            AND parent_task_id IS NULL)""",
          (self.__platform__.id,  self.__branch__))
    if res:
      return Report.Task(*res)
    return None
  
  def __find_root_by_pid(self):
    if not os.environ.get('TASKBOT_PARENT_PID'):
      return None
   
    (parent_task_id, ) = \
    self.__db__.query("""SELECT MIN(task_id)
      FROM running_task
      WHERE host = %s AND pid = %s""",
    (get_host_name(), os.environ['TASKBOT_PARENT_PID']))

    while parent_task_id:
      res = \
        self.__db__.query("""SELECT id, parent_task_id, description,
          is_command, start, finish, error_message
          FROM task
          WHERE id = %s""", (parent_task_id, ))
      parent_task_id = res[1]

    return Report.Task(*res)

  def __find_task(self, parent_task_id, description):
    cursor = self.__db__.cursor
    cursor.execute(
      """SELECT id, parent_task_id, description,
      is_command, start, finish, error_message
      FROM task
      WHERE parent_task_id = %s AND description LIKE %s
      ORDER BY id""", (parent_task_id, description))
    return [ Report.Task(*task) for task in cursor ]

  def __find_task_by_root(self, root_task_id, description):
    cursor = self.__db__.cursor
    cursor.execute(
      """SELECT id, parent_task_id, description,
      is_command, start, finish, error_message
      FROM task
      WHERE root_task_id = %s AND description LIKE %s
      ORDER BY id""", (root_task_id, description))
    return [ Report.Task(*task) for task in cursor ]

  def __find_failed_task(self, parent_task_id):
    cursor = self.__db__.cursor
    cursor.execute("""SELECT id, description, is_command, start, finish, error_message
      FROM task
      WHERE parent_task_id = %s AND error_message IS NOT NULL""", (parent_task_id, ))
    return [ Report.Task(*task) for task in cursor ]

  def __insert_report(self, task_id, gzipped, html):
    return \
           self.__db__.execute("""INSERT INTO report (task_id, gzipped, html)
           VALUES (%s, %s, %s)""", (task_id, gzipped, html));

  def __get_report(self, task_id):
    return self.__db__.query("""SELECT id, gzipped, html
      FROM report
      WHERE task_id = %s""", (task_id,))

  def __insert_view(self, type, url):
    return self.__db__.execute("""INSERT INTO view (type, url)
      VALUES (%s, %s)""", (type, url))

  def __link_view(self, report_id, view_id):
    self.__db__.execute("""
        INSERT INTO report_view (report_id, view_id)
        VALUES (%s, %s)""", (report_id, view_id))


  def __insert_to_report(self, report_id, gzipped, html):
    self.__db__.execute("""UPDATE report set gzipped = %s, html = %s
      WHERE id = %s""", (gzipped, html, report_id))

  def __add_history(self, task_id, html_table_row):
     self.__db__.execute("""UPDATE history
        SET html_table_row = CONCAT(html_table_row, %s)
        WHERE task_id = %s""", (html_table_row, task_id, ))

  def __get_stdout(self, task_id):
    return self.__db__.query("""SELECT stdout_gzipped, stdout
      FROM command
      WHERE task_id = %s""", (task_id,))

  def __get_stderr(self, task_id):
    return self.__db__.query("""SELECT stderr_gzipped, stderr
      FROM command
      WHERE task_id = %s""",(task_id, ))

  def __get_status(self, task_id):
    return self.__db__.query("""SELECT exit_status
      FROM command
      WHERE task_id = %s""",(task_id, ))

  def __prev_root_task(self, task):
    prev_task = self.__db__.query("""SELECT id, parent_task_id, description,
      is_command, start, finish, error_message
      FROM task
      WHERE id = (SELECT MAX(h.task_id)
                  FROM history h
                  JOIN task t ON h.task_id = t.id
                  WHERE h.task_id < %s
                  AND t.platform_id = %s
                  AND t.branch_id = %s
                  AND t.description = %s)""",
      (task.id, self.__platform__.id, self.__branch__, task.description))
    if prev_task:
      return Report.Task(*prev_task)
    return None

  def __files_list(self, task_id, path):
    return self.__db__.query("""SELECT id, name, fullpath, task_id
      FROM file
      WHERE task_id = %s AND fullpath LIKE %s""",(task_id, path))

  def __file_path_list(self, task_id):
    return self.__db__.query("""SELECT distinct fullpath
      FROM file
      WHERE task_id = %s""", (task_id, ))

  def __file_history(self, filename, fullpath, task_id, min, max):
    return self.__db__.query("""SELECT f.id as id, 
      t.id as task_id,
      t.root_task_id as root_task_id,
      t.start as start,
      t.finish as finish
        FROM file f
        JOIN task t on t.id = f.task_id
        WHERE f.name = %s AND
              f.fullpath = %s AND
              f.task_id < %s
        ORDER BY t.id DESC
        LIMIT %s, %s""", (filename, fullpath, task_id, min, max))

  def __get_file_content(self, file_id):
    return self.__db__.query("""SELECT content
      FROM file
      WHERE id = %s""",(file_id))

  def __get_ouput(self, fn, task):
    if isinstance(task, list):
      task = task[0]

    gzipped, out = fn(task.id)
    out = str(out)

    if not out:
      return "(not a command)"

    if gzipped:
      return zlib.decompress(out)

    return out

  # Find tasks in root by description (path)
  def find_task_by_root( self, path, root_task = None):
    paths = path.split(' > ')

    tasks = self.__find_task_by_root(
      (root_task or self.__root_task__).id,
      paths.pop(0))
   
    if tasks:
      return self.find_task(' > '.join(paths), tasks)
    return tasks
    

  # Find tasks by description (path)
  def find_task(self, path, tasks = []):
    paths = path.split(' > ') + ['']

    if not tasks:
      p = paths[0].strip()
      find_task_fn = self.__find_task_by_root
      if p == '%': find_task_fn = self.__find_task
      tasks = find_task_fn(self.__root_task__.id, paths.pop(0))

    task_queue = [None] +  tasks;

    desc = None
    while paths and task_queue:
      task = task_queue.pop(0)
      if not task:
        desc = paths.pop(0)
        task_queue.append(None)
        continue

      task_queue+=self.__find_task(task.id, desc)

    task_queue.pop()
    return task_queue

  # Add or append history report
  # It is a "box" report in the main UI window
  def add_history( self, color, html):
    if color:
      html = "<td bgcolor=%s>%s</td>" % (color, html)

    ok, _ =self.__db__.safe_execute(
      """INSERT INTO history (task_id, link_task_id, html_table_row)
      VALUES (%s, %s, %s)""", (
        self.__root_task__.id, self.__link_task_id__, html))
    if not ok:
      self.__add_history(self.__root_task__.id, html)

  # Get previous run of the task
  def get_previous_run(self, task = None):
    return self.__prev_root_task(task or self.__root_task__)

  # Get task command stdout
  def get_stdout( self, task):
    return self.__get_ouput(self.__get_stdout, task)

  def get_stderr( self, task):
    return self.__get_ouput(self.__get_stderr, task)

  # Get task status
  def get_status( self, task):
    if isinstance(task, list):
      task = task[0]
    status =  self.__get_status(task.id)
    if status:
      return status[0]
    return None

  # Get task command stderr
  def find_failed(self, task):
    result = None

    while True:
      tasks = self.__find_failed_task(task.id);
      if tasks:
        task = tasks.pop(0)
        result = task
      else:
        break

    return result

  # Add new report
  def add_report(self, html, views = {}):
    gzipped, buf = Compressor.compress_maybe(html);

    report_id = self.__insert_report(
      self.__root_task__.id, gzipped, buf)

    for view_type, urls in views.items():
      for url in urls:
        result = self.__db__.query(
          """SELECT id FROM view WHERE url = %s""", (url,))
        if result:
          view_id = result[0]
        else:
          view_id = self.__insert_view(view_type, url)
        self.__link_view(report_id, view_id)

    return report_id

  # Get task href
  def task_href( self, task ):
    return "?task=%s" % task.id

  # Get report href
  def report_href (self, report_id):
    return "?report=%s" % report_id

  @property
  def link_task_id(self):
    return self.__link_task_id__;

  # Get link to taskbot UI
  def get_taskbot_link(self):
    host = os.environ.get(
      'TASKBOT_PUBLIC_HTML_HOST',
      get_host_name())
    return "http://%s/taskbot/browse.cgi?platform=%s&branch=%s" % \
       (host,
        urllib.quote(self.__platform__.host),
        urllib.quote(os.environ['TASKBOT_BRANCHNAME']))
        
  def generate( self ):
    result = self.__generate__()
    self.__db__.commit()
    return result

  # Should return int for sys.exit:
  #   0 - if report sucessfully generated,
  #   or non-zero exit code.
  def __generate( self ):
    methodNotImplemented()
  
