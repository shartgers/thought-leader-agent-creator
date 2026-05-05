"""
Google Sheets client for the LinkedIn thought leader pipeline.

Provides CRUD operations against a single Google Sheet.
Sheet ID is read from GOOGLE_SHEET_ID in .env.
Tab name: "LinkedIn Posts"
"""

import os
import yaml
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import requests as _requests
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

_TZ = ZoneInfo('Europe/Amsterdam')
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOKEN_PATH = os.path.join(_REPO_ROOT, 'token.json')
_CREDENTIALS_PATH = os.path.join(_REPO_ROOT, 'credentials.json')
_PROFILE_PATH = os.path.join(_REPO_ROOT, 'config', 'profile.yaml')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('GOOGLE_SHEET_ID')
OAUTH_PORT = int(os.getenv('GOOGLE_OAUTH_PORT', '8080'))

POSTS_COLUMNS = [
    'source', 'about', 'title', 'text', 'image_prompt', 'status',
    'scheduled_date', 'date_added', 'date_textgen', 'published_url', 'date_posted',
]


def _get_ssl_verify():
    """Read ssl_verify from config/profile.yaml. Defaults to True (safe)."""
    try:
        with open(_PROFILE_PATH) as f:
            profile = yaml.safe_load(f) or {}
        return profile.get('ssl_verify', True)
    except Exception:
        return True


def _col_index_to_letter(n):
    """Convert a 0-based column index to a spreadsheet column letter (A, B, ..., Z, AA, AB, ...)."""
    result = ''
    while True:
        result = chr(ord('A') + n % 26) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result


def get_service():
    """Authenticates and returns a Google Sheets API service instance."""
    ssl_verify = _get_ssl_verify()
    creds = None
    if os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                if not ssl_verify:
                    session = _requests.Session()
                    session.verify = False
                    creds.refresh(Request(session=session))
                else:
                    creds.refresh(Request())
            except RefreshError:
                print("WARNING: OAuth token expired. Re-authenticating.")
                os.remove(_TOKEN_PATH)
                creds = None

        if not creds or not creds.valid:
            if not os.path.exists(_CREDENTIALS_PATH):
                print("ERROR: credentials.json not found. Run setup skill first.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=OAUTH_PORT, prompt='consent', open_browser=True)

        with open(_TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    try:
        if not ssl_verify:
            import httplib2
            from google_auth_httplib2 import AuthorizedHttp
            _http = httplib2.Http(disable_ssl_certificate_validation=True)
            _http_auth = AuthorizedHttp(creds, http=_http)
            return build('sheets', 'v4', http=_http_auth)
        return build('sheets', 'v4', credentials=creds)
    except HttpError as err:
        print(f"ERROR: Failed to build Sheets service: {err}")
        return None


def get_rows(tab_name, status_filter=None):
    """
    Reads all rows from a tab, optionally filtered by status.
    Returns list of dicts with column names as keys + '_row_number'.
    """
    service = get_service()
    if not service:
        return []

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{tab_name}'!A:Z"
        ).execute()
    except HttpError as err:
        print(f"ERROR: get_rows failed: {err}")
        return []

    values = result.get('values', [])
    if not values:
        return []

    header = values[0]
    rows = []
    for i, row in enumerate(values[1:], start=2):
        padded = row + [''] * (len(header) - len(row))
        row_dict = {header[j]: padded[j] for j in range(len(header))}
        row_dict['_row_number'] = i
        if status_filter:
            if row_dict.get('status', '').strip().lower() == status_filter.strip().lower():
                rows.append(row_dict)
        else:
            rows.append(row_dict)

    return rows


def append_to_sheet(tab_name, values):
    """Appends rows to a tab. Returns number of cells appended."""
    service = get_service()
    if not service:
        return 0

    try:
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{tab_name}'!A:Z",
            valueInputOption='USER_ENTERED',
            body={'values': values}
        ).execute()
        return result.get('updates', {}).get('updatedCells', 0)
    except HttpError as err:
        print(f"ERROR: append_to_sheet failed: {err}")
        return 0


def append_idea(about, source, status='new'):
    """Appends a new idea row to the LinkedIn Posts tab."""
    date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = []
    for col in POSTS_COLUMNS:
        if col == 'source':
            row.append(source)
        elif col == 'about':
            row.append(about)
        elif col == 'status':
            row.append(status)
        elif col == 'date_added':
            row.append(date_added)
        else:
            row.append('')
    return append_to_sheet('LinkedIn Posts', [row])


def update_row(tab_name, row_number, updates):
    """
    Updates specific columns in a row.

    Args:
        tab_name: Tab name string
        row_number: 1-indexed row number (as returned in _row_number)
        updates: Dict of {column_name: new_value}

    Returns True on success, False on failure.
    """
    service = get_service()
    if not service:
        return False

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{tab_name}'!1:1"
        ).execute()
        header = result.get('values', [[]])[0]

        data = []
        for col_name, value in updates.items():
            if col_name in header:
                col_idx = header.index(col_name)
                col_letter = _col_index_to_letter(col_idx)
                data.append({
                    'range': f"'{tab_name}'!{col_letter}{row_number}",
                    'values': [[value]]
                })
            else:
                print(f"WARNING: Column '{col_name}' not found in {tab_name} header. Skipping.")

        if data:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'valueInputOption': 'USER_ENTERED', 'data': data}
            ).execute()
        return True

    except HttpError as err:
        print(f"ERROR: update_row failed: {err}")
        return False


def get_today_scheduled_post():
    """
    Returns the single row with scheduled_date == today and status == 'ready'.
    Returns None if no such row exists.
    """
    today = datetime.now(_TZ).date().isoformat()
    rows = get_rows('LinkedIn Posts', status_filter='ready')
    for row in rows:
        if row.get('scheduled_date', '').strip() == today:
            return row
    return None


def get_schedule(days=14):
    """
    Returns (schedule_slots, unscheduled_ready) for the next N days.
    schedule_slots: list of {date, weekday, post} dicts
    unscheduled_ready: list of ready rows with no scheduled_date
    """
    today = datetime.now(_TZ).date()
    rows = get_rows('LinkedIn Posts')

    scheduled_by_date = {}
    unscheduled_ready = []

    for row in rows:
        status = row.get('status', '').strip().lower()
        sdate = row.get('scheduled_date', '').strip()
        if status == 'ready':
            if sdate:
                scheduled_by_date[sdate] = row
            else:
                unscheduled_ready.append(row)

    slots = []
    for i in range(days):
        d = today + timedelta(days=i)
        d_str = d.isoformat()
        slots.append({
            'date': d_str,
            'weekday': d.strftime('%A'),
            'post': scheduled_by_date.get(d_str),
        })

    return slots, unscheduled_ready


def set_scheduled_date(row_number, target_date, shift=False):
    """
    Sets or clears the scheduled_date for a row.
    If shift=True, bumps all later-scheduled posts forward by one day.
    """
    if shift and target_date:
        rows = get_rows('LinkedIn Posts')
        conflicting = sorted(
            [r for r in rows
             if r.get('scheduled_date', '').strip() >= target_date
             and r['_row_number'] != row_number
             and r.get('scheduled_date', '').strip()],
            key=lambda r: r['scheduled_date'],
            reverse=True
        )
        for row in conflicting:
            existing = row['scheduled_date'].strip()
            new_date = (date.fromisoformat(existing) + timedelta(days=1)).isoformat()
            update_row('LinkedIn Posts', row['_row_number'], {'scheduled_date': new_date})

    return update_row('LinkedIn Posts', row_number, {'scheduled_date': target_date})


if __name__ == '__main__':
    print("Testing Google Sheets connection...")
    rows = get_rows('LinkedIn Posts')
    print(f"Found {len(rows)} rows in LinkedIn Posts tab.")
