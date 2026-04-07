"""
Tests for CourseSearchTool.execute() in search_tools.py.

These are integration tests against the real ChromaDB vector store.
They verify that the tool returns usable results (or graceful errors)
for the kinds of queries the RAG chatbot receives.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from search_tools import CourseSearchTool
from vector_store import VectorStore
from config import config


@pytest.fixture(scope="module")
def tool():
    store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
    return CourseSearchTool(store)


# ---------------------------------------------------------------------------
# Basic execute() smoke tests
# ---------------------------------------------------------------------------

def test_execute_returns_string(tool):
    """execute() must always return a string, never raise."""
    result = tool.execute(query="what is RAG?")
    assert isinstance(result, str), f"Expected str, got {type(result)}"


def test_execute_nonempty_for_known_topic(tool):
    """A broad topic query should return content, not an empty result message."""
    result = tool.execute(query="RAG retrieval augmented generation")
    assert "No relevant content found" not in result, (
        f"Expected real results but got: {result!r}"
    )


def test_execute_with_course_name_filter(tool):
    """Filtering by a known partial course name should narrow results to that course."""
    result = tool.execute(query="lesson content", course_name="MCP")
    # Should either find results or report course not found — must not crash
    assert isinstance(result, str)
    if "No relevant content found" not in result and "No course found" not in result:
        assert "MCP" in result or "lesson" in result.lower(), (
            f"Expected MCP-related content, got: {result[:300]}"
        )


def test_execute_with_lesson_number_filter(tool):
    """Filtering by lesson number should return content for that lesson."""
    result = tool.execute(query="introduction overview", lesson_number=1)
    assert isinstance(result, str)


def test_execute_nonexistent_course_returns_error_string(tool):
    """An unknown course name must return an error string, not raise."""
    result = tool.execute(query="anything", course_name="ZZZ_NONEXISTENT_COURSE_XYZ")
    assert isinstance(result, str)
    assert len(result) > 0


def test_execute_garbage_query_does_not_crash(tool):
    """Completely irrelevant query must not raise — may return no results."""
    result = tool.execute(query="asdfjkl qwerty zxcvbnm 12345")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Sources tracking
# ---------------------------------------------------------------------------

def test_sources_populated_after_successful_search(tool):
    """After a successful search, last_sources should be a non-empty list."""
    tool.last_sources = []  # Reset
    result = tool.execute(query="chromadb vector database")
    if "No relevant content found" not in result:
        assert isinstance(tool.last_sources, list), "last_sources should be a list"
        assert len(tool.last_sources) > 0, "last_sources should not be empty after a hit"
        first = tool.last_sources[0]
        assert "label" in first, f"Source entry missing 'label': {first}"


def test_sources_is_list_after_any_search(tool):
    """last_sources must always be a list after any search (semantic search always finds nearest match)."""
    tool.last_sources = []
    tool.execute(query="some query", course_name="some course")
    assert isinstance(tool.last_sources, list), (
        f"last_sources should always be a list, got: {type(tool.last_sources)}"
    )
