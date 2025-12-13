"""Tests for CourseSearchTool and CourseOutlineTool"""

from unittest.mock import Mock

from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager

from tests.fixtures.sample_data import (
    SAMPLE_SEARCH_RESULTS_EMPTY,
    SAMPLE_SEARCH_RESULTS_SUCCESS,
    SAMPLE_SEARCH_RESULTS_WITH_ERROR,
)


class TestCourseSearchTool:
    """Test CourseSearchTool.execute() in isolation"""

    def test_execute_with_zero_max_results(self, mock_vector_store_with_zero_max_results):
        """
        CRITICAL TEST: Test that CourseSearchTool fails with max_results=0

        This exposes how the VectorStore bug propagates to the tool layer.
        """
        tool = CourseSearchTool(mock_vector_store_with_zero_max_results)

        # Mock VectorStore to return empty results (simulating the n_results=0 bug)
        mock_vector_store_with_zero_max_results.search.return_value = SAMPLE_SEARCH_RESULTS_EMPTY

        # Execute search
        result = tool.execute(query="What is MCP?")

        # With max_results=0, the tool should return "No relevant content found"
        assert (
            "No relevant content found" in result
        ), "Tool should report no content when max_results=0"

    def test_execute_returns_formatted_results(self, mock_vector_store):
        """Test that execute() formats results with course and lesson context"""
        tool = CourseSearchTool(mock_vector_store)

        # Mock VectorStore to return successful results
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS

        # Execute search
        result = tool.execute(query="What is MCP?")

        # Verify results are formatted with [Course - Lesson N] headers
        assert "[MCP: Build Rich-Context AI Apps with Anthropic - Lesson 1]" in result
        assert "MCP stands for Model Context Protocol" in result
        assert "external data sources" in result

    def test_execute_with_course_filter(self, mock_vector_store):
        """Test that course_name filter is passed to VectorStore"""
        tool = CourseSearchTool(mock_vector_store)

        # Mock successful results
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS

        # Execute with course filter
        result = tool.execute(query="test", course_name="MCP")

        # Verify vector_store.search was called with course_name
        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args[1]["course_name"] == "MCP"

    def test_execute_with_lesson_filter(self, mock_vector_store):
        """Test that lesson_number filter is passed to VectorStore"""
        tool = CourseSearchTool(mock_vector_store)

        # Mock successful results
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS

        # Execute with lesson filter
        result = tool.execute(query="test", lesson_number=2)

        # Verify vector_store.search was called with lesson_number
        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args[1]["lesson_number"] == 2

    def test_execute_handles_vector_store_errors(self, mock_vector_store):
        """Test that tool handles VectorStore errors gracefully"""
        tool = CourseSearchTool(mock_vector_store)

        # Mock VectorStore to return error
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS_WITH_ERROR

        # Execute search
        result = tool.execute(query="test")

        # Tool should return the error message
        assert result == "No course found matching 'NonExistent'"

    def test_last_sources_are_tracked(self, mock_vector_store):
        """Test that last_sources attribute tracks search results for UI"""
        tool = CourseSearchTool(mock_vector_store)

        # Mock successful search with lesson links
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS
        mock_vector_store.get_lesson_link.return_value = "https://example.com/course/mcp/lesson1"

        # Execute search
        result = tool.execute(query="What is MCP?")

        # Verify sources are tracked
        assert len(tool.last_sources) == 2
        assert all(isinstance(source, dict) for source in tool.last_sources)
        assert all("text" in source and "url" in source for source in tool.last_sources)

        # Verify source text format
        assert (
            "MCP: Build Rich-Context AI Apps with Anthropic - Lesson 1"
            in tool.last_sources[0]["text"]
        )

    def test_get_tool_definition(self):
        """Test that get_tool_definition returns valid Anthropic tool schema"""
        mock_store = Mock()
        tool = CourseSearchTool(mock_store)

        definition = tool.get_tool_definition()

        # Verify required fields
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition

        # Verify input schema
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert schema["required"] == ["query"]

        # Verify optional parameters
        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]


class TestCourseOutlineTool:
    """Test CourseOutlineTool.execute() in isolation"""

    def test_execute_returns_course_outline(self, mock_vector_store, sample_course_metadata):
        """Test that execute() returns formatted course outline"""
        tool = CourseOutlineTool(mock_vector_store)

        # Mock course resolution
        mock_vector_store._resolve_course_name.return_value = (
            "MCP: Build Rich-Context AI Apps with Anthropic"
        )

        # Mock catalog.get() to return course metadata
        mock_vector_store.course_catalog.get.return_value = {"metadatas": [sample_course_metadata]}

        # Execute
        result = tool.execute(course_name="MCP")

        # Verify output format
        assert "Course: MCP: Build Rich-Context AI Apps with Anthropic" in result
        assert "https://example.com/course/mcp" in result
        assert "Lessons (3 total):" in result
        assert "Lesson 1: Introduction to MCP" in result
        assert "Lesson 2: Core Concepts" in result
        assert "Lesson 3: Building Applications" in result

    def test_execute_with_nonexistent_course(self, mock_vector_store):
        """Test that execute() handles non-existent courses"""
        tool = CourseOutlineTool(mock_vector_store)

        # Mock course resolution to return None
        mock_vector_store._resolve_course_name.return_value = None

        # Execute
        result = tool.execute(course_name="NonExistent")

        # Should return error
        assert "No course found matching" in result
        assert "NonExistent" in result

    def test_get_tool_definition(self):
        """Test that get_tool_definition returns valid Anthropic tool schema"""
        mock_store = Mock()
        tool = CourseOutlineTool(mock_store)

        definition = tool.get_tool_definition()

        # Verify required fields
        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "input_schema" in definition

        # Verify input schema
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "course_name" in schema["properties"]
        assert schema["required"] == ["course_name"]


class TestToolManager:
    """Test ToolManager functionality"""

    def test_register_tool(self, mock_vector_store):
        """Test that tools can be registered"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        # Verify tool is registered
        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test that get_tool_definitions returns all registered tools"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)

        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        definitions = manager.get_tool_definitions()

        # Verify both tools are in definitions
        assert len(definitions) == 2
        tool_names = [d["name"] for d in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_execute_tool(self, mock_vector_store):
        """Test that execute_tool calls the correct tool"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Mock search results
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS

        # Execute tool via manager
        result = manager.execute_tool("search_course_content", query="What is MCP?")

        # Verify result is returned
        assert isinstance(result, str)
        assert "MCP" in result

    def test_execute_nonexistent_tool(self, mock_vector_store):
        """Test that executing non-existent tool returns error"""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_last_sources(self, mock_vector_store):
        """Test that get_last_sources retrieves sources from search tool"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Mock search results
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        # Execute search (populates last_sources)
        manager.execute_tool("search_course_content", query="What is MCP?")

        # Get sources
        sources = manager.get_last_sources()

        # Verify sources are retrieved
        assert len(sources) > 0
        assert all("text" in s and "url" in s for s in sources)

    def test_reset_sources(self, mock_vector_store):
        """Test that reset_sources clears sources from all tools"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute search (populates last_sources)
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"
        manager.execute_tool("search_course_content", query="What is MCP?")

        # Verify sources exist
        assert len(manager.get_last_sources()) > 0

        # Reset sources
        manager.reset_sources()

        # Verify sources are cleared
        assert len(manager.get_last_sources()) == 0
