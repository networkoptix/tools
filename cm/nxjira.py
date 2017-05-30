#!/usr/bin/env python2
# -*- coding: utf-8 -*-
__author__ = 'Danil Lavrentyuk'
import sys, os
import traceback as TB
import requests
import json
import StringIO
#import jira
import re
import copy

JIRA = "https://networkoptix.atlassian.net"
JIRAAPI = JIRA + "/rest/api/2/"
ISSUE = JIRAAPI + "issue/"
BROWSE = JIRA + "/browse/"
AUTH = ("service@networkoptix.com", "kbnUk06boqBkwU")

CODE_OK = 200
CODE_CREATED = 201
CODE_NO_CONTENT = 204
CODE_NOT_FOUND = 404
FIX_VERSION = "3.1"
HOT_FIX_VERSION = "3.0_hotfix"
JIRA_PROJECT = "VMS" # use "TEST" for testing

_version_rx = re.compile(r"^\d+\.\d+(\.\d+)?")

issue_data = {
    "fields" : {
        "project": { "key": JIRA_PROJECT },
        "issuetype": { "name": "Crash" },
        "summary": "Testing bug creation scripting",
        "customfield_10200": {"value": "Server"},
        "versions": [ ],
        "customfield_10800": "",
        "fixVersions": [ {"name": FIX_VERSION } ],
        "components": [ {"name": "Server" } ] ,
        "description": "Not a bug really, just testing the API",
        'priority': { "name": "Low" },
        "customfield_10009": "VMS-2022",
    }
}

transition_data = {
    #"Start Development": {
    #    "update" : { "comment": [{"add":{"body": "start fixing"}}]},
    #    "transition" : { "id": 11 }
    #},
    #"Back to Development": {
    #    "update" : { "comment": [{"add":{"body": "Crash Monitor: New crashes detected"}}]},
    #    "transition" : { "id": 91 }
    #},
    "Reopen": {
        "update" : { "comment": [{"add":{"body": "Crash Monitor: New crashes detected"}}]},
        "transition" : { "id": 121 }
    },
}


def _parse_fixVersion(version):
    if version == 'Future':
        return [0, 0, 0]
    m = _version_rx.match(version)
    return [int(n) for n in m.group(0).split('.')] if m else None


class JiraError(RuntimeError):

    def __init__(self, code, reason, reply):
        RuntimeError.__init__(self, code, reason, reply)
        self.message = "Jira response %s: %s" % (code, reason)
        self.reply = reply


class JiraReply(object):

    def __init__(self, data, code, reason):
        self.data = data
        self.code = code
        self.reason = reason
        self.ok = code == CODE_OK

    def mk_error(self):
        return JiraError(self.code, self.reason, self.data)

    def resolution(self):
        if self.data['fields']['resolution']:
            return self.data['fields']['resolution']['name']
        return 'Unresolved'

    def is_done(self):
        return self.ok and self.data['fields']['status']['statusCategory']["name"] != "To Do"

    def is_rejected(self):
        return self.ok and self.resolution() == "Rejected"

    def is_duplicate(self):
        return self.ok and self.resolution() == "Duplicate"

    def is_closed(self):
        return self.ok and self.data['fields']['status']["name"] == "Closed"

    def changeset(self):
        if self.ok:
            try:
                return int(self.data['fields']['customfield_10800'])
            except:
                return 0
        return 0

    def affect_versions(self):
        if self.ok:
            return [v['name'] for v in self.data['fields']['versions']]
        return []

    def smallest_fixversion(self):
        if self.ok:
            versions = sorted(filter(None,
                (_parse_fixVersion(v['name']) for v in self.data['fields'].get('fixVersions', []))))
            return versions[0] if versions else None
        return None

    def __update_build_number(self, build_number):
        put_result = jirareq('PUT', self.data['key'], {"fields": { "customfield_10800": build_number}})
        if put_result.code not in (CODE_NO_CONTENT, CODE_OK):
            return False
        return True

    def reopen(self, build_number):
        if self.ok and self.is_closed():
            reply = jirareq("POST", self.data['key'] + '/transitions', data=transition_data["Reopen"])
            if reply.code != CODE_NO_CONTENT:
                print "ERROR: Can't reopen issue %s: %s %s - %s" % (
                    self.data['key'], reply.code, reply.reason, reply.data['errorMessages'])
                return False
            return True
        if self.ok:
            print "ERROR: issue %s isn't closed, so can't reopen id" % (self.data['key'],)
        else:
            print "ERROR: JiraReply.reopen() called when self.ok isn't True"
        return self.__update_build_number(build_number)


def get_versions():
    url = JIRAAPI + 'project/%s/versions' % JIRA_PROJECT
    res = requests.get(url, auth=AUTH)
    return map(lambda v: v['name'], json.loads(res.content))

def jirareq(op, query, data=None, what='issue'):
    if what == 'issue':
        url = ISSUE + query
    else:
        url = JIRAAPI + what + '/' + query
    try:
        if op == 'GET':
            res = requests.get(url, auth=AUTH)
        elif op == 'DELETE':
            res = requests.delete(url, auth=AUTH)
        else:
            jdata = json.dumps(data)
            #print "Sending by %s json data: %s\nTo: %s" % (op, jdata, url)
            res = requests.request(op, url, data=jdata, auth=AUTH, headers={"Content-Type": "application/json"})
        #print "DEBUG: Query %s status: %s %s" % (query, res.status_code, res.reason)
        if res.content is not None and len(res.content) > 0:
            try:
                content = res.json()
            except ValueError:
                content = res.content
        else:
            content = ''
        reply = JiraReply(content, res.status_code, res.reason)
        if op == 'DELETE' and res.status_code == CODE_NO_CONTENT:
            reply.ok = True
        return reply
    except requests.exceptions.RequestException as e:
        print "JIRA request '%s' error: '%s'" % (url, str(e))
        return JiraReply(str(e), 500, "JIRA '%s' request exception")



def report(data):
    print json.dumps(data, indent=4, sort_keys=True)


def browse_url(issue):
    return BROWSE + issue


def create_issue(name, desc, priority="Medium", component=None,
                 team=None, major_version=None, build=None, is_hot_fix = False):
    issue = copy.deepcopy(issue_data)
    issue['fields']['summary'] = name
    issue['fields']['description'] = desc
    issue['fields']['priority']['name'] = priority
    versions = get_versions()
    if major_version:
        if major_version in versions:
            issue['fields']['versions'].append({'name': major_version})
        hot_fix_version = major_version + '_hotfix'
        if is_hot_fix and hot_fix_version in versions:
            issue['fields']['versions'].append({'name': hot_fix_version})
        if major_version != FIX_VERSION:
            issue['fields']['fixVersions'].append({'name': HOT_FIX_VERSION })
    if build:
        issue['fields']['customfield_10800'] = str(build)
    if component is not None:
        issue['fields']['components'][0]['name'] = component
    if team is not None:
        issue['fields']['customfield_10200']['value'] = team
    print issue
    result =  jirareq('POST', '', issue)
    if result.code != CODE_CREATED:
        print "Error creting JIRA issue: %s, %s" % (result.code, result.reason)
        print "Issue data: %s" % issue
        if result.data:
            print "Server reply: %s" % (result.data,)
        raise result.mk_error()
    else:
        result.ok = True
    return result.data['key'], browse_url(result.data['key'])


def create_attachment(issue, name, data):
    name = name.replace('/','--')
    query = ISSUE + issue + '/attachments'
    try:
        res = requests.request('POST', query, auth=AUTH, headers={"X-Atlassian-Token": "nocheck"},
                               files={'file': (name, data, 'text/plain')})
        if res.status_code != CODE_OK:
            print "Error creating attachment %s to the JIRA issue %s" % (name, issue)
            return (res.status_code, res.reason, res.content)
    except requests.exceptions.RequestException as e:
        print "Error creating attachment %s to the JIRA issue %s: '%s'" % (name, issue, str(e))
        return (500, "JIRA '%s' request exception" % query, str(e))
        
    #print "DEBUG: attached %s" % (name,)
    return None

def create_dump_attachment(issue, url, auth):
    name = os.path.basename(url)
    query = ISSUE + issue + '/attachments'
    try:
        res_dump = requests.get(url, auth = auth)
        if res_dump.status_code != 200:
            print "Error when download dump attachment '%s': %s" % (url, res_dump.status_code)
            return
        res = requests.request('POST', query, auth=AUTH, headers={"X-Atlassian-Token": "nocheck"},
                               files={'file': (name, res_dump.content, 'text/plain')})
        if res.status_code != CODE_OK:
            print "Error creating dump attachment '%s' to the JIRA issue %s" % (name, issue)
    except requests.exceptions.RequestException as e:
        print "Error creating dump attachment '%s' to the JIRA issue %s: '%s'" % (name, issue, str(e))

def create_web_link(issue, name, url):
    try:
        query = issue + '/remotelink'
        data = { "object" : { "url": url, "title": os.path.splitext(name)[0] } }
        res = jirareq('POST', query, data=data)
        if res.code < 200 or res.code > 299 :
            print "Error creating weblink '%s' to the JIRA issue %s" % (url, issue)
            return (res.code, res.reason, res.data)
    except requests.exceptions.RequestException as e:
        print "Error creating weblink '%s' to the JIRA issue %s: '%s'" % (url, issue, str(e))
        return (500, "JIRA '%s' request exception" % query, str(e))
    return None

def update_affect_version(issue, major_version, is_hot_fix):
    versions = get_versions()
    _, issue_data = get_issue(issue)
    new_versions = []
    if major_version in versions and major_version not in issue_data.affect_versions():
        new_versions.append({"add": {'name': major_version}})
    hot_fix_version = major_version + '_hotfix'
    if is_hot_fix and hot_fix_version in versions and hot_fix_version not in issue_data.affect_versions():
        new_versions.append({"add": {'name': hot_fix_version}})
    if new_versions:
        try:
            result =  jirareq('PUT', issue, data={"update": {"versions": new_versions}})
            if result.code < 200 or result.code > 299 :
                print "Error updating affect versions for JIRA issue '%s': %s, %s, %s" % (issue,  result.code, result.reason, result.data)
                return (result.code, result.reason, result.data)
        except requests.exceptions.RequestException as e:
            print "Error updating affect versions for JIRA issue '%s': '%s'" % (issue, str(e))
            return (500, "JIRA '%s' request exception" % query, str(e))
    return None

def get_issue(key):
    "Allows to pass a string issue key or already loaded issue data"
    if isinstance(key, JiraReply):
        return key.data['key'], key
    else:
        return key, jirareq('GET', key)

def priority_change(key, new_prio, old_prio=None):
    key, result = get_issue(key)
    if result.ok:
        try:
            if result.data['fields']['status']['statusCategory']["name"] == "Done":
                print "%s task statusCategory == Done. Priority wouldn't be changed."
                return None
            pd = result.data['fields']['priority']
            #print "DEBUG: %s: current priority: %s, %s" % (key, pd['id'], pd['name'])
            if old_prio is not None and pd["name"] != old_prio:
                print "DEBUG: priority != %s. No change" % old_prio
        except KeyError, e:
            print "Jira response structure error: no key '%s' found" % e.args[0]
            return None
        put_result = jirareq('PUT', key, {"fields": { "priority": {"name": new_prio}}})
        if put_result.code not in (CODE_NO_CONTENT, CODE_OK):
            raise put_result.mk_error()
        return True
    return False


def count_attachments(key, predicat=None):
    """Returns tuple (None, numnber_attachments) if result.ok
    else (result.code, result.reason)
    """
    key, result = get_issue(key)
    if result.ok:
        if predicat is None:
            count = len(result.data['fields'].get('attachment',[]))
        else:
            count = sum(1 for att in result.data['fields'].get('attachment',[]) if predicat(att))
        return None, count
    return result.code, result.reason

def delete_oldest_attchment(key, predicat=None):
    """Deletes issue's attachment with the oldest upload time.
    Returns True if no attachments found in the issue or on sucessful deletion.
    """
    k, result = get_issue(key)
    if not result.ok:
        return False
    attachments = result.data['fields'].get('attachment', None)
    if not attachments:
        return True
    if predicat is not None:
        attachments = filter(predicat, attachments)
        if not attachments:
            return True
    to_del = sorted(attachments, key=lambda a: a['created'])[0]
    reply = jirareq('DELETE', to_del['id'], what='attachment')
    if reply.ok:
        if key == result: # i.e. we work with preloaded data
            result.data['fields']['attachment'].remove(to_del)
        return True
    print "WARNING: Failed to delete attachment %s of issue %s: %d '%s'" % \
    (to_del['id'], k, reply.code, reply.reason)
    return False

def count_web_links(key, predicat=None):
    """Returns tuple (None, numnber_attachments) if result.ok
    else (result.code, result.reason)
    """
    key, result = get_issue(key)
    if not result.ok:
        return result.code, result.reason
    result = jirareq('GET', '%s/remotelink' % key)
    if result.ok:
        if predicat is None:
            count = len(result.data)
        else:
            count = sum(1 for link in result.data if predicat(link))
        return None, count
    return result.code, result.reason

def delete_oldest_web_link(key, predicat=None):
    key, result = get_issue(key)
    if not result.ok:
        return False
    result = jirareq('GET', '%s/remotelink' % key)
    if not result.ok:
        return False
    links = result.data
    if predicat is not None:
        links = filter(predicat, links)
    if not links:
        return True
    to_del = sorted(links, key=lambda l: l['id'])[0]
    reply = jirareq('DELETE', '%s/remotelink/%s' % (key, to_del['id']))
    if reply.ok:
        return True
    print "WARNING: Failed to delete remotelink %s of issue %s: %d '%s'" % \
        (to_del['id'], key, reply.code, reply.reason)
    return False

##############
# Testing (development tries) function

def _test_create():
    result =  jirareq('POST', '', issue_data)
    if result.code != CODE_CREATED:
        print "Error!"
        print result.data
        return
    print "Created issue %s '%s', url %s" % (result.data['id'], result.data['key'], result.data['self'])
    key = result.data['key']
    #if data["fields"]:
    #    code, reply, reason = jirareq('PUT', key, data)
    #    if code != CODE_NO_CONTENT:
    #        print reply
    _test_attach(key)
    _test_priority_boost(key)


def _test_attach(key):
    test = open('opendump.bat').read()
    res = requests.request('POST', ISSUE + key + '/attachments', auth=AUTH, headers={"X-Atlassian-Token": "nocheck"},
                           files={'file': ('some-file-name.txt', test, 'text/plain')})
    print "Query status: %s %s" % (res.status_code, res.reason)
    print res.content


def _test_priority_boost(key):
    result = jirareq('GET', key)
    if result.ok:
        pd = result.data['fields']['priority']
        print "Current priority: %s, %s" % (pd['id'], pd['name'])
        p = int(pd['id'])
        if p == 1:
            print "Highest priority already!"
            return
        reply = jirareq('PUT', key, {"fields": { "priority": {"id": str(p-1)}}})
        print "Result: %s\n%s" % (reply.code, reply.data)


def _test_check_attachments(key):
    key, result = get_issue(key)
    if result.ok:
        sorted_att = sorted(result.data['fields'].get('attachment',[]), key=lambda a: a['created'])
        for att in sorted_att:
            print "Id %s, tm %s" % (att['id'], att['created'])
            print att['filename']
        print "Now removing the elder attachment"
        reply = jirareq('DELETE', sorted_att[0]['id'], what='attachment')
        # good answer is CODE_NO_CONTENT
        print "Reply: code %s, reason %s, data: %s" % (reply.code, reply.reason, reply.data)


def _test_get_fixVersion(key):
    key, result = get_issue(key)
    if result.ok:
        for v in result.data['fields']['fixVersions']:
            print v
            m = _version_rx.match(v['name'])
            if m:
                print "Match: %s" % (m.group(0),)
            else:
                print "Don't match"

        versions = [[int(n) for n in m.group(0).split('.')] for m in (
            _version_rx.match(v['name']) for v in result.data['fields']['fixVersions']
        ) if m]
        print sorted(versions)


def _test_trans(key, trans):
    key, result = get_issue(key)
    if result.ok:
        data = transition_data[trans]
        reply = jirareq("POST", key + '/transitions', data=data)
        print reply.code, reply.reason
        print reply.data

if __name__ == '__main__':
    #_test_trans('TEST-121', "Reopen")
    #create()
    #priority_boost('TEST-26')
    #for k in ('TEST-97', 'TEST-100'):
    #    print "%s: %s" % (k, count_attachments(k))
    #test_check_attachments('TEST-108')
    #test_get_fixVersion('TEST-123')
    #for issue in ('TEST-120','TEST-121','TEST-123'):
    #    print issue, get_smallest_fixversion(issue)

    print "Don't run me!"
