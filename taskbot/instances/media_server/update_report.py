#!/usr/bin/env python

# $Id$
# Artem V. Nikitin
# Update report

import sys, re, cgi
sys.path.insert(0, '../../pycommons')
from Report import Report

JIRA_HREF = "https://networkoptix.atlassian.net/browse/"

def add_jira_link(src):
  return re.sub(
    r'([A-Z]+-[0-9]+)',
    r'<a href="' + JIRA_HREF + r'\1">\1</a>', src)

MAX_WIDTH = 25
def strict_message(msg):
  if msg > MAX_WIDTH:
    return msg[:MAX_WIDTH-3] + '...'
  return msg
  

class UpdateReport(Report):

  def __init__(self, config):
    Report.__init__(self, config)

  def __generate__( self ):
    import HGUtils
    type = "Media-server changes"
    
    commits = HGUtils.changes(self, self.get_previous_run());
    if commits is None:
      return 1
    
    history = "%s<br><table align=\"left\">\n" % type

    for c in commits:
      # my $author = join ' ', map ucfirst, split '_', $c->{author};
      history+="<tr><td>%s</td>\n" % c.author
      history+="<td><a href=\"%s\">%s</a></td>\n" % (c.ui_rev, c.repo.name)
      history+="<td>%s</td></tr>\n" % add_jira_link(cgi.escape(strict_message(c.description)))

    history += "</table>"

    self.add_history('#f0f0f0', history);
    return 0
    
    
if __name__ == "__main__":
  sys.exit(UpdateReport(sys.argv[1]).generate())


  
