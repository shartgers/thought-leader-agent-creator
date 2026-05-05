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

## Step 5: Set Up Daily Cloud Routine

Check if a cloud routine already exists:

```
RemoteTrigger({"action": "list"})
```

Scan the returned triggers for one whose name contains "LinkedIn Auto-Publisher". If one is already active: tell the colleague, show its claude.ai URL, and offer to remove it.

If no routine exists, build the prompt first, then create the cloud routine.

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

### Creating the cloud routine

Call RemoteTrigger with action `"create"` and this body:

```json
{
  "name": "LinkedIn Auto-Publisher — [NAME] at [COMPANY]",
  "prompt": "<full routine prompt built above>",
  "schedule": "15 8 * * *",
  "timezone": "Europe/Amsterdam"
}
```

- **Schedule:** `15 8 * * *` = 08:15 daily in `Europe/Amsterdam` (handles CET/CEST automatically)
- **No MCP connectors** (Python scripts use embedded credentials)

After creating, relay the server-confirmed run time and the claude.ai routine URL to the colleague so they can verify the schedule and bookmark the result page.

The routine runs every day in the cloud — no session needs to be open. The script itself checks whether a post is scheduled for that day; if none is found it exits cleanly with "No post scheduled for today". Posting frequency is controlled by the dates written to the sheet, not the cron cadence.

## Step 6: Confirm

> "Schedule saved. Posts are queued for:
> [list the dates]
>
> The daily cloud routine will check at 08:15 Amsterdam time and publish automatically — no session needs to be open.
> You can view the routine and its run history at: [claude.ai routine URL]
>
> To add more articles to the schedule later, just run `/schedule` again after approving new drafts."

## Removing the Routine

If the colleague asks to remove the auto-publish routine:

1. Call `RemoteTrigger({"action": "list"})` to find the trigger ID
2. Call `RemoteTrigger({"action": "update", "trigger_id": "<id>", "body": {"enabled": false}})` to disable it
3. Confirm to the colleague that the routine has been disabled
