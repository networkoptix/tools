import requests
import requests.auth

CLOUD_HOST = 'dev2.cloud.hdw.mx'

SYSTEM_ID = '733126ed-982f-4176-acd4-a44d0a38a328'
SYSTEM_AUTK_KEY = '872c8756-af59-4ba6-a390-92e40a5e0114'
TARGET_USERS = ['rbarsegian+test200@networkoptix.com']


def send_notification(notification_dict, targets, system_id, system_auth_key):
    requests.post(
        f'https://{CLOUD_HOST}/cloud_notifications/receiver/api/v1/send_notification',
        auth=requests.auth.HTTPBasicAuth(system_id, system_auth_key),
        json={
            'targets': targets,
            'systemId': system_id,
            'notification': notification_dict
        }
    )


if __name__ == '__main__':
    send_notification({'title': 'Hello', 'body': 'Hi there!'}, TARGET_USERS, SYSTEM_ID, SYSTEM_AUTK_KEY)
