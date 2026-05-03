"""
Retrieves the LinkedIn person ID (URN) for the authenticated user.

Used during setup to populate LINKEDIN_PERSON_URN in .env.
Tries /v2/me first; falls back to /v2/userinfo if permissions are restricted.

Usage:
    python execution/get_linkedin_id.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def get_linkedin_id():
    access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
    if not access_token:
        print("ERROR: LINKEDIN_ACCESS_TOKEN not found in .env")
        return None

    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
    }

    response = requests.get('https://api.linkedin.com/v2/me', headers=headers)
    if response.status_code == 200:
        person_id = response.json().get('id')
    elif response.status_code == 403:
        print("  /v2/me returned 403, trying /v2/userinfo...")
        response2 = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers)
        if response2.status_code == 200:
            person_id = response2.json().get('sub')
        else:
            print(f"ERROR: Both endpoints failed. /v2/userinfo: {response2.status_code}")
            return None
    else:
        print(f"ERROR: /v2/me returned {response.status_code}: {response.text}")
        return None

    print(f"\nYour LinkedIn Person ID: {person_id}")
    print(f"Full URN: urn:li:person:{person_id}")
    print(f"\nAdd to .env:\nLINKEDIN_PERSON_URN={person_id}")
    return person_id


if __name__ == '__main__':
    get_linkedin_id()
