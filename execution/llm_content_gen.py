"""
LLM content generator for LinkedIn thought leader pipeline.

Generates LinkedIn article drafts using the Anthropic Claude API.
All context (brand voice, themes, role) passed as parameters — no hardcoded prompts.
"""

import json
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
MODEL = 'claude-sonnet-4-6'  # single place to update if Anthropic changes the model ID


def _build_system_prompt(brand_voice, themes, role):
    """Builds the system prompt from config parameters."""
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
    Generates a LinkedIn article draft for the given idea.

    Args:
        about: The idea or topic to write about
        brand_voice: Contents of config/brand_voice.md
        themes: Formatted string of 3 content themes
        role: The author's professional role

    Returns:
        Dict with keys: title, text, image_prompt

    Raises:
        ValueError: If the model fails to return valid JSON after 2 attempts
    """
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    system_prompt = _build_system_prompt(brand_voice, themes, role)
    user_message = f"Write a LinkedIn article about this idea: {about}"

    for attempt in range(2):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_message}]
        )
        try:
            return _parse_response(response.content[0].text)
        except ValueError:
            if attempt == 1:
                raise
            print(f"  WARNING: JSON parse failed on attempt 1, retrying...")
