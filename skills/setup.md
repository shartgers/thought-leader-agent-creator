---
name: setup
description: One-time onboarding for the LinkedIn Thought Leader Agent at Xomnia. Configures profile, content themes, Google Sheets, and LinkedIn credentials. Run once per colleague, or re-run to update config.
---

# Setup — LinkedIn Thought Leader Agent at Xomnia

Guide the Xomnia thought leader through full onboarding. Follow every step in order. Do not skip steps.

## Step 1: Welcome

Introduce yourself briefly:
> "Welcome to the LinkedIn Thought Leader Agent provided by Xomnia — your personal content engine for building a strong professional presence on LinkedIn. This agent helps you as a thought leader to share your expertise consistently and efficiently. I'll walk you through setup — it takes about 10–15 minutes. By the end, you'll have your profile configured, 3 content themes locked in, and your Google Sheet and LinkedIn account connected."

## Step 2: Collect Profile Info

Ask for:
1. Full name
2. Job title / role

Write these to `config/profile.yaml`:
```yaml
name: "<name>"
role: "<role>"
company: "Xomnia"
industry: "Data & AI Consultancy"
linkedin_urn: ""
preferred_post_time: "08:30"
timezone: "Europe/Amsterdam"
# Set to false if you get SSL errors (corporate proxy with self-signed cert)
ssl_verify: true
```

## Step 3: Define 3 Content Themes

Explain:
> "Consistent thought leaders own 2-3 specific topics. I'll suggest themes based on your role — you refine them."

Suggest 3 themes based on their role. For example:
- Data engineer → "Data platform architecture", "The reality of production ML", "Career growth in data"
- AI consultant → "AI adoption lessons", "Responsible AI in practice", "From prototype to production"

Agree on 3 themes, then write to `config/themes.yaml`:
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

## Step 4: Install Python Dependencies

Run from the repo root:
```
pip install -r requirements.txt
```

## Step 5: Google Cloud Setup

Check if `credentials.json` exists in the repo root.

**If it does NOT exist**, walk through these steps:

1. Go to https://console.cloud.google.com → create a new project
2. Enable **Google Sheets API** and **Google Drive API**
3. Set up the **OAuth consent screen**:
   - Go to **APIs & Services → OAuth consent screen**
   - Under **Audience**, select **External**
   - Fill in the **App name** (e.g., "LinkedIn Publish Agent") and your **support email address**
   - Click through the remaining sections (Scopes, Optional Info) without changes and save
   - Under **Audience → Test users**, click **Add users** and add your Google account email
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Choose **Desktop app**, download the JSON file
6. Save it as `credentials.json` in the repo root

Once `credentials.json` is saved, run the Google authentication directly using the Bash tool:
```
python execution/sheets_client.py
```
Use system Python from the repo root — no virtual environment needed for this step.

This opens a browser window. When you see **"Google hasn't verified this app"**, click **"Proceed"** (Dutch: "Doorgaan") to continue. This completes the OAuth flow and creates `token.json`.

**If `credentials.json` already exists**: confirm it belongs to the colleague before proceeding.

## Step 6: Google Sheet Setup

First write a placeholder to `.env` so the import doesn't fail:
```
GOOGLE_SHEET_ID=placeholder
```

Then run this Python snippet via the Bash tool to create the sheet under the same Google account as the OAuth token:

```python
python -c "
import sys; sys.path.insert(0, '.')
from execution.sheets_client import get_service

HEADERS = ['source','about','title','text','image_prompt','status','scheduled_date',
           'date_added','date_textgen','published_url','date_posted']

svc = get_service()
body = {
    'properties': {'title': 'LinkedIn Posts'},
    'sheets': [{'properties': {'title': 'LinkedIn Posts'}}]
}
result = svc.spreadsheets().create(body=body).execute()
sheet_id = result['spreadsheetId']
print('Sheet ID:', sheet_id)
print('URL:', result['spreadsheetUrl'])

svc.spreadsheets().values().update(
    spreadsheetId=sheet_id,
    range=\"'LinkedIn Posts'!A1\",
    valueInputOption='RAW',
    body={'values': [HEADERS]}
).execute()
print('Headers written.')
"
```

Copy the printed Sheet ID and update `.env`:
```
GOOGLE_SHEET_ID=<id from output>
```

Share the sheet URL with the colleague so they can bookmark it.

## Step 7: LinkedIn Setup

**If either credential is missing**, walk through in this order:

### 7a. Create a LinkedIn Company Page (required for the developer app)

> "LinkedIn requires a Company Page to create a developer app. Let's create one for you now."

Guide the colleague to:
1. Go to https://www.linkedin.com/company/setup/new/
2. Choose **Company** as the page type
3. Fill in name, LinkedIn URL, industry, size, and type
4. Click **Create page**
5. Note the page URL (e.g., `https://www.linkedin.com/company/xomnia/`) — needed in the next step

### 7b. Create the LinkedIn Developer App

1. Go to https://www.linkedin.com/developers/apps/new
2. **App name**: `Xomnia Publish Agent` (LinkedIn does not allow the word "LinkedIn" in app names)
3. **LinkedIn Page**: paste the company page URL from step 7a (or type to search by name)
4. Accept the terms and click **Create app**
5. Go to the **Products** tab → request both:
   - **Share on LinkedIn** (grants `w_member_social`)
   - **Sign In with LinkedIn using OpenID Connect** (grants `openid`, `profile`, `email`)
   Both are usually approved instantly.
6. Go to the **Auth** tab:
   - Note your **Client ID** and **Client Secret**
   - Under **OAuth 2.0 settings**, add redirect URL: `http://localhost:8080/`

### 7c. Save credentials and authenticate

Ask the colleague to add to their `.env` file:
```
LINKEDIN_CLIENT_ID=<client_id>
LINKEDIN_CLIENT_SECRET=<client_secret>
```

Once confirmed, run the LinkedIn OAuth flow directly using the Bash tool:
```
python execution/linkedin_auth.py
```

This opens a browser, completes the OAuth flow, and automatically saves `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` to `.env`.

## Step 8: Confirm Setup Complete

Verify:
- [ ] `config/profile.yaml` written
- [ ] `config/themes.yaml` written
- [ ] `config/brand_voice.md` reviewed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
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
