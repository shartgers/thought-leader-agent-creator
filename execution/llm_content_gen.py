"""
Draft helpers for the LinkedIn thought leader pipeline.

Primary workflow (Claude Code / Cursor): the *host agent* writes each draft using
the same voice rules as build_system_prompt(), then saves to the sheet via
save_review_draft(). No API key is required for that path.

Optional workflow: set CLAUDE_API_KEY and call generate_draft() to generate drafts
from Python via the Anthropic API (CI, cron, or headless automation).
"""

import json
import os
import anthropic
from dotenv import load_dotenv

from execution.sheets_client import update_row

load_dotenv()

# Single place to update if Anthropic changes the model ID (API path only).
MODEL = 'claude-sonnet-4-6'


def build_system_prompt(brand_voice, themes, role):
    """
    Builds the system prompt from config parameters.

    Used by the host agent and by generate_draft() so voice rules stay identical.
    """
    return f"""You are a LinkedIn ghostwriter for a {role}.

Write in this voice and style:
{brand_voice}

The author publishes consistently around these 3 themes. Each article must align with one of them:
{themes}

Rules:
- 150-300 words
- Open with a hook (do NOT start with "I" or "In today's world")
- One clear insight or lesson per article
- Close with a question or call to action
- No generic AI filler. No marketing fluff.
- Output valid JSON only, no other text: {{"title": "...", "text": "...", "image_prompt": "..."}}"""


# Backwards compatibility for tests / older imports.
_build_system_prompt = build_system_prompt


def draft_prompt_for_idea(about, brand_voice, themes, role):
    """
    Returns the system and user messages for one idea.

    The hosting agent can follow these verbatim — no network call.
    """
    return {
        'system': build_system_prompt(brand_voice, themes, role),
        'user': f'Write a LinkedIn article about this idea: {about}',
    }


def validate_draft(draft):
    """
    Ensures a draft dict is safe to write to the sheet.

    Expects keys: title, text, image_prompt (non-empty strings).
    """
    if not isinstance(draft, dict):
        raise TypeError('draft must be a dict')
    missing = [k for k in ('title', 'text', 'image_prompt') if k not in draft]
    if missing:
        raise ValueError(f'draft missing keys: {missing}')
    for key in ('title', 'text', 'image_prompt'):
        val = draft.get(key)
        if val is None or not str(val).strip():
            raise ValueError(f'draft[{key!r}] must be a non-empty string')
    return draft


def save_review_draft(row_number, draft):
    """
    Validates draft fields and updates the sheet row to status=review.

    This is the normal save path when the host agent wrote the draft in-session.
    """
    from datetime import datetime

    validate_draft(draft)
    update_row('LinkedIn Posts', row_number, {
        'title': draft['title'],
        'text': draft['text'],
        'image_prompt': draft['image_prompt'],
        'status': 'review',
        'date_textgen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })


def _parse_response(text):
    """
    Extracts JSON from model response.
    Handles responses where the model wraps JSON in markdown code fences.
    Returns dict or raises ValueError.
    """
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        text = '\n'.join(lines[1:-1]) if lines[-1].strip() == '```' else '\n'.join(lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model response: {e}\nResponse: {text[:200]}")


def generate_draft(about, brand_voice, themes, role):
    """
    Generates a draft by calling the Anthropic API (optional).

    Requires CLAUDE_API_KEY. For day-to-day use in Claude Code / Cursor, prefer
    composing the draft in the agent and calling save_review_draft() instead.
    """
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        raise RuntimeError(
            'CLAUDE_API_KEY is not set. In Claude Code / Cursor, write each draft in-session '
            'using the same rules as build_system_prompt(), then call save_review_draft(row, draft). '
            'To generate from Python, add CLAUDE_API_KEY to .env (see .env.example).'
        )

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(brand_voice, themes, role)
    user_message = f"Write a LinkedIn article about this idea: {about}"

    for attempt in range(2):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_message}]
        )
        try:
            parsed = _parse_response(response.content[0].text)
            validate_draft(parsed)
            return parsed
        except ValueError:
            if attempt == 1:
                raise
            print(f"  WARNING: JSON parse failed on attempt 1, retrying...")
