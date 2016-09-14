#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Core taskbot script

import sys, os, importlib, re, subprocess, tempfile, time, zlib, threading, signal
from optparse import OptionParser
from Queue import Queue, Empty

sys.path.insert(0, "../pycommons")
from MTValue import MTFlag, MTValue
from Shutdown import shutdown
from MySQLDB import MySQLDB

CMD_HEADER_REGEX="^\s*#\s*(%s{1,2})(\s*!\s*(timeout)\s*=)?\s*(.*\S)\s*$" % re.escape('+')
DEFAULT_SHELL="/bin/bash"

# Read config and initialize environment
def read_config(config):
  try:
    directory, module_name = os.path.split(config)
    module_name = os.path.splitext(module_name)[0]
    path = list(sys.path)
    sys.path.insert(0, directory)
    try:
      config_module = __import__(module_name)
      cfg = getattr(config_module, 'config')
      return cfg
    finally:
      sys.path[:] = path
  except ImportError, x:
    print >> sys.stderr, "Cannot read config '%s': %s" % (config, x)
    exit(1)
    
# Initialize environment
def init_environment(config, options):
  environment = config.get('environment', {})
  for var, value in environment.items():
    os.putenv(var, value)

  os.putenv('TASKBOT', os.path.join(os.getcwd(), sys.argv[0]))
  if options.trace:
    os.putenv('TASKBOT_OPTIONS', '--trace')
  else:
    os.putenv('TASKBOT_OPTIONS', '')
  os.environ['TASKBOT_PARENT_PID'] = "%s" % os.getpid()


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
    

# Compress output
class Compressor:

  gzip_threshold = None
  gzip_ratio = None

  @classmethod
  def compress_maybe(cls, buf):
    if Compressor.gzip_threshold and \
       Compressor.gzip_ratio and \
       len(buf) >= cls.gzip_threshold:
      buf_gz = zlib.compress(buf)
      if len(buf_gz) <= len(buf) * cls.gzip_ratio:
        return (True, buf_gz)
    return False, buf

# Trace log
class Trace:

  enable_trace = False

  @classmethod
  def trace (cls, msg):
    if cls.enable_trace:
      print "%s" %msg

# Non-blocking read from stdout, stderr
class OutputReader:

  def __init__(self, stream):
    self.__stream__ = stream
    self.__thread__ = threading.Thread(
      target = self.__read)
    self.__thread__.daemon = True
    self.__queue__ = Queue()
    self.__thread__.start()

  def __read(self):
    for line in iter(self.__stream__.readline, b''):
      if shutdown.get(): return
      self.__queue__.put(line)

  def get(self):
    strm = ''
    while not shutdown.get():
      try:
        strm += self.__queue__.get_nowait()
      except Empty:
        return strm
    return strm

# Check status or timeout
class StatusChecker:

  def __init__(self, status_fd):
    self.__status_fd__ = status_fd
    self.__thread__ = threading.Thread(
      target = self.__read)
    self.__thread__.daemon = True
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

  def wait( self, timeout = None ):
    try:
      self.__ready__.wait(timeout)
      s = self.__status__.get()
      return s
    finally:
      self.__ready__.set(False)
      self.__status__.set()
  
# Taskbot script executor
class TaskExecutor:

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

  def __init__(self, db, shell, parent_task_id = None):
    self.__task_stack__ = []
    self.__db__ = db
    self.__branch_id__ = self.__select_branch()
    
    self.__root_task_id__ = \
      self.__select_root_task_id(parent_task_id)
      
    self.__task_stack__.append(
      TaskExecutor.Task(parent_task_id, False))
 
    self.__rfdstatus__, self.__wfdstatus__ = os.pipe()

    self.__shell_process__ = \
      subprocess.Popen(
      [shell, '-s', '--'],
      preexec_fn = self.__before_exec,
      shell = False,
      stdin  = subprocess.PIPE,
      stdout = subprocess.PIPE,
      stderr = subprocess.PIPE)

    self.__out__ = OutputReader(self.__shell_process__.stdout)
    self.__err__ = OutputReader(self.__shell_process__.stderr)
    self.__status__ = StatusChecker(self.__rfdstatus__)
    os.close(self.__wfdstatus__)
    self.closed = False

  # Get taskbot branch id
  def __select_branch(self):
    if os.environ.get('BRANCH_NAME'):
      res = self.__db__.query(
        MySQLDB.SELECT_BRANCH,
        (os.environ['BRANCH_NAME'],))
      if res:
        return res[0]
    return None

  def __select_root_task_id(self, parent_task_id):
    if parent_task_id:
      res =  self.__db__.query(
          MySQLDB.SELECT_ROOT_TASK,
          (parent_task_id,))
      if res: return res[0]
    return None
    

  def __before_exec( self ):
    os.setsid() # TODO. Need cross-platform solution to kill child processs
    os.close(self.__rfdstatus__)

  def __check_get_status( self, status, task ):
    if status:
      if len(status) == 0: # shell was terminated
        task.error_message = "non-zero exit status (execution terminated)"
        return self.__shell_process__.returncode, True
      status = int(status)
      if status != 0:
        task.error_message = "non-zero exit status"
      return status, False
    task.error_message = "command_timeout has expired"
    return 1, True
    

  def start_command(self, command):
    return self.start_task(command, True)

  def write_command(self, command, is_comment=False, timeout = None):
    self.__shell_process__.stdin.write(command)
    if not is_comment:
      status = self.__status__.wait(timeout)
      stdout = self.__out__.get()
      stderr = self.__err__.get()
    
      Trace.trace("  STATUS:   %s\n  STDOT:\n    %s\n  STDERR:\n    %s" % \
       (status, StrictOutput.strict(stdout),  StrictOutput.strict(stderr)))
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
    Trace.trace("%s:\n  %s" % (task, command))
    status, stderr, stdout = \
      self.write_command("{ %s\n/bin/echo $? >&%d; }\n" % \
        (command, self.__wfdstatus__), False, timeout)

    # Finish command
    self.finish_command(status, stderr, stdout)
    if status == '0':
      self.finish_tasks_to_level(0)
    return status

  def finish_command(self, status, err, out):
    self.__db__.ping()

    task = self.__task_stack__[-1]
    status, do_terminate = self.__check_get_status(status, task)

    self.__db__.execute(
      MySQLDB.FINISH_COMMAND,
      (task.task_id,) + Compressor.compress_maybe(out) + \
      Compressor.compress_maybe(err) + (status,))

    if do_terminate:
      shutdown.set()
      self.close()
   
    self.finish_task(True)
    

  def finish_task(self, in_transaction = False):
    if not in_transaction:
      self.__db__.ping()

    task = self.__task_stack__.pop()

    self.__db__.execute(
      MySQLDB.FINISH_TASK,
      (time.time(), task.error_message, task.task_id))

    self.__db__.execute(
      MySQLDB.DELETE_RUNNING_TASK,
      (task.task_id,))

    if len(self.__task_stack__) > 1:
        self.__task_stack__[-1].error_message = task.error_message;

    self.__db__.commit()
    
  def finish_tasks_to_level(self, level):
    while len(self.__task_stack__) > level + 1:
      self.finish_task()

  def close(self):
    self.__status__.stop()
    self.__shell_process__.stdin.close()
    # TODO. Need cross-platform solution to kill child processs
    os.killpg(os.getpgid(self.__shell_process__.pid), signal.SIGTERM)
    self.__shell_process__.kill()
    self.__shell_process__.terminate()
    self.finish_tasks_to_level(0)
    self.closed = True

  # Start new task
  def start_task(self, description, is_command=False):
    parent_task_id = None
    if len(self.__task_stack__):
      parent_task_id = self.__task_stack__[-1].task_id
    task_id = self.__db__.execute(
      MySQLDB.START_TASK,
      (self.__root_task_id__, parent_task_id,  self.__branch_id__,
       description,  is_command, time.time()))
    
    if not self.__root_task_id__:
      self.__root_task_id__ = task_id

    self.__task_stack__.append(TaskExecutor.Task(task_id, is_command))
    
    self.__db__.execute(
      MySQLDB.CREATE_RUNNING_TASK,
      (task_id, os.environ['HOSTNAME'], 
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

  (options, args) = parser.parse_args()

  if len(args) == 0 or \
         (len(args) == 1 and not option.command):
    parser.print_help()
    exit(1)
    
  config = args[0]
  script = options.command or args[1]

  Trace.enable_trace = options.trace

  os.putenv('TASKBOT_CONFIG', config)
  config = read_config(config)
  Compressor.gzip_threshold = config.get('gzip_threshold', 0)
  Compressor.gzip_ratio = config.get('gzip_ratio', 0)
  StrictOutput.max_output_size = config.get('max_output_size', 0)
  global_timeout = config.get('run_timeout', None)
  database = MySQLDB(config.get('db_config', None))
 
  # Detect parent task
  parent_task_id = None
  if (os.environ.get('TASKBOT_PARENT_PID')):

    parent_task_id, = \
      database.query(
        MySQLDB.SELECT_PARENT_TASK,
        (os.environ['HOSTNAME'], os.environ['TASKBOT_PARENT_PID']))

  init_environment(config, options)

  executor = TaskExecutor(
    database,
    shell = config.get('sh', DEFAULT_SHELL),
    parent_task_id = parent_task_id)

  if options.description:
    executor.start_task(options.description)

  command = ''
  command_timeout = None
  status = 0
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
          command_timeout or global_timeout)
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
      command_timeout or global_timeout)
    executor.close()
    
  database.commit()
  database.close()

  exit(status)
    
      
if __name__ == "__main__":
  main()
