# This file contains utilities to get update status from mediaservers
"""
POST /api/updates2
{
    "action": "stop"
    "targetVersion": ""
}
"""
"""
enum class Action
{
    stop = 0,
    install = 1,
    download = 2,
    check = 3,
};
"""
import requests
import json
    
ACTION_STOP = 0
ACTION_INSTALL = 1
ACTION_DOWNLOAD = 2
ACTION_CHECK = 3
server_url = 'http://localhost:7001'
    
# Credentials used to login to mediaserver
mediaserver_auth = ('admin', 'qweasd123')

def send_check_update():
    url = server_url + '/api/updates2'
    data = {
        "action": ACTION_CHECK,
        "targetVersion": ""        
    }
    r = requests.post(url, json=data, auth=mediaserver_auth)
    return r.json()

def send_stop():
    url = server_url + '/api/updates2'
    data = {
        "action": ACTION_STOP,
        "targetVersion": ""
    }
    r = requests.post(url, json=data, auth=mediaserver_auth)
    return r.json()
    
def get_update_status():
    url = server_url + '/api/updates2/status/all'
    r = requests.get(url, auth=mediaserver_auth)
    return r.json()