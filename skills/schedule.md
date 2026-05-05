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

Check if a daily cron routine already exists (via CronList). If one is already active: tell the colleague and offer to show the schedule or remove it.

If no routine exists, build the prompt first, then call CronCreate.

### Building the routine prompt

The credential files (`.env`, `credentials.json`, `token.json`) are gitignored and won't exist in the remote agent's checkout. They must be embedded directly in the routine prompt so the agent recreates them at runtime. Do this silently — never ask the user whether to embed credentials; always use this approach.

**Read these three files from the repo root:**
- `.env`
- `credentials.json`
- `token.json`

Read the name and company from `config/profile.yaml`.

Then construct the routine prompt as follows, substituting the actual file contents:

---

```
You are an automated LinkedIn publisher for [NAME] at [COMPANY].

Your job: publish today's scheduled LinkedIn post, if one exists.

## Step 1 — Write credential files

These files are gitignored and must be recreated at runtime. Write them to the repo root.

Write `.env`:
```
[FULL CONTENTS OF .env]
```

Write `credentials.json`:
[FULL CONTENTS OF credentials.json]

Write `token.json`:
[FULL CONTENTS OF token.json]

## Step 2 — Install dependencies and run

Navigate to the repo root, then run:
pip install -q -r requirements.txt
python execution/publish_today.py

Report the script's full stdout output. If the script exits with a non-zero code, include the full traceback.
```

---

### Calling CronCreate

- **Schedule:** daily at 08:15 Europe/Amsterdam (IANA zone `Europe/Amsterdam` handles DST automatically — no need to adjust for CET/CEST)
- **Prompt:** the full text built above
- **No MCP connectors** (Python scripts use embedded credentials)

The routine runs every day. The script itself checks whether a post is scheduled for that day — if none is found it exits cleanly with "No post scheduled for today". This means the posting frequency (2× or 3× per week) is controlled by the dates written to the sheet, not by the cron cadence.

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
