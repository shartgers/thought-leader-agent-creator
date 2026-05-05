---
name: create-articles
description: Generate LinkedIn article drafts from all ideas with status=new. Uses the colleague's brand voice and content themes. Updates sheet status to 'review' when done.
---

# Create Articles

Generate LinkedIn drafts for all new ideas using the colleague's brand voice and content themes.

Drafts are written **by you (this agent)** using the same rules as `execution/llm_content_gen.build_system_prompt`. Python only validates and writes to Google Sheets — **no `CLAUDE_API_KEY` is required** for this skill.

Optional: to generate drafts from a shell script with `generate_draft()`, set `CLAUDE_API_KEY` in `.env` (see `.env.example`).

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

## Step 3: For Each New Idea, Draft In-Session Then Save

For each row with status `new`:

1. Read `about` from the row.
2. Compose `title`, `text`, and `image_prompt` following **exactly** the rules embedded in `execution/llm_content_gen.build_system_prompt()` (hook opening, 150–300 words, one theme, JSON-shaped fields).
3. Save to the sheet with:

```bash
python -c "
from execution.llm_content_gen import save_review_draft

draft = {
    'title': '<title>',
    'text': '<full post body>',
    'image_prompt': '<short image description>',
}
save_review_draft(<row_number>, draft)
print('Saved:', draft['title'])
"
```

Replace placeholders with real values. Run once per idea.

`save_review_draft` validates fields and sets `status` to `review` and `date_textgen` automatically.

## Step 4: Report

Tell the colleague how many drafts were created and link to the sheet:

> "X drafts created and set to 'review'.
> Open your Google Sheet to review them: https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
> Change any you approve to 'ready' status, then run `/schedule` or `/post-article`."

Read `GOOGLE_SHEET_ID` from `.env` to build the URL.
