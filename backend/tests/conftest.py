"""
Shared pytest configuration and fixtures for all test modules.
Adds the backend directory to sys.path so modules can be imported
without package-prefix notation (matching how the app itself imports them).
"""

import sys
import os
from unittest.mock import MagicMock

# Make backend/ importable as the root package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from vector_store import SearchResults

# ---------------------------------------------------------------------------
# SearchResults factories
# ---------------------------------------------------------------------------


def make_search_results(documents=None, metadata=None, distances=None):
    """Return a successful SearchResults with the given content."""
    docs = documents or []
    meta = metadata or []
    dist = distances or ([0.1] * len(docs))
    return SearchResults(documents=docs, metadata=meta, distances=dist, error=None)


def make_error_results(error_msg="Search error: connection failed"):
    """Return a SearchResults that carries an error."""
    return SearchResults.empty(error_msg)


# ---------------------------------------------------------------------------
# Anthropic message response factories
# ---------------------------------------------------------------------------


def make_text_response(text="Here is the answer."):
    """Mock a Claude response that returns text directly (no tool use)."""
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text

    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [content_block]
    return response


def make_tool_use_response(
    tool_name="search_course_content",
    tool_id="toolu_abc123",
    tool_input=None,
):
    """Mock a Claude response that requests a tool call."""
    tool_input = tool_input or {"query": "what is RAG?"}

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.id = tool_id
    tool_block.input = tool_input

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_block]
    return response


# ---------------------------------------------------------------------------
# Expose factories as fixtures so tests can request them
# ---------------------------------------------------------------------------


@pytest.fixture
def search_results_factory():
    return make_search_results


@pytest.fixture
def error_results_factory():
    return make_error_results


@pytest.fixture
def text_response_factory():
    return make_text_response


@pytest.fixture
def tool_use_response_factory():
    return make_tool_use_response


# ---------------------------------------------------------------------------
# RAGSystem mock for API endpoint tests
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """
    Fully configured mock RAGSystem for API endpoint tests.

    Provides realistic default return values so tests can assert on
    response shape without wiring up ChromaDB or the Anthropic API.
    """
    mock = MagicMock()
    mock.session_manager.create_session.return_value = "session-abc123"
    mock.query.return_value = (
        "RAG stands for Retrieval-Augmented Generation.",
        [{"label": "AI Course - Lesson 1", "url": "https://example.com/1"}],
    )
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python 101", "AI Fundamentals"],
    }
    return mock
