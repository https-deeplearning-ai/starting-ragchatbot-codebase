"""Tests for CourseSearchTool, CourseOutlineTool, and ToolManager"""

import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolDefinition:
    """Test CourseSearchTool tool definition"""

    def test_get_tool_definition_has_correct_name(self, mock_vector_store):
        """Test tool definition has correct name"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"

    def test_get_tool_definition_has_input_schema(self, mock_vector_store):
        """Test tool definition has input schema"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"

    def test_get_tool_definition_has_required_query(self, mock_vector_store):
        """Test tool definition requires query parameter"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert "query" in definition["input_schema"]["properties"]
        assert "query" in definition["input_schema"]["required"]

    def test_get_tool_definition_has_optional_filters(self, mock_vector_store):
        """Test tool definition has optional course_name and lesson_number"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        properties = definition["input_schema"]["properties"]
        assert "course_name" in properties
        assert "lesson_number" in properties
        # These should NOT be required
        assert "course_name" not in definition["input_schema"]["required"]
        assert "lesson_number" not in definition["input_schema"]["required"]


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() method"""

    def test_execute_returns_formatted_results(self, mock_vector_store, valid_search_results):
        """Test execute returns properly formatted search results"""
        mock_vector_store.search.return_value = valid_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="machine learning")

        assert "[Introduction to AI" in result
        assert "machine learning fundamentals" in result

    def test_execute_calls_vector_store_search(self, mock_vector_store, valid_search_results):
        """Test execute calls vector store with correct parameters"""
        mock_vector_store.search.return_value = valid_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test query")

        mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name=None,
            lesson_number=None
        )

    def test_execute_passes_course_name_filter(self, mock_vector_store, valid_search_results):
        """Test execute passes course_name filter to vector store"""
        mock_vector_store.search.return_value = valid_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="neural networks", course_name="AI Course")

        mock_vector_store.search.assert_called_once_with(
            query="neural networks",
            course_name="AI Course",
            lesson_number=None
        )

    def test_execute_passes_lesson_number_filter(self, mock_vector_store, valid_search_results):
        """Test execute passes lesson_number filter to vector store"""
        mock_vector_store.search.return_value = valid_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="transformers", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="transformers",
            course_name=None,
            lesson_number=3
        )

    def test_execute_passes_both_filters(self, mock_vector_store, valid_search_results):
        """Test execute passes both filters to vector store"""
        mock_vector_store.search.return_value = valid_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="attention", course_name="ML Course", lesson_number=5)

        mock_vector_store.search.assert_called_once_with(
            query="attention",
            course_name="ML Course",
            lesson_number=5
        )

    def test_execute_handles_empty_results(self, mock_vector_store, empty_search_results):
        """Test execute returns appropriate message for empty results"""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_handles_empty_results_with_course_filter(self, mock_vector_store, empty_search_results):
        """Test empty results message includes course filter context"""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="nonexistent", course_name="Test Course")

        assert "No relevant content found" in result
        assert "Test Course" in result

    def test_execute_handles_empty_results_with_lesson_filter(self, mock_vector_store, empty_search_results):
        """Test empty results message includes lesson filter context"""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="nonexistent", lesson_number=5)

        assert "No relevant content found" in result
        assert "lesson 5" in result

    def test_execute_handles_empty_results_with_both_filters(self, mock_vector_store, empty_search_results):
        """Test empty results message includes both filter contexts"""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(
            query="nonexistent",
            course_name="Test Course",
            lesson_number=5
        )

        assert "No relevant content found" in result
        assert "Test Course" in result
        assert "lesson 5" in result

    def test_execute_handles_search_error(self, mock_vector_store, error_search_results):
        """Test execute returns error message when search fails"""
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="anything")

        assert "No course found matching" in result

    def test_execute_populates_last_sources(self, mock_vector_store, valid_search_results):
        """Test that last_sources is populated after search"""
        mock_vector_store.search.return_value = valid_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"
        mock_vector_store.get_course_link.return_value = "https://example.com/course"

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        assert len(tool.last_sources) > 0
        for source in tool.last_sources:
            assert "text" in source
            assert "link" in source

    def test_execute_deduplicates_sources(self, mock_vector_store):
        """Test that duplicate sources are removed"""
        duplicate_results = SearchResults(
            documents=["Content 1", "Content 2", "Content 3"],
            metadata=[
                {"course_title": "Same Course", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "Same Course", "lesson_number": 1, "chunk_index": 1},
                {"course_title": "Same Course", "lesson_number": 2, "chunk_index": 2}
            ],
            distances=[0.1, 0.2, 0.3]
        )
        mock_vector_store.search.return_value = duplicate_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        # Should have 2 unique sources (lesson 1 and lesson 2), not 3
        assert len(tool.last_sources) == 2


class TestCourseSearchToolFormatResults:
    """Test CourseSearchTool._format_results() method"""

    def test_format_results_includes_course_header(self, mock_vector_store, single_result_search):
        """Test that formatted results include course title header"""
        mock_vector_store.search.return_value = single_result_search
        mock_vector_store.get_lesson_link.return_value = "https://example.com"

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        assert "[Building Towards Computer Use" in result

    def test_format_results_includes_lesson_number(self, mock_vector_store, single_result_search):
        """Test that formatted results include lesson number"""
        mock_vector_store.search.return_value = single_result_search
        mock_vector_store.get_lesson_link.return_value = "https://example.com"

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        assert "Lesson 3" in result

    def test_format_results_includes_content(self, mock_vector_store, single_result_search):
        """Test that formatted results include actual content"""
        mock_vector_store.search.return_value = single_result_search
        mock_vector_store.get_lesson_link.return_value = "https://example.com"

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        assert "Computer use allows AI" in result


class TestCourseOutlineTool:
    """Test CourseOutlineTool functionality"""

    def test_get_tool_definition_has_correct_name(self, mock_vector_store):
        """Test tool definition has correct name"""
        tool = CourseOutlineTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"

    def test_get_tool_definition_requires_course_name(self, mock_vector_store):
        """Test tool definition requires course_name"""
        tool = CourseOutlineTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert "course_name" in definition["input_schema"]["required"]

    def test_execute_returns_formatted_outline(self, mock_vector_store):
        """Test execute returns properly formatted outline"""
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="Computer Use")

        assert "Course:" in result
        assert "Lessons:" in result
        assert "Total Lessons:" in result

    def test_execute_handles_nonexistent_course(self, mock_vector_store):
        """Test execute handles course not found"""
        mock_vector_store._resolve_course_name.return_value = None
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="NonExistent")

        assert "No course found" in result

    def test_execute_populates_last_sources(self, mock_vector_store):
        """Test that last_sources is populated after getting outline"""
        tool = CourseOutlineTool(mock_vector_store)
        tool.execute(course_name="Computer Use")

        assert len(tool.last_sources) == 1
        assert "text" in tool.last_sources[0]
        assert "link" in tool.last_sources[0]


class TestToolManager:
    """Test ToolManager functionality"""

    def test_register_tool(self, mock_vector_store):
        """Test registering a tool"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        assert "search_course_content" in manager.tools

    def test_register_multiple_tools(self, mock_vector_store):
        """Test registering multiple tools"""
        manager = ToolManager()
        manager.register_tool(CourseSearchTool(mock_vector_store))
        manager.register_tool(CourseOutlineTool(mock_vector_store))

        assert len(manager.tools) == 2
        assert "search_course_content" in manager.tools
        assert "get_course_outline" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test getting all tool definitions"""
        manager = ToolManager()
        manager.register_tool(CourseSearchTool(mock_vector_store))
        manager.register_tool(CourseOutlineTool(mock_vector_store))

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 2
        names = [d["name"] for d in definitions]
        assert "search_course_content" in names
        assert "get_course_outline" in names

    def test_execute_tool(self, mock_vector_store, valid_search_results):
        """Test executing a registered tool"""
        mock_vector_store.search.return_value = valid_search_results

        manager = ToolManager()
        manager.register_tool(CourseSearchTool(mock_vector_store))

        result = manager.execute_tool("search_course_content", query="test")

        assert result is not None
        assert "[Introduction to AI" in result

    def test_execute_unknown_tool(self):
        """Test executing an unregistered tool returns error"""
        manager = ToolManager()

        result = manager.execute_tool("unknown_tool", query="test")

        assert "not found" in result

    def test_get_last_sources(self, mock_vector_store, valid_search_results):
        """Test retrieving sources from last search"""
        mock_vector_store.search.return_value = valid_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com"
        mock_vector_store.get_course_link.return_value = "https://example.com"

        manager = ToolManager()
        manager.register_tool(CourseSearchTool(mock_vector_store))

        manager.execute_tool("search_course_content", query="test")
        sources = manager.get_last_sources()

        assert len(sources) > 0

    def test_get_last_sources_empty_initially(self, mock_vector_store):
        """Test that sources are empty before any search"""
        manager = ToolManager()
        manager.register_tool(CourseSearchTool(mock_vector_store))

        sources = manager.get_last_sources()

        assert len(sources) == 0

    def test_reset_sources(self, mock_vector_store, valid_search_results):
        """Test resetting sources clears them"""
        mock_vector_store.search.return_value = valid_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com"
        mock_vector_store.get_course_link.return_value = "https://example.com"

        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        manager.execute_tool("search_course_content", query="test")
        manager.reset_sources()

        assert search_tool.last_sources == []
