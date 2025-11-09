"""Tests for CourseSearchTool in search_tools.py"""
import pytest
from unittest.mock import Mock, patch
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test CourseSearchTool execute method and formatting"""

    def test_execute_basic_search(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test basic search without filters returns formatted results"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        result = course_search_tool.execute(query="What is Python?")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="What is Python?",
            course_name=None,
            lesson_number=None
        )
        assert "[Python Course - Lesson 1]" in result
        assert "[Python Course - Lesson 2]" in result
        assert "Python basics" in result
        assert "advanced topics" in result

    def test_execute_with_course_filter(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test search with course_name filter"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        result = course_search_tool.execute(
            query="Python basics",
            course_name="Python Course"
        )

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="Python basics",
            course_name="Python Course",
            lesson_number=None
        )
        assert "[Python Course" in result

    def test_execute_with_lesson_filter(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test search with lesson_number filter"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        result = course_search_tool.execute(
            query="Python",
            lesson_number=1
        )

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="Python",
            course_name=None,
            lesson_number=1
        )
        assert "Lesson 1" in result

    def test_execute_with_both_filters(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test search with both course_name and lesson_number filters"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        result = course_search_tool.execute(
            query="Python",
            course_name="Python Course",
            lesson_number=1
        )

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="Python",
            course_name="Python Course",
            lesson_number=1
        )
        assert "[Python Course - Lesson 1]" in result

    def test_execute_empty_results(self, course_search_tool, mock_vector_store, empty_search_results):
        """Test search with no results returns appropriate message"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results

        # Execute
        result = course_search_tool.execute(query="nonexistent topic")

        # Verify
        assert "No relevant content found" in result

    def test_execute_empty_results_with_course_filter(self, course_search_tool, mock_vector_store, empty_search_results):
        """Test empty results message includes course filter info"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results

        # Execute
        result = course_search_tool.execute(
            query="nonexistent",
            course_name="Python Course"
        )

        # Verify
        assert "No relevant content found" in result
        assert "Python Course" in result

    def test_execute_empty_results_with_lesson_filter(self, course_search_tool, mock_vector_store, empty_search_results):
        """Test empty results message includes lesson filter info"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results

        # Execute
        result = course_search_tool.execute(
            query="nonexistent",
            lesson_number=5
        )

        # Verify
        assert "No relevant content found" in result
        assert "lesson 5" in result

    def test_execute_vector_store_error(self, course_search_tool, mock_vector_store, error_search_results):
        """Test that errors from vector store are propagated"""
        # Setup
        mock_vector_store.search.return_value = error_search_results

        # Execute
        result = course_search_tool.execute(query="test query")

        # Verify
        assert "Search error" in result
        assert "Database connection failed" in result

    def test_format_results_structure(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test that results are formatted with correct header structure"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        result = course_search_tool.execute(query="Python")

        # Verify format: [Course Title - Lesson N]\nContent
        lines = result.split("\n")
        assert any("[Python Course - Lesson 1]" in line for line in lines)
        assert any("Python basics" in line for line in lines)

    def test_source_tracking(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test that last_sources and last_source_links are populated"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        # Execute
        course_search_tool.execute(query="Python")

        # Verify
        assert len(course_search_tool.last_sources) == 2
        assert "Python Course - Lesson 1" in course_search_tool.last_sources
        assert "Python Course - Lesson 2" in course_search_tool.last_sources
        assert len(course_search_tool.last_source_links) == 2

    def test_tool_definition_structure(self, course_search_tool):
        """Test that tool definition has correct Anthropic schema"""
        # Execute
        definition = course_search_tool.get_tool_definition()

        # Verify
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "properties" in definition["input_schema"]
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]


class TestToolManager:
    """Test ToolManager registration and execution"""

    def test_register_tool(self, tool_manager, mock_vector_store):
        """Test that tools can be registered"""
        # Setup
        search_tool = CourseSearchTool(mock_vector_store)

        # Execute
        tool_manager.register_tool(search_tool)

        # Verify
        assert "search_course_content" in tool_manager.tools

    def test_get_tool_definitions(self, tool_manager, mock_vector_store):
        """Test that tool definitions are returned as list"""
        # Setup
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        # Execute
        definitions = tool_manager.get_tool_definitions()

        # Verify
        assert isinstance(definitions, list)
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"

    def test_execute_tool(self, tool_manager, mock_vector_store, sample_search_results):
        """Test that tools can be executed by name"""
        # Setup
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        result = tool_manager.execute_tool(
            "search_course_content",
            query="Python"
        )

        # Verify
        assert "Python Course" in result

    def test_execute_nonexistent_tool(self, tool_manager):
        """Test that executing nonexistent tool returns error"""
        # Execute
        result = tool_manager.execute_tool("nonexistent_tool", query="test")

        # Verify
        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_last_sources(self, tool_manager, mock_vector_store, sample_search_results):
        """Test that last sources can be retrieved from tool manager"""
        # Setup
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        tool_manager.execute_tool("search_course_content", query="Python")
        sources = tool_manager.get_last_sources()

        # Verify
        assert len(sources) == 2
        assert "Python Course - Lesson 1" in sources

    def test_get_last_source_links(self, tool_manager, mock_vector_store, sample_search_results):
        """Test that last source links can be retrieved"""
        # Setup
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        tool_manager.execute_tool("search_course_content", query="Python")
        links = tool_manager.get_last_source_links()

        # Verify
        assert len(links) == 2

    def test_reset_sources(self, tool_manager, mock_vector_store, sample_search_results):
        """Test that sources are reset after calling reset_sources"""
        # Setup
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Execute
        tool_manager.execute_tool("search_course_content", query="Python")
        tool_manager.reset_sources()
        sources = tool_manager.get_last_sources()

        # Verify
        assert len(sources) == 0
