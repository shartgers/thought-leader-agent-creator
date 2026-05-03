"""
LinkedIn API client for the thought leader pipeline.

Posts articles via the ugcPosts v2 API.
Credentials read from LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN in .env.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv('LINKEDIN_ACCESS_TOKEN')
PERSON_URN = os.getenv('LINKEDIN_PERSON_URN')


def build_post_text(title, text):
    """Combines title and body into a single LinkedIn post string."""
    title = (title or '').strip()
    text = (text or '').strip()
    if not title:
        return text
    return f"{title}\n\n{text}"


def urn_to_url(post_urn):
    """
    Converts a ugcPost URN to a shareable LinkedIn URL.

    Example:
        'urn:li:ugcPost:7123456789' → 'https://www.linkedin.com/feed/update/urn:li:ugcPost:7123456789/'
    """
    return f"https://www.linkedin.com/feed/update/{post_urn}/"


def post_text(text):
    """
    Posts a text update to LinkedIn via the ugcPosts API.

    Returns the post URN string on success (e.g. 'urn:li:ugcPost:7123456789'),
    or None on failure.
    """
    if not ACCESS_TOKEN or not PERSON_URN:
        print("ERROR: LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN not set in .env")
        return None

    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
    }

    payload = {
        'author': f'urn:li:person:{PERSON_URN}',
        'lifecycleState': 'PUBLISHED',
        'specificContent': {
            'com.linkedin.ugc.ShareContent': {
                'shareCommentary': {'text': text},
                'shareMediaCategory': 'NONE',
            }
        },
        'visibility': {
            'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
        },
    }

    response = requests.post(
        'https://api.linkedin.com/v2/ugcPosts',
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        post_urn = response.headers.get('x-restli-id', '')
        print(f"  Posted: {post_urn}")
        return post_urn
    else:
        print(f"ERROR: LinkedIn API returned {response.status_code}: {response.text}")
        return None
