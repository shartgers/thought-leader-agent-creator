import pytest
from unittest.mock import patch, MagicMock
from datetime import date


def _make_post(row_number=2, title='Test Title', text='Post body.', scheduled_date=None):
    return {
        '_row_number': row_number,
        'title': title,
        'text': text,
        'image_prompt': '',
        'status': 'ready',
        'scheduled_date': scheduled_date or date.today().isoformat(),
    }


def test_publish_today_posts_and_updates_sheet():
    post = _make_post()
    with patch('execution.publish_today.check_connectivity', return_value=True), \
         patch('execution.publish_today.get_today_scheduled_post', return_value=post), \
         patch('execution.publish_today.post_text', return_value='urn:li:share:999') as mock_post, \
         patch('execution.publish_today.update_row') as mock_update, \
         patch('execution.publish_today.urn_to_url', return_value='https://linkedin.com/feed/update/urn:li:share:999/'):
        from execution.publish_today import publish_today
        result = publish_today()
    assert result is True
    mock_post.assert_called_once()
    mock_update.assert_called_once()
    update_args = mock_update.call_args[0]
    assert update_args[2]['status'] == 'posted'
    assert 'published_url' in update_args[2]


def test_publish_today_exits_cleanly_when_no_post():
    with patch('execution.publish_today.check_connectivity', return_value=True), \
         patch('execution.publish_today.get_today_scheduled_post', return_value=None):
        from execution.publish_today import publish_today
        result = publish_today()
    assert result is True


def test_publish_today_returns_false_on_api_failure():
    post = _make_post()
    with patch('execution.publish_today.check_connectivity', return_value=True), \
         patch('execution.publish_today.get_today_scheduled_post', return_value=post), \
         patch('execution.publish_today.post_text', return_value=None):
        from execution.publish_today import publish_today
        result = publish_today()
    assert result is False


def test_publish_today_returns_false_when_connectivity_fails():
    with patch('execution.publish_today.check_connectivity', return_value=False):
        from execution.publish_today import publish_today
        result = publish_today()
    assert result is False


def test_publish_today_dry_run_does_not_call_api():
    post = _make_post()
    with patch('execution.publish_today.get_today_scheduled_post', return_value=post), \
         patch('execution.publish_today.post_text') as mock_post:
        from execution.publish_today import publish_today
        result = publish_today(dry_run=True)
    assert result is True
    mock_post.assert_not_called()
