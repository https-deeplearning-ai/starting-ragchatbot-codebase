import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.get_lesson_link.return_value = None
    return store
