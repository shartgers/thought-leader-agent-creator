"""
Retrieves the LinkedIn person ID (URN) for the authenticated user.

Used during setup to populate LINKEDIN_PERSON_URN in .env.
Uses the OpenID Connect /v2/userinfo endpoint (the sub field is the person ID).

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

    response = requests.get(
        'https://api.linkedin.com/v2/userinfo',
        headers={'Authorization': f'Bearer {access_token}'},
    )

    if response.status_code != 200:
        print(f"ERROR: /v2/userinfo returned {response.status_code}: {response.text}")
        return None

    person_id = response.json().get('sub')
    if not person_id:
        print(f"ERROR: No 'sub' field in /v2/userinfo response: {response.json()}")
        return None

    print(f"\nYour LinkedIn Person ID: {person_id}")
    print(f"Full URN: urn:li:person:{person_id}")
    print(f"\nAdd to .env:\nLINKEDIN_PERSON_URN={person_id}")
    return person_id


if __name__ == '__main__':
    get_linkedin_id()
