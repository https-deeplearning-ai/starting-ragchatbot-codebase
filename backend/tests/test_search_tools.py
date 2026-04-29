import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool
from tests.helpers import make_search_results


def _make_tool(store=None):
    if store is None:
        store = MagicMock()
        store.get_lesson_link.return_value = None
    return CourseSearchTool(vector_store=store)


class TestCourseSearchToolExecute:

    def test_happy_path_returns_formatted_results(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            documents=["LLMs are large language models."],
            metadata=[{"course_title": "AI Course", "lesson_number": 2}],
            distances=[0.05],
        )
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="What is an LLM?")
        assert "[AI Course - Lesson 2]" in result
        assert "LLMs are large language models." in result

    def test_happy_path_populates_last_sources(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            documents=["Content A"],
            metadata=[{"course_title": "My Course", "lesson_number": 3}],
            distances=[0.1],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/3"
        tool = _make_tool(mock_vector_store)
        tool.execute(query="anything")
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "My Course - Lesson 3"
        assert tool.last_sources[0]["url"] == "https://example.com/3"

    def test_empty_results_returns_no_content_message(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results()
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="unknown topic")
        assert result == "No relevant content found."

    def test_empty_results_sources_are_empty(self, mock_vector_store):
        """
        EXPECTED FAIL on current code.
        Bug: last_sources is only written inside _format_results. When results
        are empty, _format_results is never called, so stale last_sources from a
        previous call persists.
        Fix: clear last_sources at the top of execute() before any branching.
        """
        mock_vector_store.search.return_value = make_search_results()
        tool = _make_tool(mock_vector_store)
        tool.last_sources = [{"text": "stale", "url": None}]  # simulate prior call
        tool.execute(query="nothing")
        assert tool.last_sources == []  # FAILS on current code

    def test_empty_results_with_lesson_zero_filter(self, mock_vector_store):
        """
        EXPECTED FAIL on current code.
        Bug: `if lesson_number:` is falsy for 0, so the filter info "in lesson 0"
        is silently dropped from the error message.
        Fix: change to `if lesson_number is not None:`.
        """
        mock_vector_store.search.return_value = make_search_results()
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="intro", lesson_number=0)
        assert "in lesson 0" in result  # FAILS on current code

    def test_error_from_store_is_propagated(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            error="No course found matching 'nonexistent'"
        )
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="anything", course_name="nonexistent")
        assert result == "No course found matching 'nonexistent'"

    def test_course_name_filter_passed_to_store(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results()
        tool = _make_tool(mock_vector_store)
        tool.execute(query="loops", course_name="Python Basics")
        mock_vector_store.search.assert_called_once_with(
            query="loops", course_name="Python Basics", lesson_number=None
        )

    def test_lesson_number_filter_passed_to_store(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results()
        tool = _make_tool(mock_vector_store)
        tool.execute(query="decorators", lesson_number=4)
        mock_vector_store.search.assert_called_once_with(
            query="decorators", course_name=None, lesson_number=4
        )
