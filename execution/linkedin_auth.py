"""
LinkedIn OAuth flow helper.

Reads LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET from .env,
opens a browser for authorization, captures the code via a local
callback server, exchanges it for an access token, fetches the
person URN, and writes both to .env.

Usage (from repo root):
    python execution/linkedin_auth.py
"""

import os
import sys
import webbrowser
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv, set_key

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_REPO_ROOT, '.env')

load_dotenv(_ENV_PATH)

_auth_code = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = parse_qs(urlparse(self.path).query)
        if 'code' in params:
            _auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h2>Authorization successful! You can close this tab.</h2>')
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'<h2>Authorization failed. No code received.</h2>')

    def log_message(self, *args):
        pass


def run():
    client_id = os.getenv('LINKEDIN_CLIENT_ID')
    client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("ERROR: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env")
        sys.exit(1)

    redirect_uri = "http://localhost:8080/"
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        "?response_type=code"
        f"&client_id={client_id}"
        "&redirect_uri=http%3A%2F%2Flocalhost%3A8080%2F"
        "&scope=w_member_social"
    )

    print("Opening browser for LinkedIn authorization...")
    print(f"If the browser does not open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for callback on http://localhost:8080/ ...")
    server = HTTPServer(('localhost', 8080), _CallbackHandler)
    server.handle_request()

    if not _auth_code:
        print("ERROR: No authorization code received.")
        sys.exit(1)

    print("Exchanging authorization code for access token...")
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            'grant_type': 'authorization_code',
            'code': _auth_code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret,
        },
    )

    if resp.status_code != 200:
        print(f"ERROR: Token exchange failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    access_token = resp.json().get('access_token')
    if not access_token:
        print(f"ERROR: No access_token in response: {resp.json()}")
        sys.exit(1)

    if not os.path.exists(_ENV_PATH):
        open(_ENV_PATH, 'w').close()
    set_key(_ENV_PATH, 'LINKEDIN_ACCESS_TOKEN', access_token)
    print("LINKEDIN_ACCESS_TOKEN saved to .env")

    # Fetch person ID
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
    }
    r = requests.get('https://api.linkedin.com/v2/me', headers=headers)
    if r.status_code == 200:
        person_id = r.json().get('id')
    elif r.status_code == 403:
        r2 = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers)
        person_id = r2.json().get('sub') if r2.status_code == 200 else None
    else:
        person_id = None

    if person_id:
        set_key(_ENV_PATH, 'LINKEDIN_PERSON_URN', str(person_id))
        print(f"LINKEDIN_PERSON_URN saved to .env (ID: {person_id})")
    else:
        print("WARNING: Could not retrieve person ID. Add LINKEDIN_PERSON_URN to .env manually.")

    print("\nLinkedIn setup complete!")


if __name__ == '__main__':
    run()
