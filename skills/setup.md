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
