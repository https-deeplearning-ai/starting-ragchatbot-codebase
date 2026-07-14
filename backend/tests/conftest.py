"""Shared fixtures for RAG backend tests."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Ensure backend/ is on sys.path so imports like `from search_tools import ...` work
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from vector_store import SearchResults  # noqa: E402


@pytest.fixture
def sample_search_results():
    """Non-empty SearchResults with course/lesson metadata."""
    return SearchResults(
        documents=["RAG combines retrieval with generation for grounded answers."],
        metadata=[
            {
                "course_title": "Advanced Retrieval for AI with Chroma",
                "lesson_number": 1,
            }
        ],
        distances=[0.12],
    )


@pytest.fixture
def empty_search_results():
    """Empty SearchResults with no error."""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """SearchResults carrying an error message."""
    return SearchResults.empty("Search error: n_results must be a positive integer")


@pytest.fixture
def mock_vector_store():
    """MagicMock stand-in for VectorStore."""
    store = MagicMock()
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    return store


@pytest.fixture
def search_course_content_tool_def():
    """Minimal Anthropic tool definition for search_course_content."""
    return {
        "name": "search_course_content",
        "description": "Search course materials",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "course_name": {"type": "string"},
                "lesson_number": {"type": "integer"},
            },
            "required": ["query"],
        },
    }


def make_text_block(text: str):
    """Create a mock Anthropic text content block."""
    return SimpleNamespace(type="text", text=text)


def make_tool_use_block(
    name: str = "search_course_content",
    tool_input: dict | None = None,
    tool_id: str = "toolu_123",
):
    """Create a mock Anthropic tool_use content block."""
    return SimpleNamespace(
        type="tool_use",
        id=tool_id,
        name=name,
        input=tool_input or {"query": "What is RAG?", "course_name": "Chroma"},
    )


def make_api_response(content, stop_reason: str = "end_turn"):
    """Create a mock Anthropic messages.create response."""
    return SimpleNamespace(content=content, stop_reason=stop_reason)
