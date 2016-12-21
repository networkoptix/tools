#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Core taskbot script

import sys, os, importlib, re, subprocess, tempfile, time, threading, signal
from optparse import OptionParser

pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../pycommons')
sys.path.insert(0, pycommons)
from MTValue import MTFlag, MTValue, MTBuffer
from Shutdown import shutdown
from MySQLDB import MySQLDB
from Utils import *


CMD_HEADER_REGEX="^\s*#\s*(%s{1,2})(\s*!\s*(timeout)\s*=)?\s*(.*\S)\s*$" % re.escape('+')
DEFAULT_SHELL="/bin/bash"
DEFAULT_BRANCH='Test'
DEFAULT_PLATFORM='Test'

class TimeOut:

  class XTimedOut(Exception):

    def __init__(self, msg, timeout, duration):
      self.msg = msg
      self.timeout = timeout
      self.duration = duration

    def __str__(self):
      return "%s (%d secs): wait %d secs" % \
        (self.msg, self.timeout, self.duration)

  def __init__(self, run_timeout, select_timeout):
    self.__run_timeout__ = run_timeout
    self.__select_timeout__ = select_timeout
    self.__select_timeout_stored__ = select_timeout
    self.__run_start__ = time.time()
    self.__select_start__ = None

  def __check_select(self, selected):
    if selected:
      self.__select_start__ = time.time()
      return False
    else:
      result = \
        self.__select_timeout__ and \
          self.__select_start__ and \
            time.time() - self.__select_start__ > \
              self.__select_timeout__
      if result:
        raise TimeOut.XTimedOut(
          "select_timeout has expired",
          self.__select_timeout__,
          time.time() - self.__select_start__)
    return result

  def __check_run(self, command_timeout):
    timeout = command_timeout or self.__run_timeout__
    result = timeout and \
      time.time() - self.__run_start__ > timeout
    if result:
      raise TimeOut.XTimedOut(
        "run_timeout has expired",
        timeout,
        time.time() - self.__run_start__)
    return result

  def start_command(self, command):
    self.__select_start__ =  time.time()
    # It's very dirty select_timeout reset
    # TODO. Child taskbot should have possibility
    #       to reset parent select timeout
    command = re.sub(r'"', '', command)
    def process_arg(arg):
      return os.path.basename(sub_environment(arg))
    args = map(process_arg, command.split())
    def cmp_arg(arg):
      return arg == os.path.basename(sys.argv[0])
    if  reduce(
      lambda x, y: x or y,
      map(cmp_arg, args), False):
      self.__select_timeout__ = None

  def finish_command(self):
    self.__select_timeout__ = \
      self.__select_timeout_stored__

  def check( self, command_timeout = None, selected = False ):
    return self.__check_select(selected) or \
      self.__check_run(command_timeout)

# Strict output by max size
class StrictOutput:

  max_output_size = None

  @classmethod
  def strict(cls, buf):
    if len(buf) > cls.max_output_size:
      return buf[0:cls.max_output_size]  + \
        "WARNING: stored only last %s"\
        " of the output\n\n..." % cls.max_output_size
    return buf
    
# Trace log
class Trace:

  enable_trace = False

  @classmethod
  def trace (cls, msg):
    if cls.enable_trace:
      sys.stdout.write(msg)
      sys.stdout.flush()

# Non-blocking read from stdout, stderr
class OutputReader:

  def __init__(self, stream):
    self.__stream__ = stream
    self.__thread__ = threading.Thread(
      target = self.__read)
    self.__buffer__ = MTBuffer()
    self.__ready__ = MTFlag()
    self.__thread__.start()

  def __read(self):
    while not shutdown.get():
      c = self.__stream__.read(1)
      if not c:
        break
      self.__buffer__.append(c)
      self.__ready__.set(True)

  def stop(self):
    self.__thread__.join()

  def get(self):
    buf = ''
    while self.__ready__.wait(.1):
      buf+=self.__buffer__.get()
      self.__ready__.set(False)
    return buf

# Check status or timeout
class StatusChecker:

  def __init__(self, status_fd):
    self.__status_fd__ = status_fd
    self.__thread__ = threading.Thread(
      target = self.__read)
    self.__status__ = MTValue()
    self.__ready__ = MTFlag()
    self.__stopped__ = MTValue(False)
    self.__thread__.start()

  def __read(self):
    while not shutdown.get() and not self.__stopped__.get():
      self.__status__.set(os.read(self.__status_fd__, 5))
      self.__ready__.set(True)

  def stop( self ):
    self.__stopped__.set(True)
    self.__thread__.join()

  def wait( self, timeout = None ):
    self.__ready__.wait(timeout)
    if self.__ready__.get():
      s = self.__status__.get()
      self.__status__.set()
      self.__ready__.set(False)
      return s
    return None

# Delete stale records
def delete_stale_records(db):
  host = get_host_name()
  user = os.environ['USER']
  cursor = db.cursor
  cursor.execute("""
    SELECT DISTINCT pid
    FROM running_task
    WHERE host = %s AND user = %s""",
    (host, user))
  pids = []
  for p in cursor:
    pid = int(p[0])
    if pid != os.getpid():
      try:
        os.kill(pid, 0)
      except OSError:
        pids.append(pid)

  for pid in pids:
    print "Deleting stale records from running_task (PID=%s)"\
          " table for user '%s' on host '%s'" % (pid, user, host)
    cursor.execute("""
      DELETE FROM running_task
      WHERE host = %s AND pid = %s""", (host, pid))
  
# Taskbot script executor
class TaskExecutor:

  START_TASK = \
    """INSERT INTO task (root_task_id, parent_task_id, branch_id, 
    platform_id, description, is_command, start, finish)
    VALUES (%s, %s, %s, %s, %s, %s, %s, 0)"""

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

  INSERT_BRANCH = \
    """INSERT INTO branch (description)
    VALUES (%s)"""

  SELECT_PLATFORM = \
    """SELECT id FROM platform
    WHERE host = %s"""

  INSERT_PLATFORM = \
    """INSERT INTO platform (host, description)
    VALUES (%s, %s)"""

  class Task:

    def __init__(self, task_id, is_command):
      self.task_id = task_id
      self.is_command = is_command
      self.error_message = None

    def __str__(self):
      is_cmd = "not command"
      if self.is_command:
        is_cmd = "command"
      return "Task#%d (%s)" % (self.task_id, is_cmd)

    def __repr__(self):
      return self.__str__()

  def __init__(self, db, shell, timeout, parent_task_id = None, args = [], env_vars=[]):
      
    self.__task_stack__ = []
    self.__db__ = db
    self.__timeout__ = timeout
    self.__branch_id__ = self.__select_branch()
    self.__platform_id__ = self.__select_platform()
    
    self.__root_task_id__ = \
      self.__select_root_task_id(parent_task_id)
      
    self.__task_stack__.append(
      TaskExecutor.Task(parent_task_id, False))
 
    self.__rfdstatus__, self.__wfdstatus__ = os.pipe()

    self.__shell_process__ = \
      subprocess.Popen(
      [shell, '-s', '--'] + args,
      preexec_fn = self.__before_exec,
      shell = False,
      stdin  = subprocess.PIPE,
      stdout = subprocess.PIPE,
      stderr = subprocess.PIPE)

    self.__out__ = OutputReader(self.__shell_process__.stdout)
    self.__err__ = OutputReader(self.__shell_process__.stderr)
    self.__status__ = StatusChecker(self.__rfdstatus__)
    self.__env_vars = env_vars
    os.close(self.__wfdstatus__)
    self.closed = False

  # Get taskbot branch id
  def __select_branch(self):
    branch = os.environ.get('TASKBOT_BRANCHNAME', DEFAULT_BRANCH)
    res = self.__db__.query(
      TaskExecutor.SELECT_BRANCH,
      (branch,))
    if res:
      return res[0]
    else:
      return self.__db__.execute(
        TaskExecutor.INSERT_BRANCH, (branch,))

  def __select_platform(self):
    host = get_host_name()
    res = self.__db__.query(
      TaskExecutor.SELECT_PLATFORM,
      (host,))
    if res:
      return res[0]
    else:
      return self.__db__.execute(
        TaskExecutor.INSERT_PLATFORM, (host, get_platform()))

  def __select_root_task_id(self, parent_task_id):
    if parent_task_id:
      res =  self.__db__.query(
          TaskExecutor.SELECT_ROOT_TASK,
          (parent_task_id,))
      if res: return res[0]
    return None
    

  def __before_exec( self ):
    os.setsid() # TODO. Need cross-platform solution to kill child processs
    os.close(self.__rfdstatus__)

  def __check_get_status( self, status, task ):
    if status is not None:
      if len(status) == 0: # shell was terminated
        status = self.__shell_process__.wait()
        if status != 0:
          task.error_message = "non-zero exit status"
        return status, True
      status = int(status)
      if status != 0:
        task.error_message = "non-zero exit status"
      return status, False
    if not task.error_message:
      task.error_message = "command_timeout has expired"
    return 1, True
    

  def start_command(self, command):
    self.__timeout__.start_command(command)
    return self.start_task(command, True)

  def __read_output(self, stream):
    out = stream.get()
    Trace.trace(out)
    return out
    
  def write_command(self, command, is_comment=False, timeout = None, task = None):
    self.__shell_process__.stdin.write(command)

    start = time.time()

    status = None
    stdout = stderr = ''

    if not is_comment:
      while True:
        status = self.__status__.wait(.1)
        out = self.__read_output(self.__out__)
        err = self.__read_output(self.__err__)
        stdout += out
        stderr += err

        if status is not None:
          break
        try:
          self.__timeout__.check(
            timeout, bool(status or out or err))
        except TimeOut.XTimedOut, x:
          if task:
            task.error_message = str(x)
          break

      return status,  stderr, stdout
    return 0, "", ""
   
      
  def process_command(self, command, timeout = None):
    # To get shell line counting right we output comment lines,
    # and then one more line to fake control/empty line (see
    # below).
    if not re.search('^\s*[^\#]', command,  re.MULTILINE | re.DOTALL):
      self.write_command(command + "\n", True)
      return
    task = self.start_command(command)
    Trace.trace("%s\n" % command)
    for v in self.__env_vars:
      self.write_command( "export %s\n" %v, True)
    status, stderr, stdout = \
      self.write_command("{ %s\n/bin/echo $? >&%d; }\n" % \
        (command, self.__wfdstatus__), False, timeout, task)

    status, do_terminate = self.__check_get_status(status, task)

    # Finish command
    self.finish_command(status, stderr, stdout)
    if status == '0':
      self.finish_tasks_to_level(0)
    
    if do_terminate:
      self.close()
      
    return status

  def finish_command(self, status, err, out):
    self.__timeout__.finish_command()
    self.__db__.ensure_connect()

    task = self.__task_stack__[-1]

    self.__db__.execute(
      TaskExecutor.FINISH_COMMAND,
      (task.task_id,) + Compressor.compress_maybe(out) + \
      Compressor.compress_maybe(err) + (status,))
  
    self.finish_task(True)
    

  def finish_task(self, in_transaction = False):
    if not in_transaction:
      self.__db__.ensure_connect()

    task = self.__task_stack__.pop()

    self.__db__.execute(
      TaskExecutor.FINISH_TASK,
      (time.time(), task.error_message, task.task_id))

    self.__db__.execute(
      TaskExecutor.DELETE_RUNNING_TASK,
      (task.task_id,))

    if len(self.__task_stack__) > 1:
      self.__task_stack__[-1].error_message = task.error_message

    self.__db__.commit()
    
  def finish_tasks_to_level(self, level):
    while len(self.__task_stack__) > level + 1:
      self.finish_task()

  def close(self, terminated = False):
    if not self.closed:
      if terminated:
        self.__task_stack__[-1].error_message = 'Terminated'
      if self.__db__.connected:
        safe_call(self.finish_tasks_to_level(0))
      self.closed = True
      safe_call(self.__shell_process__.stdin.close)
      # TODO. Need cross-platform solution to kill child process
      pgid = safe_call(os.getpgid, self.__shell_process__.pid)
      safe_call(os.killpg, pgid, signal.SIGTERM)
      safe_call(self.__shell_process__.kill)
      safe_call(self.__shell_process__.terminate)
      shutdown.set()
      safe_call(self.__status__.stop)
      safe_call(self.__err__.stop)
      safe_call(self.__out__.stop)

  # Start new task
  def start_task(self, description, is_command=False):
    parent_task_id = None
    self.__db__.ensure_connect()
    if len(self.__task_stack__):
      parent_task_id = self.__task_stack__[-1].task_id
    task_id = self.__db__.execute(
      TaskExecutor.START_TASK,
      (self.__root_task_id__, parent_task_id,  self.__branch_id__,
       self.__platform_id__, description,  is_command, time.time()))
    
    if not self.__root_task_id__:
      self.__root_task_id__ = task_id

    self.__task_stack__.append(TaskExecutor.Task(task_id, is_command))
    
    self.__db__.execute(
      TaskExecutor.CREATE_RUNNING_TASK,
      (task_id, get_host_name(), 
       os.getpid(), os.environ['USER']))

    self.__db__.commit()

    return self.__task_stack__[-1]

def main():
  usage = "usage: %prog [options] CONFIG <SCRIPT>"
  parser = OptionParser(usage)
  parser.add_option("-d", "--description",
                    help="Create root task DESCRIPTION.")

  parser.add_option("--trace", default=False, action="store_true",
                    help="Trace execution.  Print every command, " \
                    "its stdout and stderr, and its " \
                    "exit status.  Default is notrace.")
  
  parser.add_option("-c", "--command",
                    help="Execute COMMAND. This option is mutually " \
                    "exclusive with specifying SCRIPT.")

  parser.add_option("-t", "--timeout", type="int",
                    help="Run timeout in seconds.  " \
                    "Zero (or negative) value means indefinite. "\
                    "Overrides corresponding setting in config file.")
  
  parser.add_option("-s", "--select", type="int",
                    help="Select timeout in seconds.  " \
                    "Zero (or negative) value means indefinite. "\
                    "Overrides corresponding setting in config file.")

  parser.add_option("--var", action = "append", default=[],
                    help="List of the environment variables, " \
                    "passed into the script.")


  (options, args) = parser.parse_args()

  if len(args) == 0 or \
         (len(args) == 1 and not options.command):
    print >> sys.stderr, "%s invalid args: '%s'" % (sys.argv[0], args)
    parser.print_help()
    exit(2)
    
  config = args[0]

  Trace.enable_trace = options.trace

  os.putenv('TASKBOT_CONFIG', config)
  config = read_config(config)
  Compressor.gzip_threshold = config.get('gzip_threshold', 0)
  Compressor.gzip_ratio = config.get('gzip_ratio', 0)
  StrictOutput.max_output_size = config.get('max_output_size', 0)
    
  database = MySQLDB(config.get('db_config', None))
 
  # Detect parent task
  parent_task_id = None
  if (os.environ.get('TASKBOT_PARENT_PID')):

    parent_task_id, = \
      database.query(
        TaskExecutor.SELECT_PARENT_TASK,
        (get_host_name(), os.environ['TASKBOT_PARENT_PID']))

  init_environment(config, options)

  run_timeout = config.get('run_timeout', None)
  if options.timeout is not None:
    run_timeout = options.timeout

  select_timeout = config.get('select_timeout', None)
  if options.select is not None:
    select_timeout = options.select

  timeout = TimeOut(
    run_timeout,
    select_timeout)

  delete_stale_records(database)

  executor = TaskExecutor(
    database,
    shell = config.get('sh', DEFAULT_SHELL),
    timeout = timeout,
    parent_task_id = parent_task_id,
    args=args[1 + int(not options.command):],
    env_vars=options.var)

  # Register signal handlers
  def _shutdown( sigNum, frame ):
    executor.close(terminated = True)
  signal.signal(signal.SIGINT,  _shutdown)
  signal.signal(signal.SIGTERM, _shutdown)
  if options.description:
    executor.start_task(options.description)

  command = ''
  command_timeout = None
  status = 0
  try:
    if options.command:
      command = options.command
    else:
      script = args[1]    
      with open(script) as fp:
        for line in fp:
          if executor.closed:
            break
          m = re.search(CMD_HEADER_REGEX, line)
          level = var = value = None
          if m:
            (level, _, var, value) = m.group(1,2,3,4)
          if (re.search('^\s*$', value or line)):
            status = executor.process_command(
              command,
              command_timeout)
            command = ''
            command_timeout = None
          else:
            command+=line
          if m:
            if var == 'timeout':
              # Set command timeout
              command_timeout = float(value);
            elif level:
              executor.finish_tasks_to_level(
                len(level) - 1 + \
                (options.description and 1 or 0))
              executor.start_task(value);

        fp.close()

    if not executor.closed:
      status = executor.process_command(
        command,
        command_timeout)
      executor.close()

    database.commit()
    database.close()
    sys.exit(status)
  except KeyboardInterrupt:
    print >> sys.stderr
    print >> sys.stderr, "%s execution was terminated" % sys.argv[0]
    executor.close(terminated = True)
  except Exception, x:
    print >> sys.stderr
    print >> sys.stderr, "%s execution error '%s'" % (sys.argv[0], x)
    executor.close()
    sys.exit(1)
      
if __name__ == "__main__":
  main()
