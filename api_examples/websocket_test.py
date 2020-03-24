import websocket
from websocket import create_connection

def test():
    uri = 'ws://localhost:7001/ec2/messageBus?format=json&peerType=PT_VideowallClient&runtime-guid={368ee6da-7608-45a4-9867-5a0af04c7e8d}&videoWallInstanceGuid={3b25cc0a-8a7c-458c-adc8-8e173a9b8d7f}'

    headers = [
        "X-Version: 1",
        "X-NetworkOptix-VideoWall: {c9a802fc-aa33-4afb-8701-a3943e8153ba}",
        "X-runtime-guid: {368ee6da-7608-45a4-9867-5a0af04c7e8d}"
    ]

    ws = create_connection(uri, header=headers)
    print "Receiving..."
    result = ws.recv()
    print "Received '%s'" % result
    ws.close()


def on_message(ws, message):
    print('RECEIVED: {}'.format(message))


def main():
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        'ws://127.0.0.1:7001/ec2/messageBus',
        on_message=on_message,
        header=["X-NetworkOptix-VideoWall: {c9a802fc-aa33-4afb-8701-a3943e8153ba}"])
    ws.run_forever()


if __name__ == '__main__':
    main()
