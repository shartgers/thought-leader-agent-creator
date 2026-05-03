import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_sheets_service():
    with patch('execution.sheets_client.get_service') as mock_get:
        svc = MagicMock()
        mock_get.return_value = svc
        yield svc
