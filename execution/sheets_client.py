"""
Google Sheets client for the LinkedIn thought leader pipeline.

Provides CRUD operations against a single Google Sheet.
Sheet ID is read from GOOGLE_SHEET_ID in .env.
Tab name: "LinkedIn Posts"
"""

import os
from datetime import datetime, date
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('GOOGLE_SHEET_ID')
OAUTH_PORT = int(os.getenv('GOOGLE_OAUTH_PORT', '8080'))

POSTS_COLUMNS = [
    'source', 'about', 'title', 'text', 'image_prompt', 'status',
    'scheduled_date', 'date_added', 'date_textgen', 'published_url', 'date_posted',
]


def get_service():
    """Authenticates and returns a Google Sheets API service instance."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                print("WARNING: OAuth token expired. Re-authenticating.")
                os.remove('token.json')
                creds = None

        if not creds or not creds.valid:
            if not os.path.exists('credentials.json'):
                print("ERROR: credentials.json not found. Run setup skill first.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=OAUTH_PORT, prompt='consent', open_browser=False)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
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
                col_letter = chr(ord('A') + col_idx)
                data.append({
                    'range': f"'{tab_name}'!{col_letter}{row_number}",
                    'values': [[value]]
                })

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
    today = date.today().isoformat()
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
    from datetime import timedelta
    today = date.today()
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
        from datetime import timedelta
        rows = get_rows('LinkedIn Posts')
        for row in rows:
            existing = row.get('scheduled_date', '').strip()
            if existing and existing >= target_date and row['_row_number'] != row_number:
                new_date = (date.fromisoformat(existing) + timedelta(days=1)).isoformat()
                update_row('LinkedIn Posts', row['_row_number'], {'scheduled_date': new_date})

    return update_row('LinkedIn Posts', row_number, {'scheduled_date': target_date})


if __name__ == '__main__':
    print("Testing Google Sheets connection...")
    rows = get_rows('LinkedIn Posts')
    print(f"Found {len(rows)} rows in LinkedIn Posts tab.")
