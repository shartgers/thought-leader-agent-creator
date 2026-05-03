import pytest
from unittest.mock import patch, MagicMock
from execution import linkedin_client


def test_build_post_text_with_title():
    result = linkedin_client.build_post_text('My Title', 'Post body here.')
    assert result == 'My Title\n\nPost body here.'


def test_build_post_text_no_title():
    result = linkedin_client.build_post_text('', 'Just the body.')
    assert result == 'Just the body.'


def test_urn_to_url():
    urn = 'urn:li:ugcPost:7123456789'
    url = linkedin_client.urn_to_url(urn)
    assert url == 'https://www.linkedin.com/feed/update/urn:li:ugcPost:7123456789/'


def test_post_text_success():
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {'x-restli-id': 'urn:li:ugcPost:9999'}

    with patch('execution.linkedin_client.requests.post', return_value=mock_response), \
         patch('execution.linkedin_client.ACCESS_TOKEN', 'fake-token'), \
         patch('execution.linkedin_client.PERSON_URN', '12345678'):
        result = linkedin_client.post_text('Hello LinkedIn!')
    assert result == 'urn:li:ugcPost:9999'


def test_post_text_failure_returns_none():
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = 'Unauthorized'

    with patch('execution.linkedin_client.requests.post', return_value=mock_response), \
         patch('execution.linkedin_client.ACCESS_TOKEN', 'fake-token'), \
         patch('execution.linkedin_client.PERSON_URN', '12345678'):
        result = linkedin_client.post_text('Hello LinkedIn!')
    assert result is None


def test_post_text_missing_token(monkeypatch):
    monkeypatch.setenv('LINKEDIN_ACCESS_TOKEN', '')
    # Re-import to pick up empty token
    import importlib
    import execution.linkedin_client as lc
    importlib.reload(lc)
    result = lc.post_text('test')
    assert result is None
