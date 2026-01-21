"""
Tests for CourseSearchTool and ToolManager.

These tests will reveal the MAX_RESULTS=0 bug in config.py.
"""
import pytest
from unittest.mock import Mock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager, Tool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool"""

    # ============== Tool Definition Tests ==============

    def test_get_tool_definition_structure(self, mock_vector_store_with_results):
        """Verify tool definition has correct structure for Anthropic API"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "query" in definition["input_schema"]["properties"]
        assert "required" in definition["input_schema"]
        assert "query" in definition["input_schema"]["required"]

    def test_tool_definition_has_optional_parameters(self, mock_vector_store_with_results):
        """Verify optional parameters are defined but not required"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        definition = tool.get_tool_definition()
        props = definition["input_schema"]["properties"]

        assert "course_name" in props
        assert "lesson_number" in props
        assert "course_name" not in definition["input_schema"]["required"]
        assert "lesson_number" not in definition["input_schema"]["required"]

    # ============== Execute Method Tests - Bug Detection ==============

    def test_execute_returns_results_when_content_exists(self, mock_vector_store_with_results):
        """
        TEST THAT REVEALS MAX_RESULTS=0 BUG

        With proper configuration, this should return formatted search results.
        With MAX_RESULTS=0, this will fail because search returns empty.
        """
        tool = CourseSearchTool(mock_vector_store_with_results)
        result = tool.execute(query="MCP protocol")

        # Should NOT return "No relevant content found" when content exists
        assert "No relevant content found" not in result
        assert "MCP" in result or "[" in result  # Should have formatted content

    def test_execute_with_max_results_zero_returns_empty(self, mock_vector_store_empty):
        """
        EXPLICIT TEST FOR MAX_RESULTS=0 BUG

        This test demonstrates the bug behavior - when MAX_RESULTS=0,
        search always returns empty results regardless of actual content.
        """
        tool = CourseSearchTool(mock_vector_store_empty)
        result = tool.execute(query="MCP protocol")

        # With MAX_RESULTS=0, we get "No relevant content found"
        assert "No relevant content found" in result

    def test_execute_should_return_at_least_one_result_for_valid_query(
        self, mock_vector_store_with_results
    ):
        """
        CRITICAL BUG DETECTION TEST

        For a valid query against a populated vector store,
        we should get at least one result. This test will FAIL
        with MAX_RESULTS=0 configuration.
        """
        tool = CourseSearchTool(mock_vector_store_with_results)
        result = tool.execute(query="What is MCP?")

        # Verify we got actual results, not empty message
        assert "No relevant content found" not in result
        # Verify result contains course context markers
        assert "[" in result and "]" in result

    def test_execute_with_course_filter(self, mock_vector_store_with_results):
        """Test search with course name filter"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        result = tool.execute(query="protocol basics", course_name="MCP Course")

        # Verify search was called with course filter
        mock_vector_store_with_results.search.assert_called_once()
        call_kwargs = mock_vector_store_with_results.search.call_args[1]
        assert call_kwargs["course_name"] == "MCP Course"

    def test_execute_with_lesson_filter(self, mock_vector_store_with_results):
        """Test search with lesson number filter"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        result = tool.execute(query="introduction", lesson_number=1)

        mock_vector_store_with_results.search.assert_called_once()
        call_kwargs = mock_vector_store_with_results.search.call_args[1]
        assert call_kwargs["lesson_number"] == 1

    def test_execute_with_both_filters(self, mock_vector_store_with_results):
        """Test search with both course and lesson filters"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        result = tool.execute(
            query="advanced topics",
            course_name="MCP Course",
            lesson_number=2
        )

        call_kwargs = mock_vector_store_with_results.search.call_args[1]
        assert call_kwargs["course_name"] == "MCP Course"
        assert call_kwargs["lesson_number"] == 2

    # ============== Error Handling Tests ==============

    def test_execute_handles_error_results(self, mock_vector_store_with_error):
        """Test proper error handling when search fails"""
        tool = CourseSearchTool(mock_vector_store_with_error)
        result = tool.execute(query="anything")

        # Should return the error message from SearchResults
        assert "No course found" in result or "error" in result.lower()

    def test_execute_handles_course_not_found(self, mock_vector_store_course_not_found):
        """Test handling when specified course doesn't exist"""
        tool = CourseSearchTool(mock_vector_store_course_not_found)
        result = tool.execute(query="test", course_name="Unknown Course")

        assert "No course found" in result or "not found" in result.lower()

    # ============== Result Formatting Tests ==============

    def test_format_results_includes_course_title(self, mock_vector_store_with_results):
        """Verify formatted results include course title"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        result = tool.execute(query="MCP")

        assert "MCP Course" in result

    def test_format_results_includes_lesson_number(self, mock_vector_store_with_results):
        """Verify formatted results include lesson numbers"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        result = tool.execute(query="MCP")

        assert "Lesson" in result

    # ============== Source Tracking Tests ==============

    def test_last_sources_populated_after_successful_search(
        self, mock_vector_store_with_results
    ):
        """Verify last_sources is populated with search results"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        tool.execute(query="MCP")

        assert len(tool.last_sources) > 0
        assert "MCP Course" in tool.last_sources[0]

    def test_last_sources_contains_lesson_info(self, mock_vector_store_with_results):
        """Verify sources include lesson information"""
        tool = CourseSearchTool(mock_vector_store_with_results)
        tool.execute(query="MCP")

        # Should have "Course - Lesson N" format
        assert any("Lesson" in source for source in tool.last_sources)


class TestToolManager:
    """Test suite for ToolManager"""

    def test_register_tool_success(self, mock_vector_store_with_results):
        """Test successful tool registration"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store_with_results)

        manager.register_tool(tool)

        assert "search_course_content" in manager.tools

    def test_register_tool_without_name_raises_error(self):
        """Test that tool without name raises ValueError"""
        manager = ToolManager()

        mock_tool = Mock(spec=Tool)
        mock_tool.get_tool_definition.return_value = {"description": "No name"}

        with pytest.raises(ValueError, match="must have a 'name'"):
            manager.register_tool(mock_tool)

    def test_get_tool_definitions_returns_all_tools(self, mock_vector_store_with_results):
        """Test getting definitions for all registered tools"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store_with_results)
        outline_tool = CourseOutlineTool(mock_vector_store_with_results)

        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 2
        names = [d["name"] for d in definitions]
        assert "search_course_content" in names
        assert "get_course_outline" in names

    def test_execute_tool_success(self, tool_manager_with_search_tool):
        """Test successful tool execution"""
        result = tool_manager_with_search_tool.execute_tool(
            "search_course_content",
            query="MCP"
        )

        assert result is not None
        assert isinstance(result, str)

    def test_execute_tool_not_found(self, tool_manager_with_search_tool):
        """Test executing non-existent tool"""
        result = tool_manager_with_search_tool.execute_tool(
            "nonexistent_tool",
            query="test"
        )

        assert "not found" in result.lower()

    def test_get_last_sources_from_search_tool(self, mock_vector_store_with_results):
        """Test retrieving sources after tool execution"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store_with_results)
        manager.register_tool(search_tool)

        # Execute search
        manager.execute_tool("search_course_content", query="MCP")

        sources = manager.get_last_sources()
        assert len(sources) > 0

    def test_get_last_sources_empty_when_no_search(self):
        """Test sources are empty before any search"""
        manager = ToolManager()
        sources = manager.get_last_sources()

        assert sources == []

    def test_reset_sources_clears_all_tools(self, mock_vector_store_with_results):
        """Test that reset_sources clears sources from all tools"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store_with_results)
        manager.register_tool(search_tool)

        # Execute to populate sources
        manager.execute_tool("search_course_content", query="MCP")
        assert len(manager.get_last_sources()) > 0

        # Reset and verify
        manager.reset_sources()
        assert manager.get_last_sources() == []

    # ============== Integration Test with Empty Results ==============

    def test_execute_tool_with_max_results_zero(self, tool_manager_with_empty_results):
        """
        BUG DETECTION TEST

        With MAX_RESULTS=0, tool execution should still work but return
        "No relevant content found" for all queries.
        """
        result = tool_manager_with_empty_results.execute_tool(
            "search_course_content",
            query="What is MCP?"
        )

        assert "No relevant content found" in result


class TestCourseOutlineTool:
    """Test suite for CourseOutlineTool"""

    def test_get_tool_definition_structure(self, mock_vector_store_with_results):
        """Verify outline tool definition structure"""
        tool = CourseOutlineTool(mock_vector_store_with_results)
        definition = tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "course_name" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["required"]

    def test_execute_returns_outline_for_valid_course(self, mock_vector_store_with_results):
        """Test outline retrieval for existing course"""
        mock_vector_store_with_results.get_course_outline.return_value = {
            "course_title": "MCP Course",
            "course_link": "https://example.com/mcp",
            "instructor": "Dr. Smith",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Introduction"}
            ]
        }

        tool = CourseOutlineTool(mock_vector_store_with_results)
        result = tool.execute(course_name="MCP")

        assert "MCP Course" in result
        assert "Lesson" in result

    def test_execute_returns_error_for_unknown_course(self, mock_vector_store_with_results):
        """Test outline retrieval for non-existent course"""
        mock_vector_store_with_results.get_course_outline.return_value = None

        tool = CourseOutlineTool(mock_vector_store_with_results)
        result = tool.execute(course_name="Unknown")

        assert "No course found" in result
