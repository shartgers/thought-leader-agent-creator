---
name: create-articles
description: Generate LinkedIn article drafts from all ideas with status=new. Uses the colleague's brand voice and content themes. Updates sheet status to 'review' when done.
---

# Create Articles

Generate LinkedIn drafts for all new ideas using the colleague's brand voice and content themes.

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

## Step 3: Generate Drafts

For each new idea row, run:
```bash
python -c "
import yaml
from pathlib import Path
from execution.llm_content_gen import generate_draft
from execution.sheets_client import update_row
from datetime import datetime

brand_voice = Path('config/brand_voice.md').read_text()
themes_raw = yaml.safe_load(Path('config/themes.yaml').read_text())
themes = '\n'.join(f'{i+1}. {t[\"name\"]}: {t[\"description\"]}' for i, t in enumerate(themes_raw['themes']))
profile = yaml.safe_load(Path('config/profile.yaml').read_text())
role = profile.get('role', 'professional')

draft = generate_draft('<about>', brand_voice, themes, role)
update_row('LinkedIn Posts', <row_number>, {
    'title': draft['title'],
    'text': draft['text'],
    'image_prompt': draft['image_prompt'],
    'status': 'review',
    'date_textgen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
})
print('Done:', draft['title'])
"
```

Replace `<about>` and `<row_number>` with actual values. Run once per idea.

## Step 4: Report

Tell the colleague how many drafts were created and link to the sheet:
> "X drafts created and set to 'review'.
> Open your Google Sheet to review them: https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
> Change any you approve to 'ready' status, then run `/schedule` or `/post-article`."

Read `GOOGLE_SHEET_ID` from `.env` to build the URL.
