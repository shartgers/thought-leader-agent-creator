# LinkedIn Thought Leader Agent — Design Spec

**Date:** 2026-05-03
**Status:** Approved for implementation

---

## Overview

A portable, skills-based LinkedIn content pipeline that colleagues can clone, configure once, and use to consistently publish thought leadership articles. Built on Claude skills + Python execution scripts + Google Sheets. No webapp. No GitHub Actions. Scheduled publishing via Claude's `CronCreate` routine.

The repo is designed to be shared. A colleague clones it, runs the setup skill, and is guided through everything — role, themes, credentials, and sheet creation — before they write a single article.

---

## Goals

- Any colleague can clone this repo and be fully operational after one setup conversation
- Ideas captured by pasting a text list into chat
- Articles generated in a consistent brand voice tied to 3 personal content themes
- Human review gate preserved: `review → ready` is always manual (in the sheet)
- Scheduled posts publish autonomously at optimal LinkedIn times (NL timezone), no action required from the user

---

## Non-Goals

- Voice note transcription (out of scope)
- YouTube channel scanning (removed for simplicity)
- RSS/news feed harvesting (removed for simplicity)
- A web UI or dashboard
- GitHub Actions (replaced by Claude CronCreate)

---

## Architecture

### Layer 1: Skills (entry points)
Five skills that colleagues invoke directly. Skills are the orchestration layer — they read config, call execution scripts, and handle all user interaction.

```
skills/
  setup.md            ← onboarding: role, themes, credentials, sheet creation
  capture-ideas.md    ← text list → Google Sheet (status: new)
  create-articles.md  ← new ideas → LinkedIn drafts (status: review)
  post-article.md     ← selected ready article → LinkedIn (status: posted)
  schedule.md         ← propose schedule + create CronCreate routine
```

### Layer 2: Execution Scripts (deterministic)
Python scripts ported and parameterized from the proven original implementation. Scripts read from config files rather than hardcoded values, making the repo portable.

```
execution/
  sheets_client.py    ← Google Sheets CRUD (read, append, update rows)
  linkedin_client.py  ← LinkedIn ugcPosts API wrapper
  llm_content_gen.py  ← Claude API: draft generation from idea + brand voice + themes
  publish_today.py    ← reads today's scheduled ready post and publishes it (called by cron)
```

### Layer 3: Config (per-colleague customization)
Everything a colleague customizes lives here. Set once during setup, editable any time.

```
config/
  brand_voice.md      ← LinkedIn writing style (tone, structure, dos/don'ts)
  themes.yaml         ← 3 content themes agreed during onboarding
  profile.yaml        ← name, role, company, LinkedIn URN, preferred post time

.env                  ← API keys (never committed)
.env.example          ← template with all required keys and instructions
```

---

## Google Sheet Structure

**Sheet name:** `LinkedIn Posts` (created by setup skill if not present)

| Column | Description |
|--------|-------------|
| `source` | How the idea was captured (e.g. "Manual") |
| `about` | Original idea text as provided by colleague |
| `title` | Generated post title |
| `text` | LinkedIn post body |
| `image_prompt` | AI image generation prompt (optional, not used by default) |
| `status` | Workflow state: `new / review / ready / posted` |
| `scheduled_date` | ISO date assigned by schedule skill (YYYY-MM-DD) |
| `date_added` | Timestamp when idea was captured |
| `date_textgen` | Timestamp when draft was generated |
| `published_url` | LinkedIn post URL after publishing |
| `date_posted` | Timestamp when published |

### Status Workflow

```
new → review → ready → posted
       ↑
  MANUAL GATE: colleague changes review → ready in the sheet
```

The `review → ready` transition is **intentionally manual**. This is a feature, not a gap. The colleague reads the draft in the sheet, edits if needed, and marks it ready. No automation bypasses this step.

---

## Skill Specifications

### `setup` — Onboarding

**Trigger:** Run once per colleague (or re-run to update config).

**Flow:**
1. Greet the colleague and explain what the agent does
2. Ask for their **name**, **role**, and **company/industry**
3. Collaboratively identify **3 content themes** — the skill suggests themes based on role/industry, the colleague refines them. Themes define what they post about consistently (e.g. "AI in operations", "leadership lessons", "sustainable logistics")
4. Write `config/profile.yaml` and `config/themes.yaml`
5. Copy `config/brand_voice.md` from the default template — invite the colleague to review and edit it
6. **Google Cloud / Sheets setup:**
   - Explain that a Google Cloud project and OAuth credentials are required for Sheets access
   - Walk through these steps if `credentials.json` does not exist:
     1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a new project
     2. Enable the **Google Sheets API** and **Google Drive API**
     3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
     4. Choose **Desktop app**, download the JSON, and save it as `credentials.json` in the repo root
     5. Run `python execution/sheets_client.py` once — this opens a browser auth flow and generates `token.json`
   - Check for `GOOGLE_SHEET_ID` in `.env`:
     - If found: display the sheet URL derived from the ID and ask "Is this your sheet? (yes / no)"
       - On **yes**: proceed with the existing sheet
       - On **no**: create a new Google Sheet via Google Drive MCP with the correct tab name and columns; display the URL; instruct the colleague to update `GOOGLE_SHEET_ID` in `.env`
     - If not found: create a new Google Sheet via Google Drive MCP; display the URL; instruct the colleague to add `GOOGLE_SHEET_ID` to `.env`
   - **CRITICAL:** Never silently use an existing `GOOGLE_SHEET_ID` without explicit confirmation from the colleague. Always ask.
7. **LinkedIn credentials check:**
   - Look for `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` in `.env`
   - If missing: walk through the LinkedIn Developer App OAuth flow step by step:
     1. Go to [linkedin.com/developers](https://linkedin.com/developers) → create a new app
     2. Request the `w_member_social` and `r_liteprofile` OAuth scopes
     3. Complete the OAuth 2.0 flow to retrieve the access token
     4. Run `python execution/get_linkedin_id.py` to retrieve and confirm the person URN
     5. Add both values to `.env`
8. Confirm setup is complete. Tell the colleague their next step: run `capture-ideas` to add their first ideas.

---

### `capture-ideas` — Idea Intake

**Trigger:** Colleague pastes a list of ideas.

**Input format:** Any of:
- Bullet list (`- idea one\n- idea two`)
- Numbered list (`1. idea one\n2. idea two`)
- Plain line-separated text

**Flow:**
1. Parse the input into individual ideas
2. Fetch existing `about` values from the sheet to deduplicate
3. For each new idea, call `sheets_client.py` to append a row: `source=Manual`, `status=new`, `date_added=now`
4. Report: "Added X ideas. Y were duplicates and skipped."

---

### `create-articles` — Draft Generation

**Trigger:** Colleague invokes skill (no input required).

**Flow:**
1. Fetch all rows with `status=new` from the sheet
2. If none: "No new ideas to draft. Add ideas first with capture-ideas."
3. For each idea, call `llm_content_gen.py` with:
   - The `about` text
   - Full contents of `config/brand_voice.md`
   - The 3 themes from `config/themes.yaml`
   - The colleague's role from `config/profile.yaml`
4. Write `title`, `text`, `date_textgen` back to the row; update `status` to `review`
5. Report: "X drafts created. Review them in your Google Sheet and mark any as 'ready' when approved."
6. Output the sheet URL for convenience.

**Article generation rules (enforced in the LLM prompt):**
- Articles must align with one of the 3 themes
- Tone and structure must follow `brand_voice.md`
- Length: 150–300 words (LinkedIn optimal)
- Must include a hook in the first line, a clear point, and a closing question or call to action
- No generic AI filler. No marketing fluff.

---

### `post-article` — Publish to LinkedIn

**Trigger:** Colleague invokes skill (optionally with a row number).

**Flow:**
1. Fetch all rows with `status=ready`
2. If none: "No ready articles found. Review drafts in your sheet and mark approved ones as 'ready'."
3. If no row specified: display list of ready articles ranked by score (length, hashtags, engagement signals) — colleague picks one
4. Show full preview of selected article
5. Ask: "Post this to LinkedIn now? (yes/no)"
6. On yes: call `linkedin_client.py` to post via ugcPosts API
7. Update row: `status=posted`, `date_posted=now`, `published_url=<url>`
8. Confirm: "Posted. URL: <url>"

**Error handling:**
- Missing `LINKEDIN_ACCESS_TOKEN`: redirect to setup skill for credential walkthrough
- API failure: report error verbatim, keep row at `status=ready` for retry

---

### `schedule` — Schedule + Autonomous Routine

**Trigger:** Colleague invokes skill.

**Flow:**
1. Fetch all `status=ready` rows without a `scheduled_date`
2. Fetch existing scheduled rows to map occupied dates
3. **Propose schedule:**
   - Post days: Tuesday, Wednesday, Thursday only
   - Minimum gap: 2 days between posts
   - Post time: `08:30 Europe/Amsterdam` (adjusts for CET/CEST automatically)
   - Skip occupied dates
   - Fill forward from today until all ready articles are scheduled
4. Present proposed schedule:
   ```
   Row 4  →  Tue 2026-05-06  "Why AI won't replace your team"
   Row 7  →  Thu 2026-05-08  "3 lessons from our digital rollout"
   Row 9  →  Tue 2026-05-13  "What good leadership looks like in 2026"
   ```
5. Ask: "Does this schedule work, or would you like to adjust any dates?"
6. On approval: write `scheduled_date` to each row via `sheets_client.py`
7. **CronCreate:** If no daily routine exists yet, create one:
   - Schedule: daily at **08:15 Europe/Amsterdam** (15 min before post time)
   - Timezone: `Europe/Amsterdam` (IANA, DST-aware)
   - Prompt: *"Navigate to the repo root, then execute: `python execution/publish_today.py`. The script checks the Google Sheet for a post with today's `scheduled_date` and `status=ready`. If found, it publishes to LinkedIn and updates the sheet. If not found, it logs 'No post scheduled for today' and exits cleanly. Report the script's full output."*
   - The cron agent resolves the repo root from the project directory set at session start
8. Confirm: "Schedule saved. The daily routine will check and post automatically."

**Cron behaviour:**
- No post scheduled for today → logs "nothing scheduled", exits cleanly (not an error)
- Post published successfully → sheet row updated to `posted`
- LinkedIn API failure → logs error, row stays `ready` for retry next day or manual post via `post-article`
- Cron can be paused or deleted by re-invoking the schedule skill and choosing "remove routine"

---

## Execution Script Specifications

### `sheets_client.py`
Ported from original. Parameterized to read `GOOGLE_SHEET_ID` from `.env`. Key functions:
- `get_rows(tab, status_filter=None)` — returns rows as dicts, injecting `_row_number`
- `append_idea(about, source, status)` — adds new row
- `update_row(tab, row_number, fields)` — partial update by field name
- `get_schedule(days)` — returns calendar view + unscheduled ready posts
- `set_scheduled_date(row_number, date, shift=False)` — assigns or clears `scheduled_date`
- `get_today_scheduled_post()` — returns the row scheduled for today with `status=ready`, or None

### `linkedin_client.py`
Ported from original. Reads `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` from `.env`. Key functions:
- `post_text(text)` — posts via ugcPosts API, returns post URN or None
- `build_post_text(title, text)` — concatenates title + body for the API call

### `llm_content_gen.py`
Ported from original. Updated to accept `brand_voice`, `themes`, and `role` as inputs rather than reading hardcoded prompts. Key function:
- `generate_draft(about, brand_voice, themes, role)` → returns `{title, text, image_prompt}`

### `publish_today.py`
Ported from original. Standalone script called by the CronCreate routine:
1. Calls `get_today_scheduled_post()` — if None, exits cleanly
2. Calls `post_text(build_post_text(title, text))`
3. On success: calls `update_row` with `status=posted`, `date_posted`, `published_url`
4. On failure: logs error and exits with non-zero code

---

## Configuration Files

### `.env.example`
```
# Google Sheets
GOOGLE_SHEET_ID=                    # from sheet URL after /d/
GOOGLE_CREDENTIALS_JSON_PATH=./credentials.json
GOOGLE_TOKEN_JSON_PATH=./token.json

# LinkedIn API
LINKEDIN_ACCESS_TOKEN=              # from OAuth flow (see setup skill)
LINKEDIN_PERSON_URN=                # numeric ID only, e.g. 12345678

# Claude API (for draft generation)
CLAUDE_API_KEY=                     # from console.anthropic.com
```

### `config/themes.yaml`
```yaml
themes:
  - name: "Theme 1"
    description: "Short description of what this theme covers"
  - name: "Theme 2"
    description: "..."
  - name: "Theme 3"
    description: "..."
```

### `config/profile.yaml`
```yaml
name: ""
role: ""
company: ""
industry: ""
linkedin_urn: ""          # numeric person ID
preferred_post_time: "08:30"
timezone: "Europe/Amsterdam"
```

---

## Repo Structure (final)

```
.
├── skills/
│   ├── setup.md
│   ├── capture-ideas.md
│   ├── create-articles.md
│   ├── post-article.md
│   └── schedule.md
├── execution/
│   ├── sheets_client.py
│   ├── linkedin_client.py
│   ├── llm_content_gen.py
│   ├── publish_today.py
│   └── get_linkedin_id.py  ← retrieves person URN during setup
├── config/
│   ├── brand_voice.md      ← default template, colleague edits
│   ├── themes.yaml         ← written by setup skill
│   └── profile.yaml        ← written by setup skill
├── docs/
│   └── superpowers/specs/
│       └── 2026-05-03-linkedin-thought-leader-agent-design.md
├── tests/
│   └── (unit tests for execution scripts)
├── .env.example
├── .gitignore              ← excludes .env, credentials.json, token.json
├── requirements.txt
└── README.md
```

---

## Error Handling Philosophy

- **"No items to process"** is expected output, not an error. Cron exits cleanly. Skills report clearly.
- **API failures** are surfaced verbatim and leave data in a recoverable state (row stays `ready`).
- **Missing credentials** redirect to the setup skill — never silently fail.
- **Manual gates** (review → ready) are never automated. They are documented as intentional design choices.

---

## Open Questions / Future Scope

- Image generation (Gemini API) was in the original but excluded here for simplicity — can be added as an optional flag in `create-articles`
- Multi-language support (Dutch/English) could be a `brand_voice.md` config option
- A `report` skill showing posting history and engagement stats could be added later
