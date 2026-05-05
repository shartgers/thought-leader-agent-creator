"""
LinkedIn API client for the thought leader pipeline.

Posts articles via the LinkedIn REST Posts API.
Credentials read from LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN in .env.
"""

import os
import yaml
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv('LINKEDIN_ACCESS_TOKEN')
PERSON_URN = os.getenv('LINKEDIN_PERSON_URN')
LINKEDIN_API_VERSION = os.getenv('LINKEDIN_API_VERSION', '202408')

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROFILE_PATH = os.path.join(_REPO_ROOT, 'config', 'profile.yaml')


def _get_ssl_verify():
    """Read ssl_verify from config/profile.yaml. Defaults to True (safe)."""
    try:
        with open(_PROFILE_PATH) as f:
            profile = yaml.safe_load(f) or {}
        return profile.get('ssl_verify', True)
    except Exception:
        return True


def build_post_text(title, text):
    """Combines title and body into a single LinkedIn post string."""
    title = (title or '').strip()
    text = (text or '').strip()
    if not title:
        return text
    return f"{title}\n\n{text}"


def urn_to_url(post_urn):
    """Converts a post URN to a shareable LinkedIn URL."""
    return f"https://www.linkedin.com/feed/update/{post_urn}/"


def check_connectivity():
    """
    Pre-flight check for LinkedIn API access.
    Returns False and prints actionable guidance if server IP is not allowlisted.
    """
    if not ACCESS_TOKEN:
        return True  # let post_text() surface the credential error
    ssl_verify = _get_ssl_verify()
    try:
        r = requests.get(
            'https://api.linkedin.com/v2/userinfo',
            headers={'Authorization': f'Bearer {ACCESS_TOKEN}'},
            verify=ssl_verify,
            timeout=10,
        )
        if r.status_code == 403 and 'allowlist' in r.text.lower():
            print("ERROR: This server's IP is not in your LinkedIn app's allowlist.")
            print("Fix: LinkedIn Developer Portal → your app → Auth tab → add this server's IP/domain.")
            return False
    except Exception as e:
        print(f"WARNING: LinkedIn connectivity pre-check failed: {e}")
    return True


def post_text(text):
    """
    Posts a text update to LinkedIn via the REST Posts API.

    Returns the post URN string on success (e.g. 'urn:li:share:7123456789'),
    or None on failure.
    """
    if not ACCESS_TOKEN or not PERSON_URN:
        print("ERROR: LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN not set in .env")
        return None

    ssl_verify = _get_ssl_verify()

    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json',
        'LinkedIn-Version': LINKEDIN_API_VERSION,
        'X-Restli-Protocol-Version': '2.0.0',
    }

    payload = {
        'author': f'urn:li:person:{PERSON_URN}',
        'commentary': text,
        'visibility': 'PUBLIC',
        'distribution': {
            'feedDistribution': 'MAIN_FEED',
            'targetEntities': [],
            'thirdPartyDistributionChannels': [],
        },
        'lifecycleState': 'PUBLISHED',
        'isReshareDisabledByAuthor': False,
    }

    response = requests.post(
        'https://api.linkedin.com/rest/posts',
        headers=headers,
        json=payload,
        verify=ssl_verify,
    )

    if response.status_code == 201:
        post_urn = response.headers.get('x-restli-id', '')
        print(f"  Posted: {post_urn}")
        return post_urn
    else:
        print(f"ERROR: LinkedIn API returned {response.status_code}: {response.text}")
        return None
