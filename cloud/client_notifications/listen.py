import asyncio
import json
import requests
import websockets

CLOUD_HOST = 'dev2.cloud.hdw.mx'
CLOUD_USER = 'rbarsegian+test200@networkoptix.com'
CLOUD_PASSWORD = 'qweasd1234'


def get_auth_token(user, password):
    response = requests.post(
        f'https://{CLOUD_HOST}/cdb/oauth2/token',
        json={
            "grant_type": "password",
            "response_type": "token",
            "password": password,
            "username": user
        }
    )
    return response.json().get('access_token')


async def listen_to_notifications(user, access_token):
    async with websockets.connect(f"wss://{CLOUD_HOST}/cloud_notifications/provider/api/v1/subscribe?access-token={access_token}") as websocket:
        while True:
            print(await websocket.recv())


def main():
    access_token = get_auth_token(CLOUD_USER, CLOUD_PASSWORD)
    asyncio.run(listen_to_notifications(CLOUD_USER, access_token))


if __name__ == '__main__':
    main()
