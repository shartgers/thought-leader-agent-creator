"""
LinkedIn OAuth flow for the Thought Leader Agent at Xomnia.

Reads LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET from .env,
opens a browser for the user to authorize, captures the callback code,
exchanges it for an access token, fetches the person URN,
and writes both to .env automatically.

Usage:
    python execution/linkedin_auth.py
"""

import os
import http.server
import threading
import webbrowser
import urllib.parse
import base64
import json
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv, set_key

load_dotenv()

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_REPO_ROOT, '.env')

REDIRECT_URI = "http://localhost:8080/"
SCOPE = "openid profile w_member_social"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

_auth_code = None
_server_done = threading.Event()


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if 'code' in params:
            _auth_code = params['code'][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Authorized! You can close this tab and return to Claude.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>No authorization code received. Please try again.</h2>")
        _server_done.set()

    def log_message(self, format, *args):
        pass


def _run_server():
    server = http.server.HTTPServer(('localhost', 8080), _CallbackHandler)
    server.handle_request()


def run_oauth_flow():
    client_id = os.getenv('LINKEDIN_CLIENT_ID')
    client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
    if not client_id or not client_secret:
        print("ERROR: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env")
        return False

    auth_url = (
        f"{AUTH_URL}?response_type=code"
        f"&client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&scope={urllib.parse.quote(SCOPE)}"
    )

    print("Starting local callback server on port 8080...")
    threading.Thread(target=_run_server, daemon=True).start()

    print("\nOpening browser for LinkedIn authorization...")
    print(f"If the browser does not open automatically, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    _server_done.wait(timeout=120)

    if not _auth_code:
        print("ERROR: Timed out waiting for authorization. Please try again.")
        return False

    print("Authorization code received. Exchanging for access token...")

    response = requests.post(TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': _auth_code,
        'redirect_uri': REDIRECT_URI,
        'client_id': client_id,
        'client_secret': client_secret,
    })

    if response.status_code != 200:
        print(f"ERROR: Token exchange failed ({response.status_code}): {response.text}")
        return False

    token_data = response.json()
    access_token = token_data.get('access_token')
    if not access_token:
        print("ERROR: No access_token in LinkedIn response.")
        return False

    set_key(_ENV_PATH, 'LINKEDIN_ACCESS_TOKEN', access_token)
    print("LINKEDIN_ACCESS_TOKEN saved to .env")

    # Extract person ID from id_token JWT (requires openid + profile scope)
    person_id = None
    id_token = token_data.get('id_token')
    if id_token:
        payload = id_token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        person_id = claims.get('sub')

    # Fallback: userinfo endpoint
    if not person_id:
        r = requests.get(
            'https://api.linkedin.com/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
        )
        if r.status_code == 200:
            person_id = r.json().get('sub')

    if person_id:
        set_key(_ENV_PATH, 'LINKEDIN_PERSON_URN', str(person_id))
        print(f"LINKEDIN_PERSON_URN={person_id} saved to .env")
    else:
        print("WARNING: Could not fetch person ID. Add LINKEDIN_PERSON_URN to .env manually.")

    print("\nLinkedIn credentials configured successfully!")
    return True


if __name__ == '__main__':
    run_oauth_flow()
