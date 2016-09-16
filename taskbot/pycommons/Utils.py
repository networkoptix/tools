import os, sys

def methodNotImplemented( obj = None ):
  raise Exception('(%s) Abstract method call: method is not implemented' % obj)

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
      pass
      # sys.path[:] = path
  except ImportError, x:
    print >> sys.stderr, "Cannot read config '%s': %s" % (config, x)
    sys.exit(1)
  except AttributeError, x:
    print >> sys.stderr, "Cannot read config '%s': %s" % (config, x)
    sys.exit(1)
    
# Initialize environment
def init_environment(config, options = None):
  environment = config.get('environment', {})
  for var, value in environment.items():
    os.environ[var] = value

  os.putenv('TASKBOT', os.path.join(os.getcwd(), sys.argv[0]))
  if options and options.trace:
    os.putenv('TASKBOT_OPTIONS', '--trace')
  else:
    os.putenv('TASKBOT_OPTIONS', '')
  os.environ['TASKBOT_PARENT_PID'] = "%s" % os.getpid()
