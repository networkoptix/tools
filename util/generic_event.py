import requests
import argparse
from time import sleep

default_timeout = 60

def send_request():
    try:
        r = requests.get('http://localhost:7001/api/createEvent?caption=Test%20Caption&description=Test%20Description', auth=('admin', 'admin'), timeout=2)
        print ("Success" if r.status_code == 200 else "Error")
    except:
        print "Timeout"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--timeout', type=int, help="Timeout (in seconds), default value is 60")
    parser.add_argument('-o', '--once', help="Send only once", action="store_true")
    args = parser.parse_args()
    
    timeout = args.timeout
    if not timeout:
        timeout = default_timeout
       
    if args.once:
        print "Generate event once"
        send_request()
        return
        
       
    print "Generate event every {0} seconds".format(timeout)

    while True:
        send_request()
        sleep(timeout);

if __name__ == '__main__':
    main()
