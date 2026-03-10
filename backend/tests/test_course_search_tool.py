"""
Tests for CourseSearchTool.execute()

Only VectorStore is mocked; the tool itself runs unpatched so any bug in
_format_results() or execute() is caught directly.
"""

import pytest
from unittest.mock import MagicMock

from helpers import build_text_response, build_tool_use_response
from vector_store import SearchResults
from search_tools import CourseSearchTool


@pytest.fixture
def search_tool(mock_vector_store, sample_search_results):
    """CourseSearchTool backed by a mock store that returns sample results"""
    mock_vector_store.search.return_value = sample_search_results
    return CourseSearchTool(mock_vector_store)


# ── result format ─────────────────────────────────────────────────────────────


def test_execute_returns_string(search_tool):
    result = search_tool.execute(query="What is Python?")
    assert isinstance(result, str) and len(result) > 0


def test_execute_formatted_content_includes_course_header(search_tool):
    result = search_tool.execute(query="What is Python?")
    assert "[Intro to Python - Lesson 1]" in result


# ── sources format ────────────────────────────────────────────────────────────


def test_execute_sources_are_list_of_dicts(search_tool):
    """Sources must be List[Dict]; returning List[str] causes a Pydantic 500"""
    search_tool.execute(query="What is Python?")
    assert len(search_tool.last_sources) > 0
    src = search_tool.last_sources[0]
    assert isinstance(src, dict), f"Expected dict, got {type(src)}"
    assert "label" in src
    assert "url" in src


def test_execute_sources_label_format(search_tool):
    search_tool.execute(query="What is Python?")
    assert search_tool.last_sources[0]["label"] == "Intro to Python - Lesson 1"


def test_execute_calls_get_lesson_link_with_correct_args(
    search_tool, mock_vector_store
):
    search_tool.execute(query="What is Python?")
    mock_vector_store.get_lesson_link.assert_called_with("Intro to Python", 1)


def test_execute_url_in_sources_from_get_lesson_link(search_tool, mock_vector_store):
    mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/1"
    search_tool.execute(query="What is Python?")
    assert search_tool.last_sources[0]["url"] == "https://example.com/lesson/1"


def test_execute_url_none_when_no_lesson_number(mock_vector_store):
    """When metadata has no lesson_number, get_lesson_link must not be called"""
    results = SearchResults(
        documents=["Content without lesson number"],
        metadata=[{"course_title": "Intro to Python"}],  # no lesson_number key
        distances=[0.1],
    )
    mock_vector_store.search.return_value = results
    tool = CourseSearchTool(mock_vector_store)
    tool.execute(query="What is Python?")
    mock_vector_store.get_lesson_link.assert_not_called()
    assert tool.last_sources[0]["url"] is None


# ── error / empty paths ───────────────────────────────────────────────────────


def test_execute_with_search_error_returns_error_string(
    mock_vector_store, error_search_results
):
    mock_vector_store.search.return_value = error_search_results
    tool = CourseSearchTool(mock_vector_store)
    result = tool.execute(query="What is Python?")
    assert isinstance(result, str)
    assert "error" in result.lower() or "Search error" in result


def test_execute_with_empty_results_returns_no_content_message(
    mock_vector_store, empty_search_results
):
    mock_vector_store.search.return_value = empty_search_results
    tool = CourseSearchTool(mock_vector_store)
    result = tool.execute(query="What is Python?")
    assert result.startswith("No relevant content found")


def test_execute_empty_with_course_filter_includes_course_in_message(
    mock_vector_store, empty_search_results
):
    mock_vector_store.search.return_value = empty_search_results
    tool = CourseSearchTool(mock_vector_store)
    result = tool.execute(query="What is Python?", course_name="Intro to Python")
    assert "in course 'Intro to Python'" in result


# ── parameter forwarding ──────────────────────────────────────────────────────


def test_execute_forwards_course_name_to_vector_store(
    mock_vector_store, sample_search_results
):
    mock_vector_store.search.return_value = sample_search_results
    tool = CourseSearchTool(mock_vector_store)
    tool.execute(query="What is Python?", course_name="Intro to Python")
    mock_vector_store.search.assert_called_once_with(
        query="What is Python?",
        course_name="Intro to Python",
        lesson_number=None,
    )


def test_execute_forwards_lesson_number_to_vector_store(
    mock_vector_store, sample_search_results
):
    mock_vector_store.search.return_value = sample_search_results
    tool = CourseSearchTool(mock_vector_store)
    tool.execute(query="What is Python?", lesson_number=3)
    mock_vector_store.search.assert_called_once_with(
        query="What is Python?",
        course_name=None,
        lesson_number=3,
    )


# ── stale-state detection ─────────────────────────────────────────────────────


def test_last_sources_reset_between_calls(
    mock_vector_store, sample_search_results, empty_search_results
):
    """After an empty-result call last_sources must be [] — stale sources must not leak"""
    mock_vector_store.search.return_value = sample_search_results
    tool = CourseSearchTool(mock_vector_store)
    tool.execute(query="What is Python?")
    assert len(tool.last_sources) > 0, "Precondition: first call must populate sources"

    mock_vector_store.search.return_value = empty_search_results
    tool.execute(query="What else?")
    assert tool.last_sources == [], f"Expected [], got {tool.last_sources}"
