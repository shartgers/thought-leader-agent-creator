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
