#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Update report

import sys, re, cgi, os

pycommons = os.path.join(
  os.path.dirname(os.path.realpath(__file__)),
  '../../../pycommons')
sys.path.insert(0, pycommons)
from Report import Report

JIRA_HREF = "https://networkoptix.atlassian.net/browse/"

def add_jira_link(src):
  return re.sub(
    r'([A-Z]+-[0-9]+)',
    r'<a href="' + JIRA_HREF + r'\1">\1</a>', src)

MAX_WIDTH = 25
def strict_message(msg):
  if len(msg) > MAX_WIDTH:
    return msg[:MAX_WIDTH-3] + '...'
  return msg
  

class UpdateReport(Report):

  def __init__(self, config):
    Report.__init__(self, config)

  def __generate__( self ):
    import HGUtils
    type = "Changes"
    
    commits = HGUtils.changes(self, self.get_previous_run());
    if commits is None:
      print >> sys.stderr, "There are no commits!"
      return 1
    
    history = "%s<br>" % type

    repo_name = None
    for repo, commits in commits.items():
      if commits:
        history += """<b>%s#%s</b><br>\n""" % \
          (repo, commits[0].rev)
        history += """<table align="left">\n"""
        for c in commits:
          history+="<tr><td>%s</td>\n" % c.author
          history+="<td><a href=\"%s\">%s</a></td>\n" % (c.ui_rev, c.repo.name)
          history+="<td>%s</td></tr>\n" % add_jira_link(cgi.escape(strict_message(c.description)))
        history += "</table>"

    print "Add update report:\n%s" % history
    self.add_history('#f0f0f0', history);
    return 0
    
    
if __name__ == "__main__":
  sys.exit(UpdateReport(sys.argv[1]).generate())


  
