import json
import os
import pytest
from unittest.mock import MagicMock, patch
from execution import llm_content_gen

SAMPLE_BRAND_VOICE = "Write concisely. No fluff. Use short sentences."
SAMPLE_THEMES = "1. AI in operations\n2. Leadership lessons\n3. Digital transformation"
SAMPLE_ROLE = "Operations Director"
SAMPLE_ABOUT = "How AI is changing supply chain management"

VALID_RESPONSE = json.dumps({
    "title": "AI Is Rewriting the Supply Chain",
    "text": "Five years ago, predicting demand meant gut feel and spreadsheets.\n\nToday, AI models do it in seconds.\n\nWhat does that mean for operations leaders?",
    "image_prompt": "Futuristic warehouse with robotic arms and digital overlays"
})


def _api_env():
    """generate_draft() reads CLAUDE_API_KEY at runtime; patch for tests."""
    return patch.dict(os.environ, {'CLAUDE_API_KEY': 'sk-test-key'}, clear=False)


def test_generate_draft_returns_expected_fields():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=VALID_RESPONSE)]
    )
    with _api_env(), patch('execution.llm_content_gen.anthropic.Anthropic', return_value=mock_client):
        result = llm_content_gen.generate_draft(
            SAMPLE_ABOUT, SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE
        )
    assert 'title' in result
    assert 'text' in result
    assert 'image_prompt' in result
    assert result['title'] == "AI Is Rewriting the Supply Chain"


def test_generate_draft_retries_on_json_parse_failure():
    bad_response = "Here is your post: some plain text without JSON"
    good_response = VALID_RESPONSE

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        MagicMock(content=[MagicMock(text=bad_response)]),
        MagicMock(content=[MagicMock(text=good_response)]),
    ]
    with _api_env(), patch('execution.llm_content_gen.anthropic.Anthropic', return_value=mock_client):
        result = llm_content_gen.generate_draft(
            SAMPLE_ABOUT, SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE
        )
    assert result['title'] == "AI Is Rewriting the Supply Chain"
    assert mock_client.messages.create.call_count == 2


def test_generate_draft_raises_after_two_failures():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="not json at all")]
    )
    with _api_env(), patch('execution.llm_content_gen.anthropic.Anthropic', return_value=mock_client):
        with pytest.raises(ValueError, match="Failed to parse"):
            llm_content_gen.generate_draft(
                SAMPLE_ABOUT, SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE
            )


def test_generate_draft_requires_api_key():
    with patch('execution.llm_content_gen.os.getenv', return_value=None):
        with pytest.raises(RuntimeError, match='CLAUDE_API_KEY'):
            llm_content_gen.generate_draft(
                SAMPLE_ABOUT, SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE
            )


def test_build_system_prompt_includes_role_and_voice():
    prompt = llm_content_gen.build_system_prompt(SAMPLE_BRAND_VOICE, SAMPLE_THEMES, SAMPLE_ROLE)
    assert SAMPLE_ROLE in prompt
    assert SAMPLE_BRAND_VOICE in prompt
    assert SAMPLE_THEMES in prompt


def test_validate_draft_accepts_complete_dict():
    d = json.loads(VALID_RESPONSE)
    assert llm_content_gen.validate_draft(d) is d


def test_validate_draft_rejects_incomplete():
    with pytest.raises(ValueError, match='missing'):
        llm_content_gen.validate_draft({'title': 'x'})


def test_save_review_draft_calls_update_row():
    draft = json.loads(VALID_RESPONSE)
    with patch('execution.llm_content_gen.update_row') as mock_update:
        llm_content_gen.save_review_draft(12, draft)
    mock_update.assert_called_once()
    args, kwargs = mock_update.call_args
    assert args[0] == 'LinkedIn Posts'
    assert args[1] == 12
    payload = args[2]
    assert payload['status'] == 'review'
    assert payload['title'] == draft['title']
    assert 'date_textgen' in payload
