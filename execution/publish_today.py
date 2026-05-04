"""
publish_today.py — Publish today's scheduled LinkedIn post.

Called by the Claude CronCreate daily routine at 08:15 Europe/Amsterdam.
Finds the single post with status=ready and scheduled_date=today.
Publishes it and updates the sheet. Exits cleanly if nothing is scheduled.

Usage:
    python execution/publish_today.py [--dry-run]
"""

import sys
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ = ZoneInfo('Europe/Amsterdam')

sys.path.insert(0, '.')

from execution.sheets_client import get_today_scheduled_post, update_row
from execution.linkedin_client import post_text, build_post_text, urn_to_url


def publish_today(dry_run=False):
    now = datetime.now(_TZ)
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S %Z')}] publish_today starting")
    print(f"  Date : {now.date().isoformat()}")
    print(f"  Mode : {'DRY RUN' if dry_run else 'LIVE'}")

    post = get_today_scheduled_post()

    if not post:
        print("  Result: No post scheduled for today. Nothing to publish.")
        return True

    row_number = post['_row_number']
    title = post.get('title', '(no title)')
    text = post.get('text', '')

    print(f"  Post  : Row {row_number} — {title[:60]}")

    if not text:
        print("  Error : Post has no text content. Aborting.")
        return False

    full_text = build_post_text(title, text)

    if dry_run:
        print(f"  [DRY RUN] Would publish: {full_text[:200]}...")
        return True

    post_urn = post_text(full_text)

    if post_urn:
        published_url = urn_to_url(post_urn)
        update_row('LinkedIn Posts', row_number, {
            'status': 'posted',
            'date_posted': now.strftime('%Y-%m-%d %H:%M:%S'),
            'published_url': published_url,
        })
        print(f"  Result: Published — {published_url}")
        return True
    else:
        print("  Result: FAILED — LinkedIn API error. Row stays 'ready' for retry.")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Publish today's scheduled LinkedIn post")
    parser.add_argument('--dry-run', action='store_true', help='Simulate without posting')
    args = parser.parse_args()
    success = publish_today(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
