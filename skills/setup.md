---
name: setup
description: One-time onboarding for the LinkedIn Thought Leader Agent at Xomnia. Configures profile, content themes, Google Sheets, and LinkedIn credentials. Run once per colleague, or re-run to update config.
---

# Setup — LinkedIn Thought Leader Agent at Xomnia

Guide the colleague through full onboarding. Follow every step in order. Do not skip steps.

## Step 1: Welcome

Introduce yourself:
> "Welcome to the LinkedIn Thought Leader Agent at Xomnia! I'll walk you through setup — it takes about 15 minutes. By the end, you'll have your profile configured, 3 content themes locked in, and your Google Sheet and LinkedIn account connected so you can start publishing consistently."

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
```

## Step 3: Define 3 Content Themes

Explain:
> "Consistent thought leaders own 2-3 specific topics. I'll suggest themes based on your role — you refine them."

Suggest 3 themes based on their role. For example:
- Data scientist → "AI in practice", "Data-driven decisions", "ML engineering lessons"
- Consultant → "Digital transformation", "AI adoption", "Tech leadership"

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

## Step 4: Python Environment Setup

Check if `.venv` exists in the repo root. If it does NOT exist, run:

```
python -m venv .venv
```

Then install dependencies:
- **Windows**: `.venv\Scripts\pip install -r requirements.txt`
- **Mac/Linux**: `.venv/bin/pip install -r requirements.txt`

All subsequent Python script runs in this setup use `.venv\Scripts\python` (Windows) or `.venv/bin/python` (Mac/Linux).

## Step 5: Google Cloud Setup

Check if `credentials.json` exists in the repo root.

**If it does NOT exist**, walk through these steps:

1. Go to https://console.cloud.google.com → create a new project
2. Enable **Google Sheets API** and **Google Drive API**
3. Go to **APIs & Services → OAuth consent screen**:
   - Set User Type to **External**, click **Create**
   - Fill in **App name** (e.g., "Xomnia Thought Leader Agent") and your **support email**
   - Save and continue through the scopes screen (no changes needed)
   - On the **Audience** tab: publishing status stays **Testing**
   - Under **Test users** → click **Add users** → add your Google account email → Save
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Choose **Desktop app**, download the JSON file, save it as `credentials.json` in the repo root

Once `credentials.json` is in place, run the Google authentication directly:

**Windows**: `.venv\Scripts\python -c "from execution.sheets_client import get_service; get_service()"`
**Mac/Linux**: `.venv/bin/python -c "from execution.sheets_client import get_service; get_service()"`

This opens a browser. When the colleague sees **"Google hasn't verified this app"**, tell them to click **"Proceed"** (Dutch: "Doorgaan") to continue. This completes OAuth and creates `token.json`.

**If `credentials.json` already exists**: confirm it belongs to the colleague before proceeding.

## Step 6: Google Sheet Setup

Using the Google Drive MCP, create a new Google Sheet:
- Name: `LinkedIn Posts`
- Add a tab called `LinkedIn Posts` with these headers in row 1 (exact order):
  `source, about, title, text, image_prompt, status, scheduled_date, date_added, date_textgen, published_url, date_posted`

Share the sheet URL with the colleague, then:
1. Extract the Sheet ID from the URL (the part between `/d/` and `/edit`)
2. Write `GOOGLE_SHEET_ID=<id>` to `.env`

Confirm the sheet is reachable before continuing.

## Step 7: LinkedIn Setup

### 7a — Create a LinkedIn Company Page

The colleague needs a LinkedIn Company Page to register the developer app. If they don't have one yet:

1. Go to https://www.linkedin.com/company/setup/new/
2. Choose **Company** page type
3. Fill in: company name, LinkedIn URL slug, website, industry (IT Services and IT Consulting), company size, organization type
4. Click **Create page**

Copy the company page URL (e.g., `https://www.linkedin.com/company/xomnia/`) — it's needed in the next step.

### 7b — Create a LinkedIn Developer App

1. Go to https://www.linkedin.com/developers/apps/new
2. Fill in:
   - **App name**: `Xomnia Thought Leader Agent`
   - **LinkedIn Page**: paste the company page URL from above
3. Under **Products**, request **Share on LinkedIn** (grants `w_member_social`)
4. Under **Auth**, add redirect URL: `http://localhost:8080/`
5. From the **Auth** tab, copy the **Client ID** and **Client Secret**

### 7c — Run LinkedIn Authorization

Ask the colleague to add to their `.env` file:
```
LINKEDIN_CLIENT_ID=<client_id>
LINKEDIN_CLIENT_SECRET=<client_secret>
```

Once confirmed, run the LinkedIn OAuth flow directly:

**Windows**: `.venv\Scripts\python execution/linkedin_auth.py`
**Mac/Linux**: `.venv/bin/python execution/linkedin_auth.py`

This opens a browser, the colleague authorizes the app, and the script saves `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` to `.env` automatically.

## Step 8: Confirm Setup Complete

Verify:
- [ ] `config/profile.yaml` written
- [ ] `config/themes.yaml` written
- [ ] `config/brand_voice.md` reviewed
- [ ] `.venv` created and dependencies installed
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
