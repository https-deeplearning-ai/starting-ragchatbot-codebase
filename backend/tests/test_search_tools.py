"""Tests for CourseSearchTool.execute() and ToolManager dispatch."""

import pytest
from unittest.mock import MagicMock, patch
from helpers import make_search_results, make_valid_search_results
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_lesson_link = MagicMock(return_value="https://example.com/lesson")
    return store


@pytest.fixture
def search_tool(mock_store):
    return CourseSearchTool(mock_store)


@pytest.fixture
def tool_manager(search_tool):
    tm = ToolManager()
    tm.register_tool(search_tool)
    return tm


class TestCourseSearchToolExecute:
    def test_execute_returns_formatted_results(self, search_tool, mock_store):
        """Valid search results are formatted as [Course - Lesson N]\\ncontent."""
        results = make_valid_search_results(2)
        mock_store.search.return_value = results

        output = search_tool.execute(query="test query")

        assert "[Course 0 - Lesson 1]" in output
        assert "Content about topic 0" in output
        assert "[Course 1 - Lesson 2]" in output
        assert "Content about topic 1" in output

    def test_execute_populates_sources(self, search_tool, mock_store):
        """last_sources and last_source_links are populated after execution."""
        results = make_valid_search_results(2)
        mock_store.search.return_value = results

        search_tool.execute(query="test query")

        assert len(search_tool.last_sources) == 2
        assert "Course 0 - Lesson 1" in search_tool.last_sources
        assert len(search_tool.last_source_links) == 2

    def test_execute_error_from_search(self, search_tool, mock_store):
        """When SearchResults.error is set, execute returns the error string."""
        mock_store.search.return_value = make_search_results(
            error="No course found matching 'xyz'"
        )

        output = search_tool.execute(query="test", course_name="xyz")

        assert "No course found matching 'xyz'" in output

    def test_execute_empty_results(self, search_tool, mock_store):
        """When no documents found, returns 'No relevant content found'."""
        mock_store.search.return_value = make_search_results()

        output = search_tool.execute(query="nonexistent topic")

        assert "No relevant content found" in output

    def test_execute_empty_with_filters(self, search_tool, mock_store):
        """Empty results with course_name/lesson filters include filter info."""
        mock_store.search.return_value = make_search_results()

        output = search_tool.execute(query="topic", course_name="MCP", lesson_number=3)

        assert "in course 'MCP'" in output
        assert "in lesson 3" in output

    def test_execute_exception_propagates(self, search_tool, mock_store):
        """When store.search() raises, exception propagates (not caught)."""
        mock_store.search.side_effect = RuntimeError("DB connection failed")

        with pytest.raises(RuntimeError, match="DB connection failed"):
            search_tool.execute(query="test")

    def test_tool_definition_schema(self, search_tool):
        """Tool definition has correct name, required params, schema."""
        defn = search_tool.get_tool_definition()

        assert defn["name"] == "search_course_content"
        assert defn["input_schema"]["required"] == ["query"]
        assert "query" in defn["input_schema"]["properties"]
        assert "course_name" in defn["input_schema"]["properties"]
        assert "lesson_number" in defn["input_schema"]["properties"]


class TestToolManager:
    def test_dispatches_correctly(self, tool_manager, mock_store):
        """ToolManager.execute_tool dispatches to the right tool."""
        mock_store.search.return_value = make_valid_search_results(1)

        result = tool_manager.execute_tool("search_course_content", query="test query")

        mock_store.search.assert_called_once_with(
            query="test query", course_name=None, lesson_number=None
        )
        assert "[Course 0 - Lesson 1]" in result

    def test_unknown_tool_returns_error(self, tool_manager):
        """Unknown tool name returns error string, not exception."""
        result = tool_manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result.lower()
