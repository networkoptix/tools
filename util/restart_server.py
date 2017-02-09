# -*- coding: utf-8 -*-
#/bin/python

import requests
import argparse
from time import sleep

count = 0
default_timeout = 60
default_url = "localhost:7001"

def send_request(apiUrl):
    try:
        global count
        print "Shutting server down: {0}".format(count)
        count += 1
        r = requests.get(apiUrl +'/api/dev-mode-key?razrazraz', auth=('admin', 'admin'), timeout=1)
        print ("Success" if r.status_code == 200 else "Error {0}".format(r.status_code))
    except:
        print "Timeout"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--timeout', type=int, help="Timeout (in seconds), default value is 60")
    parser.add_argument('-u', '--url', type=str, help="Server url in the format localhost:7001")
    args = parser.parse_args()
    
    timeout = args.timeout
    if not timeout:
        timeout = default_timeout
        
    url = args.url
    if not url:
        url = default_url
        
    apiUrl = "http://{0}".format(url)
        
    print "Shutdown {0} every {1} seconds".format(apiUrl, timeout)

    while True:
        send_request(apiUrl)
        sleep(timeout);

if __name__ == '__main__':
    main()
