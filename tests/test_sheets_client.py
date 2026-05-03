import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from execution import sheets_client
from execution.sheets_client import POSTS_COLUMNS


def test_get_rows_returns_dicts_with_row_number(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'title', 'text', 'image_prompt', 'status',
             'scheduled_date', 'date_added', 'date_textgen', 'published_url', 'date_posted'],
            ['Manual', 'AI idea', '', '', '', 'new', '', '2026-01-01', '', '', ''],
        ]
    }
    rows = sheets_client.get_rows('LinkedIn Posts')
    assert len(rows) == 1
    assert rows[0]['about'] == 'AI idea'
    assert rows[0]['_row_number'] == 2


def test_get_rows_status_filter(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'status'],
            ['Manual', 'idea1', 'new'],
            ['Manual', 'idea2', 'ready'],
        ]
    }
    rows = sheets_client.get_rows('LinkedIn Posts', status_filter='new')
    assert len(rows) == 1
    assert rows[0]['about'] == 'idea1'


def test_get_rows_status_filter_case_insensitive(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'status'],
            ['Manual', 'idea1', 'Ready'],
        ]
    }
    rows = sheets_client.get_rows('LinkedIn Posts', status_filter='ready')
    assert len(rows) == 1


def test_append_idea_builds_correct_row(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().append().execute.return_value = {
        'updates': {'updatedCells': 11}
    }
    result = sheets_client.append_idea('Test idea', 'Manual', status='new')
    assert result > 0
    call_args = mock_sheets_service.spreadsheets().values().append.call_args
    body = call_args.kwargs['body']
    row = body['values'][0]
    assert row[POSTS_COLUMNS.index('about')] == 'Test idea'
    assert row[POSTS_COLUMNS.index('source')] == 'Manual'
    assert row[POSTS_COLUMNS.index('status')] == 'new'


def test_update_row_calls_batch_update(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [['source', 'about', 'status']]
    }
    mock_sheets_service.spreadsheets().values().batchUpdate().execute.return_value = {}
    result = sheets_client.update_row('LinkedIn Posts', 2, {'status': 'review'})
    assert result is True


def test_get_today_scheduled_post_returns_matching_row(mock_sheets_service):
    today = date.today().isoformat()
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'title', 'text', 'image_prompt', 'status',
             'scheduled_date', 'date_added', 'date_textgen', 'published_url', 'date_posted'],
            ['Manual', 'idea', 'Title', 'Post text', '', 'ready', today, '', '', '', ''],
        ]
    }
    post = sheets_client.get_today_scheduled_post()
    assert post is not None
    assert post['title'] == 'Title'


def test_get_today_scheduled_post_returns_none_when_no_match(mock_sheets_service):
    mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['source', 'about', 'status', 'scheduled_date'],
            ['Manual', 'idea', 'ready', '2020-01-01'],
        ]
    }
    post = sheets_client.get_today_scheduled_post()
    assert post is None
