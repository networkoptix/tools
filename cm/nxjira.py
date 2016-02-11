#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
__author__ = 'Danil Lavrentyuk'
import sys, os
import traceback as TB
import requests
import json
import StringIO
#import jira

JIRA = "https://networkoptix.atlassian.net"
JIRAAPI = JIRA + "/rest/api/2/"
ISSUE = JIRAAPI + "issue/"
BROWSE = JIRA + "/browse/"
AUTH = ("dlavrentyuk", "LathanderTest109")

CODE_OK = 200
CODE_CREATED = 201
CODE_NO_CONTENT = 204


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


def jirareq(op, query, data=None, what='issue'):
    if what == 'issue':
        url = ISSUE + query
    else:
        url = JIRAAPI + what + '/' + query
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


def report(data):
    print json.dumps(data, indent=4, sort_keys=True)


issue_data = {
    "fields" : {
        "project": { "key": "TEST" },  # "VMS" #FIXME make it configurable
        "issuetype": { "name": "Task" },
        "summary": "Testing bug creation scripting",
        "customfield_10200": {"value": "Server"},
        "fixVersions": [ {"name": "Future"} ],
        "components": [ {"name": "Server" } ] ,
        "description": "Not a bug really, just testing the API",
        'priority': { "name": "Low" },
        "customfield_10009": "TEST-1", # TODO: change to the real epic in VMS  #FIXME make it configurable
    }
}


def browse_url(issue):
    return BROWSE + issue


def create_issue(name, desc, priority="Medium"):
    issue = issue_data.copy()
    issue['fields']['summary'] = name
    issue['fields']['description'] = desc
    issue['fields']['priority']['name'] = priority
    result =  jirareq('POST', '', issue)
    if result.code != CODE_CREATED:
        print "Error creting JIRA issue: %s, %s" % (result.code, result.reason)
        if result.data:
            print "Server reply: %s" % (result.data,)
        raise result.mk_error()
    else:
        result.ok = True
    return result.data['key'], browse_url(result.data['key'])


def create_attachment(issue, name, data):
    name = name.replace('/','--')
    res = requests.request('POST', ISSUE + issue + '/attachments', auth=AUTH, headers={"X-Atlassian-Token": "nocheck"},
                           files={'file': (name, data, 'text/plain')})
    if res.status_code != CODE_OK:
        print "Error creating attachment %s to the JIRA issue %s" % (name, issue)
        return (res.status_code, res.reason, res.content)
    #print "DEBUG: attached %s" % (name,)
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
    """"Returns tuple (None, numnber_attachments) if result.ok
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
    """"Deletes issue's attachment with the oldest u[load time.
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
    print "WARNING: Failed to delete attachment %s of issue %s" % (to_del['id'], k)
    return False

def test_create():
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
    test_attach(key)
    test_priority_boost(key)


def test_attach(key):
    test = open('opendump.bat').read()
    res = requests.request('POST', ISSUE + key + '/attachments', auth=AUTH, headers={"X-Atlassian-Token": "nocheck"},
                           files={'file': ('some-file-name.txt', test, 'text/plain')})
    print "Query status: %s %s" % (res.status_code, res.reason)
    print res.content


def test_priority_boost(key):
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


def test_check_attachments(key):
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




if __name__ == '__main__':
    #create()
    #priority_boost('TEST-26')
    #for k in ('TEST-97', 'TEST-100'):
    #    print "%s: %s" % (k, count_attachments(k))
    #test_check_attachments('TEST-108')
    print "Don't run me!"
