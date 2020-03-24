#/bin/python

import requests

def send_request(req):
    try:
        r = requests.get(req, auth=('admin', 'admin'), timeout=1)
        print ("Success" if r.status_code == 200 else "Error")
    except:
        print "Timeout"    
        
def getRequests():
    events = ["networkIssue", "disconnected"]
    ids = ["noframe", "packetloss", "closed"]
    cameras = ["urn_uuid_7841e1c8-db81-11d3-ba38-3191735595fb", "64-76-57-80-05-7F", "urn_uuid_b0e78864-c021-11d3-a482-f12907312681"]
    paramsPacketLoss = ["1234;5678", "5679;9101", "9102;1314"]
    paramsNoFrame = ["5000", "7000", "8000"]
    paramsClosed = ["0", "1"]
    
    for event in events:
        for id in ids:
            for camera in cameras:
                params = []                
                if id == "noframe":
                    params = paramsNoFrame
                elif id == "packetloss":
                    params = paramsPacketLoss
                elif id == "closed":
                    params = paramsClosed
                for param in params:
                    yield "http://localhost:7001/api/debugEvent/{0}?id={1}&cameraId={2}&param={3}".format(event, id, camera, param)
        
def main():
    for req in getRequests():
        print req
        send_request(req)

if __name__ == "__main__":
    main()