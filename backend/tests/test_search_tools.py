"""Tests for search tools (CourseSearchTool and CourseOutlineTool)"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Tests for CourseSearchTool.execute()"""

    def test_execute_returns_formatted_results(self, mock_vector_store, sample_search_results):
        """Test that execute returns properly formatted results"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="python basics")

        # Verify the search was called
        mock_vector_store.search.assert_called_once_with(
            query="python basics",
            course_name=None,
            lesson_number=None
        )

        # Verify result is a string
        assert isinstance(result, str)
        assert "Introduction to Python" in result
        assert "Lesson 1" in result
        assert "python" in result.lower()

    def test_execute_with_course_name_filter(self, mock_vector_store, sample_search_results):
        """Test execute with course_name filter"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="functions", course_name="Python")

        # Verify the search was called with course_name
        mock_vector_store.search.assert_called_once_with(
            query="functions",
            course_name="Python",
            lesson_number=None
        )
        assert isinstance(result, str)

    def test_execute_with_lesson_filter(self, mock_vector_store, sample_search_results):
        """Test execute with lesson_number filter"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="variables", lesson_number=2)

        # Verify the search was called with lesson_number
        mock_vector_store.search.assert_called_once_with(
            query="variables",
            course_name=None,
            lesson_number=2
        )
        assert isinstance(result, str)

    def test_execute_with_both_filters(self, mock_vector_store, sample_search_results):
        """Test execute with both course_name and lesson_number filters"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(
            query="variables",
            course_name="Python",
            lesson_number=2
        )

        # Verify the search was called with both filters
        mock_vector_store.search.assert_called_once_with(
            query="variables",
            course_name="Python",
            lesson_number=2
        )
        assert isinstance(result, str)

    def test_execute_returns_error_when_search_fails(self, mock_vector_store, error_search_results):
        """Test that execute returns error message when search fails"""
        mock_vector_store.search.return_value = error_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="anything")

        # Should return the error message
        assert "Search failed" in result or "error" in result.lower()

    def test_execute_returns_no_results_message(self, mock_vector_store, empty_search_results):
        """Test that execute returns appropriate message for empty results"""
        mock_vector_store.search.return_value = empty_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="nonexistent topic")

        # Should indicate no results found
        assert "No relevant content found" in result

    def test_execute_returns_no_results_with_course_filter(self, mock_vector_store, empty_search_results):
        """Test empty results message includes filter information"""
        mock_vector_store.search.return_value = empty_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic", course_name="Advanced Python")

        assert "No relevant content found" in result
        assert "Advanced Python" in result

    def test_execute_returns_no_results_with_lesson_filter(self, mock_vector_store, empty_search_results):
        """Test empty results message includes lesson information"""
        mock_vector_store.search.return_value = empty_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic", lesson_number=5)

        assert "No relevant content found" in result
        assert "lesson 5" in result

    def test_execute_tracks_sources(self, mock_vector_store, sample_search_results):
        """Test that execute properly tracks sources for UI"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="python")

        # Check that sources were stored
        assert len(tool.last_sources) == 2
        assert tool.last_sources[0]["title"] == "Introduction to Python - Lesson 1"
        assert tool.last_sources[0]["url"] == "https://example.com/lesson/1"

    def test_get_tool_definition(self, mock_vector_store):
        """Test that get_tool_definition returns proper schema"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert "query" in definition["input_schema"]["properties"]
        assert "query" in definition["input_schema"]["required"]


class TestCourseOutlineTool:
    """Tests for CourseOutlineTool"""

    def test_execute_returns_course_outline(self, mock_vector_store):
        """Test that execute returns properly formatted course outline"""
        mock_vector_store.get_course_outline.return_value = {
            "course_title": "Introduction to Python",
            "course_link": "https://example.com/python",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Getting Started"},
                {"lesson_number": 2, "lesson_title": "Variables and Types"}
            ]
        }

        tool = CourseOutlineTool(mock_vector_store)
        result = tool.execute(course_title="Python")

        # Verify the call
        mock_vector_store.get_course_outline.assert_called_once_with("Python")

        # Verify output format
        assert "Course: Introduction to Python" in result
        assert "Link: https://example.com/python" in result
        assert "1. Getting Started" in result
        assert "2. Variables and Types" in result

    def test_execute_returns_not_found_message(self, mock_vector_store):
        """Test that execute returns not found message"""
        mock_vector_store.get_course_outline.return_value = None

        tool = CourseOutlineTool(mock_vector_store)
        result = tool.execute(course_title="Nonexistent Course")

        assert "No course found" in result

    def test_get_tool_definition(self, mock_vector_store):
        """Test that get_tool_definition returns proper schema"""
        tool = CourseOutlineTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "input_schema" in definition
        assert "course_title" in definition["input_schema"]["properties"]


class TestToolManager:
    """Tests for ToolManager"""

    def test_register_tool(self, mock_vector_store):
        """Test that tools can be registered"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test that tool definitions are returned correctly"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)

        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 2
        names = [d["name"] for d in definitions]
        assert "search_course_content" in names
        assert "get_course_outline" in names

    def test_execute_tool(self, mock_vector_store, sample_search_results):
        """Test that execute_tool properly calls the tool"""
        manager = ToolManager()
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="python")

        assert isinstance(result, str)
        assert "python" in result.lower()

    def test_execute_nonexistent_tool(self, mock_vector_store):
        """Test that executing nonexistent tool returns error"""
        manager = ToolManager()
        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """Test retrieving last sources from tool"""
        manager = ToolManager()
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute a search
        manager.execute_tool("search_course_content", query="python")

        # Get sources
        sources = manager.get_last_sources()

        assert len(sources) == 2
        assert sources[0]["title"] == "Introduction to Python - Lesson 1"

    def test_reset_sources(self, mock_vector_store, sample_search_results):
        """Test that sources can be reset"""
        manager = ToolManager()
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute a search
        manager.execute_tool("search_course_content", query="python")
        assert len(manager.get_last_sources()) > 0

        # Reset
        manager.reset_sources()
        assert len(manager.get_last_sources()) == 0
