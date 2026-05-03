---
name: post-article
description: Publish a ready LinkedIn article immediately. Lists ready articles for the colleague to choose from, shows a preview, and posts on confirmation.
---

# Post Article

Publish a selected article to LinkedIn right now.

## Step 1: List Ready Articles

```bash
python -c "
from execution.sheets_client import get_rows
rows = get_rows('LinkedIn Posts', status_filter='ready')
if not rows:
    print('NO_READY')
else:
    for r in rows:
        score = len(r.get('text','')) // 100 + r.get('text','').count('#') + (2 if '?' in r.get('text','') else 0)
        print(f'Row {r[\"_row_number\"]:3} | Score {score:2} | {(r.get(\"title\") or r.get(\"about\",\"\"))[:55]}')
"
```

If output is `NO_READY`:
> "No ready articles found. Review your drafts in Google Sheets and mark approved ones as 'ready', then try again."
Stop here.

## Step 2: Select Article

If the colleague did not specify a row number, ask them to pick one from the list.

## Step 3: Show Preview

```bash
python -c "
from execution.sheets_client import get_rows
from execution.linkedin_client import build_post_text
rows = get_rows('LinkedIn Posts')
row = next((r for r in rows if r['_row_number'] == <row_number>), None)
if row:
    print(build_post_text(row.get('title',''), row.get('text','')))
"
```

Show the full post text to the colleague.

## Step 4: Confirm and Post

Ask: "Post this to LinkedIn now? (yes / no)"

On **yes**:
```bash
python -c "
from execution.sheets_client import get_rows, update_row
from execution.linkedin_client import post_text, build_post_text, urn_to_url
from datetime import datetime
rows = get_rows('LinkedIn Posts')
row = next((r for r in rows if r['_row_number'] == <row_number>), None)
if row:
    full_text = build_post_text(row.get('title',''), row.get('text',''))
    post_urn = post_text(full_text)
    if post_urn:
        url = urn_to_url(post_urn)
        update_row('LinkedIn Posts', <row_number>, {
            'status': 'posted',
            'date_posted': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'published_url': url,
        })
        print('SUCCESS:', url)
    else:
        print('FAILED')
"
```

On **SUCCESS**: tell the colleague the post URL.
On **FAILED**: tell the colleague the API call failed, the row stays 'ready' for retry. Suggest running `/setup` to check LinkedIn credentials.

On **no**: tell the colleague "Cancelled. The article stays in 'ready' status."

## Error Handling

- If `LINKEDIN_ACCESS_TOKEN` is not set: redirect to `/setup`
- If the selected row is not found or not in 'ready' status: report clearly and stop
