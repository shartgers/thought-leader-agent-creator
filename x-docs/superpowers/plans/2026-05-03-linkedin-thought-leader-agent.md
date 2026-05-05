# LinkedIn Thought Leader Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable, skills-based LinkedIn content pipeline that any colleague can clone, configure once, and use to consistently publish thought leadership articles.

**Architecture:** Five Claude skills (setup, capture-ideas, create-articles, post-article, schedule) act as orchestration entry points, each calling deterministic Python execution scripts. Google Sheets is the central database with a `new → review → ready → posted` status workflow. Scheduled autonomous publishing uses Claude's `CronCreate` routine (no GitHub Actions).

**Tech Stack:** Python 3.11+, `anthropic` SDK, `google-api-python-client`, `google-auth-oauthlib`, `requests`, `python-dotenv`, `pytest`, `pyyaml`

**Spec:** `docs/superpowers/specs/2026-05-03-linkedin-thought-leader-agent-design.md`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `execution/sheets_client.py` | Create | Google Sheets CRUD — all sheet operations |
| `execution/linkedin_client.py` | Create | LinkedIn ugcPosts API wrapper + URN→URL |
| `execution/llm_content_gen.py` | Create | Claude API draft generation (parameterized) |
| `execution/publish_today.py` | Create | Standalone cron script — publish today's post |
| `execution/get_linkedin_id.py` | Create | Retrieve LinkedIn person URN during setup |
| `execution/__init__.py` | Create | Package marker |
| `config/brand_voice.md` | Create | Default LinkedIn writing style template |
| `config/themes.yaml` | Create | Placeholder themes (written by setup skill) |
| `config/profile.yaml` | Create | Placeholder profile (written by setup skill) |
| `skills/setup.md` | Create | Onboarding skill |
| `skills/capture-ideas.md` | Create | Idea intake skill |
| `skills/create-articles.md` | Create | Draft generation skill |
| `skills/post-article.md` | Create | Publish to LinkedIn skill |
| `skills/schedule.md` | Create | Schedule + CronCreate skill |
| `tests/conftest.py` | Create | Shared pytest fixtures |
| `tests/test_sheets_client.py` | Create | Unit tests for sheets_client |
| `tests/test_linkedin_client.py` | Create | Unit tests for linkedin_client |
| `tests/test_llm_content_gen.py` | Create | Unit tests for llm_content_gen |
| `tests/test_publish_today.py` | Create | Integration test for publish_today |
| `.env.example` | Create | Credential template |
| `requirements.txt` | Create | Python dependencies |
| `CLAUDE.md` | Create | Project instructions for Claude |
| `README.md` | Create | Colleague-facing quickstart |

---

## Task 1: Repo Scaffolding

**Files:**
- Create: `execution/__init__.py`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `CLAUDE.md`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p execution config skills tests logs .tmp/images
touch execution/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `.env.example`**

```
# Google Sheets
GOOGLE_SHEET_ID=                    # from sheet URL: .../spreadsheets/d/<ID>/edit
GOOGLE_OAUTH_PORT=8080              # port for local OAuth redirect
# credentials.json and token.json are expected in the repo root (standard paths, not configurable)

# LinkedIn API
LINKEDIN_ACCESS_TOKEN=              # from OAuth flow (see setup skill)
LINKEDIN_PERSON_URN=                # numeric ID only, e.g. 12345678

# Claude API (for draft generation)
CLAUDE_API_KEY=                     # from console.anthropic.com
```

- [ ] **Step 3: Write `requirements.txt`**

```
anthropic>=0.25.0
google-api-python-client>=2.0.0
google-auth-httplib2>=0.2.0
google-auth-oauthlib>=1.0.0
python-dotenv>=1.0.0
requests>=2.31.0
pyyaml>=6.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 4: Write `CLAUDE.md`**

```markdown
# LinkedIn Thought Leader Agent

This repo helps you consistently publish LinkedIn thought leadership articles.
It uses Claude skills + Python execution scripts + Google Sheets.

## First time? Run the setup skill

Invoke: `/setup`

The setup skill guides you through configuring your profile, 3 content themes,
Google Sheets connection, and LinkedIn credentials.

## Available Skills

| Skill | How to invoke | What it does |
|-------|---------------|--------------|
| `setup` | `/setup` | One-time onboarding: role, themes, credentials, sheet |
| `capture-ideas` | `/capture-ideas` | Add ideas (paste a list) → Google Sheet |
| `create-articles` | `/create-articles` | Generate LinkedIn drafts from new ideas |
| `post-article` | `/post-article` | Publish a ready article to LinkedIn |
| `schedule` | `/schedule` | Schedule ready articles + set up daily auto-post |

Skills are defined in `skills/`. To invoke one, type `/skill-name` or ask Claude
to use it by name.

## Workflow

```
capture-ideas → create-articles → [review in sheet] → schedule or post-article
```

The `review → ready` status change in Google Sheets is intentionally manual.
Never automate this step.

## Execution Scripts

Python scripts in `execution/` are the deterministic layer. Skills call them.
Do not modify them to bypass workflow gates.

## Config

- `config/brand_voice.md` — your LinkedIn writing style (edit freely)
- `config/themes.yaml` — your 3 content themes (set during setup)
- `config/profile.yaml` — your name, role, LinkedIn URN (set during setup)

## Status Workflow

`new → review → ready → posted`

- `new`: idea captured, not yet drafted
- `review`: draft generated, awaiting your approval in the sheet
- `ready`: you approved it — eligible for scheduling and posting
- `posted`: published to LinkedIn
```

- [ ] **Step 5: Commit**

```bash
git add execution/__init__.py .env.example requirements.txt CLAUDE.md
git commit -m "chore: scaffold repo structure and project config"
```

---

## Task 2: `sheets_client.py`

**Files:**
- Create: `execution/sheets_client.py`
- Create: `tests/conftest.py`
- Create: `tests/test_sheets_client.py`

This is ported from the proven original. Key changes: `POSTS_COLUMNS` now includes `scheduled_date`; `get_today_scheduled_post()` is added; module-level `SPREADSHEET_ID` reads from `.env`.

- [ ] **Step 1: Write failing tests**

Create `tests/conftest.py`:
```python
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_sheets_service():
    with patch('execution.sheets_client.get_service') as mock_get:
        svc = MagicMock()
        mock_get.return_value = svc
        yield svc
```

Create `tests/test_sheets_client.py`:
```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from execution import sheets_client


def test_get_rows_returns_dicts_with_row_number(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'title', 'text', 'image_prompt', 'status',
             'scheduled_date', 'date_added', 'date_textgen', 'published_url', 'date_posted'],
            ['Manual', 'AI idea', '', '', '', 'new', '', '2026-01-01', '', '', ''],
        ]
    }
    rows = sheets_client.get_rows('LinkedIn Posts')
    assert len(rows) == 1
    assert rows[0]['about'] == 'AI idea'
    assert rows[0]['_row_number'] == 2


def test_get_rows_status_filter(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'status'],
            ['Manual', 'idea1', 'new'],
            ['Manual', 'idea2', 'ready'],
        ]
    }
    rows = sheets_client.get_rows('LinkedIn Posts', status_filter='new')
    assert len(rows) == 1
    assert rows[0]['about'] == 'idea1'


def test_get_rows_status_filter_case_insensitive(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'status'],
            ['Manual', 'idea1', 'Ready'],
        ]
    }
    rows = sheets_client.get_rows('LinkedIn Posts', status_filter='ready')
    assert len(rows) == 1


def test_append_idea_builds_correct_row(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().append().execute.return_value = {
        'updates': {'updatedCells': 11}
    }
    result = sheets_client.append_idea('Test idea', 'Manual', status='new')
    assert result > 0
    call_args = mock_sheets_service.spreadsheets().values().append.call_args
    body = call_args.kwargs['body']
    row = body['values'][0]
    assert 'Test idea' in row
    assert 'Manual' in row
    assert 'new' in row


def test_update_row_calls_batch_update(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [['source', 'about', 'status']]
    }
    mock_sheets_service.spreadsheets().values().batchUpdate().execute.return_value = {}
    result = sheets_client.update_row('LinkedIn Posts', 2, {'status': 'review'})
    assert result is True


def test_get_today_scheduled_post_returns_matching_row(mock_sheets_service):
    today = date.today().isoformat()
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'title', 'text', 'image_prompt', 'status',
             'scheduled_date', 'date_added', 'date_textgen', 'published_url', 'date_posted'],
            ['Manual', 'idea', 'Title', 'Post text', '', 'ready', today, '', '', '', ''],
        ]
    }
    post = sheets_client.get_today_scheduled_post()
    assert post is not None
    assert post['title'] == 'Title'


def test_get_today_scheduled_post_returns_none_when_no_match(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'status', 'scheduled_date'],
            ['Manual', 'idea', 'ready', '2020-01-01'],
        ]
    }
    post = sheets_client.get_today_scheduled_post()
    assert post is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_sheets_client.py -v
```
Expected: `ModuleNotFoundError` or `ImportError` — `sheets_client` not yet written.

- [ ] **Step 3: Write `execution/sheets_client.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_sheets_client.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add execution/sheets_client.py tests/conftest.py tests/test_sheets_client.py
git commit -m "feat: add sheets_client with CRUD operations and schedule helpers"
```

---

## Task 3: `linkedin_client.py`

**Files:**
- Create: `execution/linkedin_client.py`
- Create: `tests/test_linkedin_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_linkedin_client.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from execution import linkedin_client


def test_build_post_text_with_title():
    result = linkedin_client.build_post_text('My Title', 'Post body here.')
    assert result == 'My Title\n\nPost body here.'


def test_build_post_text_no_title():
    result = linkedin_client.build_post_text('', 'Just the body.')
    assert result == 'Just the body.'


def test_urn_to_url():
    urn = 'urn:li:ugcPost:7123456789'
    url = linkedin_client.urn_to_url(urn)
    assert url == 'https://www.linkedin.com/feed/update/urn:li:ugcPost:7123456789/'


def test_post_text_success():
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {'x-restli-id': 'urn:li:ugcPost:9999'}

    with patch('execution.linkedin_client.requests.post', return_value=mock_response):
        result = linkedin_client.post_text('Hello LinkedIn!')
    assert result == 'urn:li:ugcPost:9999'


def test_post_text_failure_returns_none():
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = 'Unauthorized'

    with patch('execution.linkedin_client.requests.post', return_value=mock_response):
        result = linkedin_client.post_text('Hello LinkedIn!')
    assert result is None


def test_post_text_missing_token(monkeypatch):
    monkeypatch.setenv('LINKEDIN_ACCESS_TOKEN', '')
    # Re-import to pick up empty token
    import importlib
    import execution.linkedin_client as lc
    importlib.reload(lc)
    result = lc.post_text('test')
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_linkedin_client.py -v
```
Expected: FAIL — `linkedin_client` not yet written.

- [ ] **Step 3: Write `execution/linkedin_client.py`**

```python
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
        # LinkedIn returns the post URN in the x-restli-id header
        post_urn = response.headers.get('x-restli-id', '')
        print(f"  Posted: {post_urn}")
        return post_urn
    else:
        print(f"ERROR: LinkedIn API returned {response.status_code}: {response.text}")
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_linkedin_client.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add execution/linkedin_client.py tests/test_linkedin_client.py
git commit -m "feat: add linkedin_client with post_text and urn_to_url"
```

---

## Task 4: `llm_content_gen.py`

**Files:**
- Create: `execution/llm_content_gen.py`
- Create: `tests/test_llm_content_gen.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_llm_content_gen.py`:
```python
import json
import pytest
from unittest.mock import MagicMock, patch
from execution import llm_content_gen

SAMPLE_BRAND_VOICE = "Write concisely. No fluff. Use short sentences."
SAMPLE_THEMES = "1. AI in operations\n2. Leadership lessons\n3. Digital transformation"
SAMPLE_ROLE = "Operations Director"
SAMPLE_ABOUT = "How AI is changing supply chain management"

VALID_RESPONSE = json.dumps({
    "title": "AI Is Rewriting the Supply Chain",
    "text": "Five years ago, predicting demand meant gut feel and spreadsheets.\n\nToday, AI models do it in seconds.\n\nWhat does that mean for operations leaders?",
    "image_prompt": "Futuristic warehouse with robotic arms and digital overlays"
})


def test_generate_draft_returns_expected_fields():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=VALID_RESPONSE)]
    )
    with patch('execution.llm_content_gen.anthropic.Anthropic', return_value=mock_client):
        result = llm_content_gen.generate_draft(
            SAMPLE_ABOUT, SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE
        )
    assert 'title' in result
    assert 'text' in result
    assert 'image_prompt' in result
    assert result['title'] == "AI Is Rewriting the Supply Chain"


def test_generate_draft_retries_on_json_parse_failure():
    bad_response = "Here is your post: some plain text without JSON"
    good_response = VALID_RESPONSE

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        MagicMock(content=[MagicMock(text=bad_response)]),
        MagicMock(content=[MagicMock(text=good_response)]),
    ]
    with patch('execution.llm_content_gen.anthropic.Anthropic', return_value=mock_client):
        result = llm_content_gen.generate_draft(
            SAMPLE_ABOUT, SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE
        )
    assert result['title'] == "AI Is Rewriting the Supply Chain"
    assert mock_client.messages.create.call_count == 2


def test_generate_draft_raises_after_two_failures():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="not json at all")]
    )
    with patch('execution.llm_content_gen.anthropic.Anthropic', return_value=mock_client):
        with pytest.raises(ValueError, match="Failed to parse"):
            llm_content_gen.generate_draft(
                SAMPLE_ABOUT, SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE
            )


def test_build_system_prompt_includes_role_and_voice():
    prompt = llm_content_gen._build_system_prompt(SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE)
    assert SAMPLE_ROLE in prompt
    assert SAMPLE_BRAND_VOICE in prompt
    assert SAMPLE_THEMES in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_llm_content_gen.py -v
```
Expected: FAIL — module not yet written.

- [ ] **Step 3: Write `execution/llm_content_gen.py`**

```python
"""
LLM content generator for LinkedIn thought leader pipeline.

Generates LinkedIn article drafts using the Anthropic Claude API.
All context (brand voice, themes, role) passed as parameters — no hardcoded prompts.
"""

import json
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
MODEL = 'claude-sonnet-4-6'


def _build_system_prompt(brand_voice, themes, role):
    """Builds the system prompt from config parameters."""
    return f"""You are a LinkedIn ghostwriter for a {role}.

Write in this voice and style:
{brand_voice}

The author publishes consistently around these 3 themes. Each article must align with one of them:
{themes}

Rules:
- 150-300 words
- Open with a hook (do NOT start with "I" or "In today's world")
- One clear insight or lesson per article
- Close with a question or call to action
- No generic AI filler. No marketing fluff.
- Output valid JSON only, no other text: {{"title": "...", "text": "...", "image_prompt": "..."}}"""


def _parse_response(text):
    """
    Extracts JSON from model response.
    Handles responses where the model wraps JSON in markdown code fences.
    Returns dict or raises ValueError.
    """
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith('```'):
        lines = text.splitlines()
        text = '\n'.join(lines[1:-1]) if lines[-1].strip() == '```' else '\n'.join(lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model response: {e}\nResponse: {text[:200]}")


def generate_draft(about, brand_voice, themes, role):
    """
    Generates a LinkedIn article draft for the given idea.

    Args:
        about: The idea or topic to write about
        brand_voice: Contents of config/brand_voice.md
        themes: Formatted string of 3 content themes
        role: The author's professional role

    Returns:
        Dict with keys: title, text, image_prompt

    Raises:
        ValueError: If the model fails to return valid JSON after 2 attempts
    """
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    system_prompt = _build_system_prompt(brand_voice, themes, role)
    user_message = f"Write a LinkedIn article about this idea: {about}"

    for attempt in range(2):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_message}]
        )
        try:
            return _parse_response(response.content[0].text)
        except ValueError:
            if attempt == 1:
                raise
            print(f"  WARNING: JSON parse failed on attempt 1, retrying...")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_llm_content_gen.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add execution/llm_content_gen.py tests/test_llm_content_gen.py
git commit -m "feat: add llm_content_gen with parameterized prompt and retry logic"
```

---

## Task 5: `get_linkedin_id.py`

**Files:**
- Create: `execution/get_linkedin_id.py`

No unit tests for this utility — it's a thin API wrapper used interactively during setup.

- [ ] **Step 1: Write `execution/get_linkedin_id.py`**

```python
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

    # Try primary endpoint
    response = requests.get('https://api.linkedin.com/v2/me', headers=headers)
    if response.status_code == 200:
        person_id = response.json().get('id')
    elif response.status_code == 403:
        # Fall back to userinfo (OpenID Connect)
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
```

- [ ] **Step 2: Commit**

```bash
git add execution/get_linkedin_id.py
git commit -m "feat: add get_linkedin_id utility for setup onboarding"
```

---

## Task 6: `publish_today.py`

**Files:**
- Create: `execution/publish_today.py`
- Create: `tests/test_publish_today.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_publish_today.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from datetime import date


def _make_post(row_number=2, title='Test Title', text='Post body.', scheduled_date=None):
    return {
        '_row_number': row_number,
        'title': title,
        'text': text,
        'image_prompt': '',
        'status': 'ready',
        'scheduled_date': scheduled_date or date.today().isoformat(),
    }


def test_publish_today_posts_and_updates_sheet():
    post = _make_post()
    with patch('execution.publish_today.get_today_scheduled_post', return_value=post), \
         patch('execution.publish_today.post_text', return_value='urn:li:ugcPost:999') as mock_post, \
         patch('execution.publish_today.update_row') as mock_update, \
         patch('execution.publish_today.urn_to_url', return_value='https://linkedin.com/feed/update/urn:li:ugcPost:999/'):
        from execution.publish_today import publish_today
        result = publish_today()
    assert result is True
    mock_post.assert_called_once()
    mock_update.assert_called_once()
    update_args = mock_update.call_args[0]
    assert update_args[2]['status'] == 'posted'
    assert 'published_url' in update_args[2]


def test_publish_today_exits_cleanly_when_no_post():
    with patch('execution.publish_today.get_today_scheduled_post', return_value=None):
        from execution.publish_today import publish_today
        result = publish_today()
    assert result is True


def test_publish_today_returns_false_on_api_failure():
    post = _make_post()
    with patch('execution.publish_today.get_today_scheduled_post', return_value=post), \
         patch('execution.publish_today.post_text', return_value=None):
        from execution.publish_today import publish_today
        result = publish_today()
    assert result is False


def test_publish_today_dry_run_does_not_call_api():
    post = _make_post()
    with patch('execution.publish_today.get_today_scheduled_post', return_value=post), \
         patch('execution.publish_today.post_text') as mock_post:
        from execution.publish_today import publish_today
        result = publish_today(dry_run=True)
    assert result is True
    mock_post.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_publish_today.py -v
```
Expected: FAIL — module not yet written.

- [ ] **Step 3: Write `execution/publish_today.py`**

```python
"""
publish_today.py — Publish today's scheduled LinkedIn post.

Called by the Claude CronCreate daily routine at 08:15 Europe/Amsterdam.
Finds the single post with status=ready and scheduled_date=today.
Publishes it and updates the sheet. Exits cleanly if nothing is scheduled.

Usage:
    python execution/publish_today.py [--dry-run]
"""

import sys
import argparse
from datetime import datetime, date

sys.path.insert(0, '.')

from execution.sheets_client import get_today_scheduled_post, update_row
from execution.linkedin_client import post_text, build_post_text, urn_to_url


def publish_today(dry_run=False):
    now = datetime.now()
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] publish_today starting")
    print(f"  Date : {date.today().isoformat()}")
    print(f"  Mode : {'DRY RUN' if dry_run else 'LIVE'}")

    post = get_today_scheduled_post()

    if not post:
        print("  Result: No post scheduled for today. Nothing to publish.")
        return True

    row_number = post['_row_number']
    title = post.get('title', '(no title)')
    text = post.get('text', '')

    print(f"  Post  : Row {row_number} — {title[:60]}")

    if not text:
        print("  Error : Post has no text content. Aborting.")
        return False

    full_text = build_post_text(title, text)

    if dry_run:
        print(f"  [DRY RUN] Would publish: {full_text[:200]}...")
        return True

    post_urn = post_text(full_text)

    if post_urn:
        published_url = urn_to_url(post_urn)
        update_row('LinkedIn Posts', row_number, {
            'status': 'posted',
            'date_posted': now.strftime('%Y-%m-%d %H:%M:%S'),
            'published_url': published_url,
        })
        print(f"  Result: Published — {published_url}")
        return True
    else:
        print("  Result: FAILED — LinkedIn API error. Row stays 'ready' for retry.")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Publish today's scheduled LinkedIn post")
    parser.add_argument('--dry-run', action='store_true', help='Simulate without posting')
    args = parser.parse_args()
    success = publish_today(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_publish_today.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add execution/publish_today.py tests/test_publish_today.py
git commit -m "feat: add publish_today with urn_to_url integration and dry-run support"
```

---

## Task 7: Config Templates

**Files:**
- Create: `config/brand_voice.md`
- Create: `config/themes.yaml`
- Create: `config/profile.yaml`

These are the default templates. `setup` skill overwrites `themes.yaml` and `profile.yaml` during onboarding. `brand_voice.md` is a template the colleague edits directly.

- [ ] **Step 1: Write `config/brand_voice.md`**

```markdown
# Brand Voice — LinkedIn Writing Style

This file defines how your LinkedIn articles should sound. Edit it to match your personal style.
The create-articles skill injects this entire file into the article generation prompt.

---

## Voice in one line

[Replace this with your own: e.g. "Pragmatic and direct — like advice from a trusted peer, not a consultant."]

---

## Tone

- Direct and confident. Say what you mean.
- Conversational but professional. Write like you speak, not like a press release.
- Avoid buzzwords: "synergy", "leverage", "disrupt", "game-changing".

## Structure

- Open with a hook — a surprising fact, a short story, or a provocative question.
- One main point per article. Don't try to say everything.
- Use short paragraphs (1-3 sentences). LinkedIn readers scroll fast.
- End with a question or clear call to action.

## What to avoid

- Starting with "I" or "In today's world"
- Lists of 5+ bullet points (write in prose)
- Marketing fluff or generic AI-sounding sentences
- Hedging: "might", "could potentially", "in some ways"

---

*Edit this file to match your voice. The more specific you are, the better your drafts will be.*
```

- [ ] **Step 2: Write `config/themes.yaml`**

```yaml
# Content themes — set by the setup skill during onboarding.
# Edit directly or re-run /setup to update.
themes:
  - name: "Theme 1"
    description: "Replace with your first content theme"
  - name: "Theme 2"
    description: "Replace with your second content theme"
  - name: "Theme 3"
    description: "Replace with your third content theme"
```

- [ ] **Step 3: Write `config/profile.yaml`**

```yaml
# Your profile — set by the setup skill during onboarding.
# Edit directly or re-run /setup to update.
name: ""
role: ""
company: ""
industry: ""
linkedin_urn: ""        # numeric person ID (e.g. 12345678), NOT the full URN
preferred_post_time: "08:30"
timezone: "Europe/Amsterdam"
```

- [ ] **Step 4: Commit**

```bash
git add config/brand_voice.md config/themes.yaml config/profile.yaml
git commit -m "feat: add default config templates for brand voice, themes, and profile"
```

---

## Task 8: `skills/setup.md`

**Files:**
- Create: `skills/setup.md`

- [ ] **Step 1: Write `skills/setup.md`**

```markdown
---
name: setup
description: One-time onboarding for the LinkedIn thought leader agent. Configures profile, content themes, Google Sheets, and LinkedIn credentials. Run once per colleague, or re-run to update config.
---

# Setup — LinkedIn Thought Leader Agent

Guide the colleague through full onboarding. Follow every step in order. Do not skip steps.

## Step 1: Welcome

Introduce yourself briefly:
> "Welcome to the LinkedIn Thought Leader Agent. I'll walk you through setup — it takes about 10 minutes. By the end, you'll have your profile configured, 3 content themes locked in, and your Google Sheet and LinkedIn account connected."

## Step 2: Collect Profile Info

Ask for:
1. Full name
2. Job title / role
3. Company name
4. Industry

Write these to `config/profile.yaml`:
```yaml
name: "<name>"
role: "<role>"
company: "<company>"
industry: "<industry>"
linkedin_urn: ""
preferred_post_time: "08:30"
timezone: "Europe/Amsterdam"
```

## Step 3: Define 3 Content Themes

Explain:
> "Consistent thought leaders own 2-3 specific topics. I'll suggest themes based on your role and industry — you refine them."

Suggest 3 themes based on their role/industry. For example:
- Operations leader → "AI in supply chain", "Leadership under pressure", "Digital transformation lessons"
- HR director → "Future of work", "Building high-performance teams", "People analytics"

Agree on 3 themes with the colleague, then write to `config/themes.yaml`:
```yaml
themes:
  - name: "<Theme 1>"
    description: "<1-2 sentence description>"
  - name: "<Theme 2>"
    description: "<1-2 sentence description>"
  - name: "<Theme 3>"
    description: "<1-2 sentence description>"
```

Then say:
> "Your `config/brand_voice.md` has a default writing style template. Review it and edit it to match how you actually write. The better it describes your voice, the better your drafts will be."

## Step 4: Google Cloud Setup

Check if `credentials.json` exists in the repo root.

**If it does NOT exist:**

Walk through these steps with the colleague:
1. Go to https://console.cloud.google.com → create a new project
2. Enable **Google Sheets API** and **Google Drive API**
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Choose **Desktop app**, download the JSON file
5. Save it as `credentials.json` in the repo root
6. Run: `python execution/sheets_client.py` — this opens a browser, completes the OAuth flow, and creates `token.json`

**If it exists:** confirm it belongs to the colleague before proceeding.

## Step 5: Google Sheet Setup

Read `GOOGLE_SHEET_ID` from `.env`.

**If `GOOGLE_SHEET_ID` is set:**
- Derive the sheet URL: `https://docs.google.com/spreadsheets/d/<ID>/edit`
- Ask: "I found a Google Sheet ID in your `.env`. Is this your sheet? (yes / no)"
- On **yes**: confirm which sheet will be used and proceed
- On **no**: proceed to create a new sheet (below)

**If not set, or if the colleague said no:**
- Use the Google Drive MCP to create a new Google Sheet
- Name it: `LinkedIn Posts`
- Create a tab called `LinkedIn Posts` with these headers in row 1 (in this exact order):
  `source, about, title, text, image_prompt, status, scheduled_date, date_added, date_textgen, published_url, date_posted`
- Share the sheet URL with the colleague
- Instruct them: "Add the sheet ID to your `.env` file as `GOOGLE_SHEET_ID=<id>`"
- The ID is the part of the URL between `/d/` and `/edit`
- Wait for the colleague to confirm they've added it before proceeding

## Step 6: LinkedIn Credentials

Read `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` from `.env`.

**If both are set:** confirm and skip to Step 7.

**If either is missing**, walk through:
1. Go to https://linkedin.com/developers → **Create app**
2. Fill in app name and LinkedIn page (can use your personal profile page URL)
3. Under **Products**, request **Share on LinkedIn** (this grants `w_member_social`)
4. Under **Auth**, add a redirect URL: `http://localhost:8080/` (or any valid URL)
5. Complete the OAuth 2.0 Authorization Code flow:
   - Authorization URL: `https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=<CLIENT_ID>&redirect_uri=<REDIRECT_URI>&scope=w_member_social%20r_liteprofile`
   - Exchange the returned code for a token at: `https://www.linkedin.com/oauth/v2/accessToken`
6. Add `LINKEDIN_ACCESS_TOKEN=<token>` to `.env`
7. Run: `python execution/get_linkedin_id.py`
8. Add `LINKEDIN_PERSON_URN=<id>` to `.env` (numeric ID only, not full URN)

## Step 7: Confirm Setup Complete

Verify:
- [ ] `config/profile.yaml` written
- [ ] `config/themes.yaml` written
- [ ] `config/brand_voice.md` reviewed
- [ ] `credentials.json` present and `token.json` generated
- [ ] `GOOGLE_SHEET_ID` in `.env`
- [ ] `LINKEDIN_ACCESS_TOKEN` in `.env`
- [ ] `LINKEDIN_PERSON_URN` in `.env`

Then say:
> "Setup complete! Here's what to do next:
> 1. `/capture-ideas` — paste a list of article ideas
> 2. `/create-articles` — generate drafts from those ideas
> 3. Review drafts in your Google Sheet and mark any you like as 'ready'
> 4. `/schedule` — let me propose a posting schedule and set up automatic publishing"
```

- [ ] **Step 2: Commit**

```bash
git add skills/setup.md
git commit -m "feat: add setup skill for colleague onboarding"
```

---

## Task 9: `skills/capture-ideas.md`

**Files:**
- Create: `skills/capture-ideas.md`

- [ ] **Step 1: Write `skills/capture-ideas.md`**

```markdown
---
name: capture-ideas
description: Capture a list of LinkedIn article ideas and save them to Google Sheets with status=new. Accepts bullet lists, numbered lists, or plain line-separated text.
---

# Capture Ideas

Parse the colleague's input and save each idea to the Google Sheet.

## Step 1: Parse Input

The colleague has provided a list of ideas. Parse it into individual ideas, handling:
- Bullet list: `- idea` or `* idea`
- Numbered list: `1. idea`
- Plain lines: one idea per non-empty line

Strip leading/trailing whitespace and list markers from each item.
Skip empty lines.

## Step 2: Deduplicate

Run: `python execution/sheets_client.py` is not a dedup tool — instead, call `get_rows('LinkedIn Posts')` via the execution script to retrieve existing `about` values. Compare case-insensitively. Flag any ideas already in the sheet.

To fetch existing ideas, run:
```bash
python -c "
from execution.sheets_client import get_rows
rows = get_rows('LinkedIn Posts')
for r in rows: print(r.get('about',''))
"
```

## Step 3: Append New Ideas

For each new (non-duplicate) idea, run:
```bash
python -c "
from execution.sheets_client import append_idea
append_idea('<idea text>', 'Manual', status='new')
"
```

Or batch them in a single script if there are many.

## Step 4: Report

Tell the colleague:
> "Added X ideas to your sheet. Y were duplicates and skipped.
> Run `/create-articles` when you're ready to generate drafts."

If `GOOGLE_SHEET_ID` is not set, redirect:
> "I couldn't find your Google Sheet. Run `/setup` first to connect your sheet."
```

- [ ] **Step 2: Commit**

```bash
git add skills/capture-ideas.md
git commit -m "feat: add capture-ideas skill for idea intake"
```

---

## Task 10: `skills/create-articles.md`

**Files:**
- Create: `skills/create-articles.md`

- [ ] **Step 1: Write `skills/create-articles.md`**

```markdown
---
name: create-articles
description: Generate LinkedIn article drafts from all ideas with status=new. Uses the colleague's brand voice and content themes. Updates sheet status to 'review' when done.
---

# Create Articles

Generate LinkedIn drafts for all new ideas using the colleague's brand voice and content themes.

## Step 1: Check for New Ideas

```bash
python -c "
from execution.sheets_client import get_rows
rows = get_rows('LinkedIn Posts', status_filter='new')
print(f'{len(rows)} new ideas found')
for r in rows: print(f'  Row {r[\"_row_number\"]}: {r.get(\"about\",\"\")[:60]}')
"
```

If 0 rows: tell the colleague "No new ideas to draft. Add ideas first with `/capture-ideas`." and stop.

## Step 2: Load Config

Read these files:
- `config/brand_voice.md` — full contents as a string
- `config/themes.yaml` — parse with PyYAML, format themes as a numbered list
- `config/profile.yaml` — read the `role` field

Format themes as:
```
1. <theme name>: <description>
2. <theme name>: <description>
3. <theme name>: <description>
```

If any config file is missing or empty, tell the colleague to run `/setup` first.

## Step 3: Generate Drafts

For each new idea row, run:
```bash
python -c "
import yaml
from pathlib import Path
from execution.llm_content_gen import generate_draft
from execution.sheets_client import update_row
from datetime import datetime

brand_voice = Path('config/brand_voice.md').read_text()
themes_raw = yaml.safe_load(Path('config/themes.yaml').read_text())
themes = '\n'.join(f'{i+1}. {t[\"name\"]}: {t[\"description\"]}' for i, t in enumerate(themes_raw['themes']))
profile = yaml.safe_load(Path('config/profile.yaml').read_text())
role = profile.get('role', 'professional')

draft = generate_draft('<about>', brand_voice, themes, role)
update_row('LinkedIn Posts', <row_number>, {
    'title': draft['title'],
    'text': draft['text'],
    'image_prompt': draft['image_prompt'],
    'status': 'review',
    'date_textgen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
})
print('Done:', draft['title'])
"
```

Replace `<about>` and `<row_number>` with actual values. Run once per idea.

## Step 4: Report

Tell the colleague how many drafts were created and link to the sheet:
> "X drafts created and set to 'review'.
> Open your Google Sheet to review them: https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
> Change any you approve to 'ready' status, then run `/schedule` or `/post-article`."

Read `GOOGLE_SHEET_ID` from `.env` to build the URL.
```

- [ ] **Step 2: Commit**

```bash
git add skills/create-articles.md
git commit -m "feat: add create-articles skill for draft generation"
```

---

## Task 11: `skills/post-article.md`

**Files:**
- Create: `skills/post-article.md`

- [ ] **Step 1: Write `skills/post-article.md`**

```markdown
---
name: post-article
description: Publish a ready LinkedIn article immediately. Lists ready articles for the colleague to choose from, shows a preview, and posts on confirmation.
---

# Post Article

Publish a selected article to LinkedIn right now.

## Step 1: List Ready Articles

```bash
python -c "
from execution.sheets_client import get_rows
rows = get_rows('LinkedIn Posts', status_filter='ready')
if not rows:
    print('NO_READY')
else:
    for r in rows:
        score = len(r.get('text','')) // 100 + r.get('text','').count('#') + (2 if '?' in r.get('text','') else 0)
        print(f'Row {r[\"_row_number\"]:3} | Score {score:2} | {(r.get(\"title\") or r.get(\"about\",\"\"))[:55]}')
"
```

If output is `NO_READY`:
> "No ready articles found. Review your drafts in Google Sheets and mark approved ones as 'ready', then try again."
Stop here.

## Step 2: Select Article

If the colleague did not specify a row number, ask them to pick one from the list.

## Step 3: Show Preview

```bash
python -c "
from execution.sheets_client import get_rows
from execution.linkedin_client import build_post_text
rows = get_rows('LinkedIn Posts')
row = next((r for r in rows if r['_row_number'] == <row_number>), None)
if row:
    print(build_post_text(row.get('title',''), row.get('text','')))
"
```

Show the full post text to the colleague.

## Step 4: Confirm and Post

Ask: "Post this to LinkedIn now? (yes / no)"

On **yes**:
```bash
python -c "
from execution.sheets_client import get_rows, update_row
from execution.linkedin_client import post_text, build_post_text, urn_to_url
from datetime import datetime
rows = get_rows('LinkedIn Posts')
row = next((r for r in rows if r['_row_number'] == <row_number>), None)
if row:
    full_text = build_post_text(row.get('title',''), row.get('text',''))
    post_urn = post_text(full_text)
    if post_urn:
        url = urn_to_url(post_urn)
        update_row('LinkedIn Posts', <row_number>, {
            'status': 'posted',
            'date_posted': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'published_url': url,
        })
        print('SUCCESS:', url)
    else:
        print('FAILED')
"
```

On **SUCCESS**: tell the colleague the post URL.
On **FAILED**: tell the colleague the API call failed, the row stays 'ready' for retry. Suggest running `/setup` to check LinkedIn credentials.

On **no**: tell the colleague "Cancelled. The article stays in 'ready' status."

## Error Handling

- If `LINKEDIN_ACCESS_TOKEN` is not set: redirect to `/setup`
- If the selected row is not found or not in 'ready' status: report clearly and stop
```

- [ ] **Step 2: Commit**

```bash
git add skills/post-article.md
git commit -m "feat: add post-article skill for interactive LinkedIn publishing"
```

---

## Task 12: `skills/schedule.md`

**Files:**
- Create: `skills/schedule.md`

- [ ] **Step 1: Write `skills/schedule.md`**

```markdown
---
name: schedule
description: Propose a posting schedule for all ready articles (Tue/Wed/Thu, 08:30 Europe/Amsterdam), write scheduled dates to Google Sheet, and set up a daily Claude CronCreate routine for autonomous publishing.
---

# Schedule Posts

Propose a posting schedule and set up the daily auto-publish routine.

## Step 1: Fetch Ready and Scheduled Posts

```bash
python -c "
from execution.sheets_client import get_schedule
slots, unscheduled = get_schedule(days=30)
print('SCHEDULED:')
for s in slots:
    if s['post']:
        print(f'  {s[\"date\"]}  {s[\"weekday\"][:3]}  Row {s[\"post\"][\"_row_number\"]}  {(s[\"post\"].get(\"title\") or \"\")[:45]}')
print('UNSCHEDULED_READY:')
for r in unscheduled:
    print(f'  Row {r[\"_row_number\"]}  {(r.get(\"title\") or r.get(\"about\",\"\"))[:50]}')
"
```

If there are no unscheduled ready articles:
> "All your ready articles are already scheduled. Re-run `/schedule` after approving more drafts."

## Step 2: Propose Schedule

Generate a schedule for all unscheduled ready rows:

Rules:
- Post only on **Tuesday, Wednesday, Thursday**
- Minimum **2 days** between consecutive posts
- Start from **tomorrow** (never today — allow time for any last-minute review)
- Skip dates already occupied by a scheduled post
- Fill forward until all unscheduled ready articles have a date

Present the proposed schedule as a table, for example:
```
Row 4  →  Tue 2026-05-06  "Why AI won't replace your team"
Row 7  →  Thu 2026-05-08  "3 lessons from our digital rollout"
Row 9  →  Tue 2026-05-13  "What good leadership looks like in 2026"
```

## Step 3: Confirm with Colleague

Ask: "Does this schedule work, or would you like to adjust any dates?"

If they want changes, accept revised dates (YYYY-MM-DD format) and update the proposed schedule before writing.

## Step 4: Write Schedule to Sheet

For each confirmed row/date pair:
```bash
python -c "
from execution.sheets_client import set_scheduled_date
set_scheduled_date(<row_number>, '<YYYY-MM-DD>')
print('Scheduled Row <row_number> for <date>')
"
```

## Step 5: Set Up Daily CronCreate Routine

Check if a daily cron routine already exists (ask the colleague or check via CronList).

If no routine exists, create one using CronCreate:
- **Schedule:** daily at 08:15 Europe/Amsterdam (CET: `15 8 * * *`, CEST: `15 7 * * *` UTC — use IANA zone `Europe/Amsterdam` so DST is handled automatically)
- **Prompt:** "Navigate to the repo root, then execute: `python execution/publish_today.py`. The script checks the Google Sheet for a post with today's scheduled_date and status=ready. If found, it publishes to LinkedIn and updates the sheet. If not found, it logs 'No post scheduled for today' and exits cleanly. Report the script's full output."

If a routine already exists: tell the colleague it's already active. Offer to show the schedule or remove it.

## Step 6: Confirm

> "Schedule saved. Posts are queued for:
> [list the dates]
>
> The daily routine will check at 08:15 and publish automatically.
> You'll need to be logged in to Claude Code for the routine to run.
>
> To add more articles to the schedule later, just run `/schedule` again after approving new drafts."

## Removing the Routine

If the colleague asks to remove the auto-publish routine, use CronDelete to remove it and confirm.
```

- [ ] **Step 2: Commit**

```bash
git add skills/schedule.md
git commit -m "feat: add schedule skill with auto-propose and CronCreate setup"
```

---

## Task 13: README and Final Polish

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# LinkedIn Thought Leader Agent

A Claude-powered pipeline for publishing consistent LinkedIn thought leadership articles. Clone it, run the setup skill, and you're posting.

## What it does

1. **Captures ideas** — paste a list, they go into Google Sheets
2. **Drafts articles** — Claude writes LinkedIn posts in your voice around 3 themes you define
3. **You review** — approve drafts in Google Sheets by changing status to `ready`
4. **Auto-posts** — a daily routine publishes scheduled articles at 08:30 Netherlands time

## Prerequisites

- [Claude Code](https://claude.ai/code) installed
- Python 3.11+
- A Google account (for Sheets)
- A LinkedIn Developer app ([guide in setup skill](skills/setup.md))
- An [Anthropic API key](https://console.anthropic.com)

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/shartgers/linkedin-publish-agent.git
cd linkedin-publish-agent

# 2. Install Python dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Copy credential template
cp .env.example .env

# 4. Open Claude Code and run the setup skill
# In Claude Code, type:
/setup
```

The setup skill walks you through everything else.

## Skills

| Skill | Invoke | Purpose |
|-------|--------|---------|
| `setup` | `/setup` | One-time onboarding |
| `capture-ideas` | `/capture-ideas` | Add ideas → Sheet |
| `create-articles` | `/create-articles` | Generate drafts |
| `post-article` | `/post-article` | Publish now |
| `schedule` | `/schedule` | Schedule + auto-post |

## Workflow

```
/capture-ideas  →  /create-articles  →  [review in sheet]  →  /schedule
```

The `review → ready` step in Google Sheets is intentionally manual. You decide what gets published.

## Customization

- `config/brand_voice.md` — edit to match your writing style
- `config/themes.yaml` — your 3 content topics
- `config/profile.yaml` — your name, role, LinkedIn URN

## Running Tests

```bash
pytest -v
```
```

- [ ] **Step 2: Verify full test suite passes**

```bash
pytest -v
```
Expected: all tests PASS, no failures.

- [ ] **Step 3: Final commit**

```bash
git add README.md
git commit -m "docs: add README with quickstart guide for colleagues"
```

---

## Verification Checklist

Before calling this complete:

- [ ] `pytest -v` — all tests pass
- [ ] `python execution/sheets_client.py` — connects to Google Sheets (requires real credentials)
- [ ] `python execution/get_linkedin_id.py` — retrieves person ID (requires real credentials)
- [ ] `python execution/publish_today.py --dry-run` — exits cleanly with "No post scheduled for today" or preview
- [ ] All 5 skill files exist in `skills/`
- [ ] All 3 config template files exist in `config/`
- [ ] `.env.example` covers all required keys
- [ ] `CLAUDE.md` lists all 5 skills
- [ ] `README.md` covers getting started end-to-end
- [ ] `.gitignore` excludes `.env`, `credentials.json`, `token.json`, `app-backup/`
