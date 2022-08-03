from __future__ import print_function
import base64
import json
import os
from .email_parser import process_email
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class Email(object):
    def __init__(self, subject, body):
        self.subject = subject
        self.body = body

    def parsed_body(self):
        print(self.subject)
        res = process_email(self.body) or []
        if not len(res):
            print('Error for this email')
        return res


class EmailClient:
    def __init__(self, email_query=None, fetched_messages=None):
        credentials = self.fetch_credentials()
        service = build("gmail", "v1", credentials=credentials)
        self.client = service.users().messages()
        self.email_query = "subject: Alarm on nxcloud (prod) is:unread -{'re:'}"
        self.fetched_messages = 1
        if email_query:
            self.email_query = email_query

        if fetched_messages:
            self.fetched_messages = fetched_messages

    def get_email(self, id):
        return EmailClient.extract_info(self.client.get(userId="me", id=id).execute())

    def get_emails(self):
        results = self.client.list(userId="me", q=self.email_query, maxResults=self.fetched_messages).execute()
        return results.get("messages", [])

    @staticmethod
    def extract_body_from_parts(payload):
        parts = next(iter(payload.get("parts", [])), dict())
        body = next((entry.get("body") for entry in parts.get("parts", []) if entry.get("partId") == "0.1"),
                    dict()).get("data", "")
        return EmailClient.format_body(body)

    @staticmethod
    def extract_info(email):
        payload = email.get("payload", dict())
        return Email(EmailClient.extract_subject(payload), EmailClient.extract_body_from_parts(payload))

    @staticmethod
    def extract_subject(payload):
        headers = payload.get("headers", dict())
        return next(entry.get("value") for entry in headers if entry.get("name") == "Subject")

    @staticmethod
    def format_body(body):
        encoded_body = body.replace("_", "/").replace("-", "+").encode("utf8")
        decoded_body = base64.b64decode(encoded_body)
        return decoded_body.decode("utf8")

    @staticmethod
    def fetch_credentials():
        credentials = None
        token_file = f"{os.path.dirname(os.path.realpath(__file__))}/token.json"
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(token_file):
            credentials = Credentials.from_authorized_user_file(token_file, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except RefreshError:
                    pass
            if not credentials.valid:
                if os.path.exists(token_file):
                    os.remove(token_file)
                flow = InstalledAppFlow.from_client_secrets_file(
                    "client_id.json", SCOPES)
                credentials = flow.run_local_server(port=51555)
            # Save the credentials for the next run
            with open(token_file, "w") as token:
                token.write(credentials.to_json())
        return credentials


def main():
    email_client = EmailClient(fetched_messages=30)
    messages = email_client.get_emails()
    emails = []
    for message in messages:
        email = email_client.get_email(message.get("id"))
        emails.append({
            "subject": email.subject,
            "body": email.parsed_body()
        })
    return emails


if __name__ == "__main__":
    main()
