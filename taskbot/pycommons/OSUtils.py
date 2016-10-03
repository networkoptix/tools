# $Id$
# Artem V. Nikitin
# OS specific utils

# Windows
def cygpath(path):
  path = re.sub(r'(\w):\\', r'/cygdrive/\1/', path)
  return re.sub(r'\\', r'/', path)
