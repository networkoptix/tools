# $Id$
# Artem V. Nikitin
# Mercurial usefull command wrappers

import os, subprocess, sys, urllib

HG_UI_ROOT = 'http://enk.me:8082/'

class Repository:

  def __init__(self, path, ui = None, branch = 'default'):
    self.name = os.path.basename(path)
    self.path = path
    self.ui = ui or HG_UI_ROOT + self.name
    self.branch = branch

HOME_PATH = os.environ.get('TASKBOT_HOME', os.environ['HOME'])
DEFAULT_VAR_PATH = os.path.join(HOME_PATH, 'develop')
DEFAULT_DEVTOOLS_PATH = os.path.join(DEFAULT_VAR_PATH, 'devtools')

REPOSITORIES = {
  'devtools': Repository(
    os.environ.get('TASKBOT_REPO',DEFAULT_DEVTOOLS_PATH),
    HG_UI_ROOT + 'devtools'),
  'nx_vms': Repository(
    os.path.join(os.environ.get('TASKBOT_VAR', DEFAULT_VAR_PATH), 'nx_vms'),
    HG_UI_ROOT + 'nx-vms',
    os.environ.get('TASKBOT_BRANCHNAME', 'dev_3.0.0')) }


def get_changes(repo, rev, prev_rev):

  class ChangeSet:

    def __init__(self, repo, cs):
      self.timestamp = cs[0]
      self.author = cs[1]
      self.author_email = cs[2]
      self.rev = cs[3]
      self.description = urllib.unquote(cs[4])
      self.repo = repo
      self.ui_rev = os.path.join(repo.ui, "revision/%s" % self.rev)

    def __str__(self):
      return "ts: %s, author: %s, rev: %s, dsc: %s" % \
      (self.timestamp, self.author, self.rev, self.description)

    def __repr__(self):
      return self.__str__()
  
  r = REPOSITORIES.get(
    repo,
    Repository(
      os.path.join(DEFAULT_VAR_PATH, repo)))

  template = r"{date|isodate}|{author|person}|{author|email}|{node|short}|{desc|firstline|urlescape}\n"

  stored_path = os.getcwd()
  try:
    os.chdir(r.path)
    
    hg_log_cmd = [
      "hg", "log",
      "--rev", " %s..%s" % (prev_rev, rev),
      # "--no-merges", 
      "--template", template,
      "--branch", "%s" % r.branch]

    p = subprocess.Popen(
      hg_log_cmd,
      stdout = subprocess.PIPE,
      stderr = subprocess.PIPE)
    (out, err) = p.communicate()
    if p.returncode:
      print >> sys.stderr, "Can't process '%s' : %s, %s" % \
            (" ".join(hg_log_cmd), p.returncode, err)
      return None

    changes =  [ChangeSet(r, line.split('|')) for line in out.splitlines()]
    return filter(lambda c: c.rev != prev_rev, changes)
  finally:
    os.chdir(stored_path)
 

def changes(report, since):
  revisions = \
      report.find_task_by_root('%remember_revisions.taskbot% > Remember revisions > %')

  prev_revisions = \
     report.find_task_by_root('%remember_revisions.taskbot% > Remember revisions > %', since)

  commits = {}

  for repo_task in report.find_task('%', revisions):
     repo = repo_task.description
     revision = \
       report.get_stdout(report.find_task('%', [repo_task])).strip()
     prev_revision = \
       report.get_stdout(report.find_task(repo + ' > %' , prev_revisions)).strip()
     print revision, prev_revision
     cs = []
     if revision != prev_revision:
       cs = get_changes(repo, revision, prev_revision)
       print "Changeset: %s" % cs
       if cs is None:
         return None
       cs.sort(lambda x, y: x.timestamp > y.timestamp)
     commits[repo] = cs
  return commits
