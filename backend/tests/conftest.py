import sys
import os

# Add backend and tests directories to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from unittest.mock import MagicMock, patch
from helpers import MockConfig, make_valid_search_results


@pytest.fixture
def mock_config():
    """Shared MockConfig instance."""
    return MockConfig()


@pytest.fixture
def mock_rag_system():
    """A MagicMock standing in for RAGSystem with pre-wired sub-components."""
    rag = MagicMock()
    rag.session_manager.create_session.return_value = "test-session-123"
    rag.query.return_value = (
        "This is a test answer.",
        ["Source A", "Source B"],
        ["http://example.com/a", "http://example.com/b"],
    )
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    return rag


@pytest.fixture
def mock_vector_store():
    """A MagicMock standing in for VectorStore."""
    store = MagicMock()
    store.get_course_count.return_value = 2
    store.get_existing_course_titles.return_value = ["Course A", "Course B"]
    store.search.return_value = make_valid_search_results(2)
    return store
