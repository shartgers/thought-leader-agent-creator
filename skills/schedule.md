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
