# Creator Agent Updates — Fixes from First Real Setup Run

These are the changes discovered during the first real onboarding of this agent.
Apply them to the creator agent repo so future instances are generated correctly.

---

## 1. `execution/linkedin_auth.py` — Two fixes

### 1a. OAuth scope: add `openid profile`

The LinkedIn developer app needs the **"Sign In with LinkedIn using OpenID Connect"** product
in addition to "Share on LinkedIn". The auth URL must request `openid profile` alongside
`w_member_social`.

```diff
- "&scope=w_member_social"
+ "&scope=openid%20profile%20w_member_social"
```

**Why:** The `/v2/me` endpoint (which the original code used) returns 403 for all new LinkedIn
apps — LinkedIn deprecated it. The `/v2/userinfo` endpoint also returns 403 unless the
OpenID Connect product is added. Adding `openid profile` makes LinkedIn return an `id_token`
JWT in the token exchange response, which is the reliable way to get the person ID.

### 1b. Person ID extraction: decode `id_token` instead of API calls

Replace the API-based person ID fetching with OIDC `id_token` JWT decoding:

```python
# OLD — both endpoints return 403 for new apps
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
```

```python
# NEW — extract sub claim from id_token JWT (no extra API call needed)
token_data = resp.json()
access_token = token_data.get('access_token')

person_id = None
id_token = token_data.get('id_token')
if id_token:
    import base64, json as _json
    payload = id_token.split('.')[1]
    payload += '=' * (-len(payload) % 4)
    claims = _json.loads(base64.urlsafe_b64decode(payload))
    person_id = claims.get('sub')

# Fallback: try userinfo endpoint
if not person_id:
    headers = {'Authorization': f'Bearer {access_token}'}
    r = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers)
    if r.status_code == 200:
        person_id = r.json().get('sub')
```

---

## 2. `execution/sheets_client.py` — Open browser during OAuth

```diff
- creds = flow.run_local_server(port=OAUTH_PORT, prompt='consent', open_browser=False)
+ creds = flow.run_local_server(port=OAUTH_PORT, prompt='consent', open_browser=True)
```

**Why:** The original had `open_browser=False`, which meant the user had to manually copy/paste
the auth URL. Setting it to `True` automatically opens the browser, which is the expected UX.

---

## 3. `skills/setup.md` — Step 6b: require OpenID Connect product

In Step 6b under the Products tab instruction, add the second product:

```diff
- 5. Go to the **Products** tab → request **Share on LinkedIn** (grants `w_member_social`)
+ 5. Go to the **Products** tab → request both:
+    - **Share on LinkedIn** (grants `w_member_social`)
+    - **Sign In with LinkedIn using OpenID Connect** (grants `openid`, `profile`, `email`)
+    Both are usually approved instantly.
```

---

## 4. `skills/setup.md` — Step 5: create sheet via Python, not Drive MCP

The setup skill currently says to use the Google Drive MCP to create the spreadsheet.
**This causes a 403 error** because the Drive MCP authenticates under a different Google account
than the one used by the Python scripts (e.g. Xomnia Workspace vs personal Gmail).

Replace the Google Drive MCP step with a Python-based creation:

```diff
- Use the Google Drive MCP to create a new Google Sheet:
- - Name it: `LinkedIn Posts`
- - Create a tab called `LinkedIn Posts` with these headers in row 1 (in this exact order):
-   `source, about, title, text, image_prompt, status, scheduled_date, date_added, date_textgen, published_url, date_posted`
+ First write a placeholder `.env` with an empty GOOGLE_SHEET_ID, then run this Python snippet
+ via the Bash tool to create the sheet under the same account as the OAuth token:
+
+ ```python
+ python -c "
+ import sys; sys.path.insert(0, '.')
+ from execution.sheets_client import get_service
+
+ HEADERS = ['source','about','title','text','image_prompt','status','scheduled_date',
+            'date_added','date_textgen','published_url','date_posted']
+
+ svc = get_service()
+ body = {
+     'properties': {'title': 'LinkedIn Posts'},
+     'sheets': [{'properties': {'title': 'LinkedIn Posts'}}]
+ }
+ result = svc.spreadsheets().create(body=body).execute()
+ sheet_id = result['spreadsheetId']
+ print('Sheet ID:', sheet_id)
+ print('URL:', result['spreadsheetUrl'])
+
+ svc.spreadsheets().values().update(
+     spreadsheetId=sheet_id,
+     range=\"'LinkedIn Posts'!A1\",
+     valueInputOption='RAW',
+     body={'values': [HEADERS]}
+ ).execute()
+ print('Headers written.')
+ "
+ ```
+
+ Copy the printed Sheet ID and write it to `.env`:
+ ```
+ GOOGLE_SHEET_ID=<id from output>
+ ```
```

**Note:** `get_service()` requires `GOOGLE_SHEET_ID` to be set only for read/write operations,
not for `spreadsheets().create()`. So either set a dummy value first or remove the `SPREADSHEET_ID`
guard from `get_service()` — the current code works because `create()` doesn't use `SPREADSHEET_ID`.
