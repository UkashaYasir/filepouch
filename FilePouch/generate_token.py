from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Fetch account email
oauth2_service = build('oauth2', 'v2', credentials=creds)
user_info = oauth2_service.userinfo().get().execute()

creds_data = json.loads(creds.to_json())
creds_data['account'] = user_info.get('email', '')

with open('token.json', 'w') as token_file:
    json.dump(creds_data, token_file, indent=2)

print(f"✅ Token saved for account: {creds_data['account']}")
