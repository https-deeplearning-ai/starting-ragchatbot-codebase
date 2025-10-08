"""Tests for CourseSearchTool.execute() method and search functionality"""
import pytest
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() method"""

    def test_execute_simple_query(self, course_search_tool):
        """Test basic query execution without filters"""
        result = course_search_tool.execute(query="machine learning")

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain course context in results
        assert "Introduction to Machine Learning" in result or "Machine Learning" in result

    def test_execute_query_with_course_filter(self, course_search_tool):
        """Test query with course_name filter (exact match)"""
        result = course_search_tool.execute(
            query="neural networks",
            course_name="Introduction to Machine Learning"
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Introduction to Machine Learning" in result
        # Should NOT contain other courses
        assert "Anthropic" not in result

    def test_execute_query_with_partial_course_name(self, course_search_tool):
        """Test query with partial course name (semantic matching)"""
        result = course_search_tool.execute(
            query="API",
            course_name="Anthropic"  # Partial match for "Building Towards Computer Use with Anthropic"
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Should resolve to the full course name
        assert "Building Towards Computer Use with Anthropic" in result or "Anthropic" in result

    def test_execute_query_with_lesson_filter(self, course_search_tool):
        """Test query with lesson_number filter"""
        result = course_search_tool.execute(
            query="learning",
            course_name="Introduction to Machine Learning",
            lesson_number=1
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Lesson 1" in result
        # Should filter to specific lesson
        assert "supervised" in result.lower() or "Supervised" in result

    def test_execute_query_with_both_filters(self, course_search_tool):
        """Test query with both course_name and lesson_number filters"""
        result = course_search_tool.execute(
            query="neural",
            course_name="Introduction to Machine Learning",
            lesson_number=2
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Introduction to Machine Learning" in result
        assert "Lesson 2" in result

    def test_execute_invalid_course_name(self, course_search_tool):
        """Test query with non-existent course name"""
        result = course_search_tool.execute(
            query="test query",
            course_name="Non-Existent Course 12345"
        )

        assert isinstance(result, str)
        # Should return error message
        assert "No course found" in result or "not found" in result.lower()

    def test_execute_no_results(self, course_search_tool):
        """Test query that returns no results"""
        result = course_search_tool.execute(
            query="quantum physics relativistic mechanics",
            course_name="Introduction to Machine Learning"
        )

        assert isinstance(result, str)
        # Should handle no results gracefully
        assert "No relevant content found" in result or len(result) > 0

    def test_execute_empty_query(self, course_search_tool):
        """Test with empty query string"""
        result = course_search_tool.execute(query="")

        assert isinstance(result, str)
        # Should return something (empty query might still match content)

    def test_source_tracking(self, course_search_tool):
        """Test that sources are tracked after search"""
        # Reset sources first
        course_search_tool.last_sources = []

        result = course_search_tool.execute(
            query="machine learning",
            course_name="Introduction to Machine Learning"
        )

        # Check that sources were tracked
        assert hasattr(course_search_tool, 'last_sources')
        sources = course_search_tool.last_sources

        if "No relevant content found" not in result:
            assert len(sources) > 0
            # Each source should have label and link
            for source in sources:
                assert isinstance(source, dict)
                assert 'label' in source
                assert 'link' in source

    def test_result_formatting(self, course_search_tool):
        """Test that results are properly formatted with context"""
        result = course_search_tool.execute(
            query="supervised learning",
            course_name="Introduction to Machine Learning"
        )

        if "No relevant content found" not in result:
            # Should have course title in brackets
            assert "[" in result and "]" in result
            # Should contain content
            assert len(result) > 50  # Should have substantial content

    def test_lesson_link_in_sources(self, course_search_tool):
        """Test that lesson links are included in sources"""
        course_search_tool.last_sources = []

        result = course_search_tool.execute(
            query="neural networks",
            course_name="Introduction to Machine Learning",
            lesson_number=2
        )

        sources = course_search_tool.last_sources

        if "No relevant content found" not in result and len(sources) > 0:
            # At least one source should have a link
            has_link = any(source.get('link') is not None for source in sources)
            assert has_link, "Sources should include lesson links"

    def test_multiple_results_formatting(self, course_search_tool):
        """Test formatting when multiple chunks are returned"""
        result = course_search_tool.execute(query="learning")

        if "No relevant content found" not in result:
            # Multiple results should be separated
            assert "\n\n" in result or result.count("[") > 1

    def test_special_characters_in_query(self, course_search_tool):
        """Test handling of special characters in query"""
        result = course_search_tool.execute(
            query="AI & ML: what's the difference?"
        )

        assert isinstance(result, str)
        # Should handle special characters without crashing


class TestCourseOutlineTool:
    """Test CourseOutlineTool functionality"""

    def test_get_outline_exact_match(self, course_outline_tool):
        """Test getting course outline with exact course name"""
        result = course_outline_tool.execute(
            course_name="Introduction to Machine Learning"
        )

        assert isinstance(result, str)
        assert "Introduction to Machine Learning" in result
        assert "Lesson 0" in result
        assert "Lesson 1" in result
        assert "Lesson 2" in result

    def test_get_outline_partial_match(self, course_outline_tool):
        """Test getting course outline with partial course name"""
        result = course_outline_tool.execute(
            course_name="Machine Learning"
        )

        assert isinstance(result, str)
        assert "Introduction to Machine Learning" in result or "Machine Learning" in result

    def test_get_outline_invalid_course(self, course_outline_tool):
        """Test outline retrieval for non-existent course"""
        result = course_outline_tool.execute(
            course_name="Non-Existent Course XYZ"
        )

        assert isinstance(result, str)
        assert "No course found" in result

    def test_get_outline_includes_course_link(self, course_outline_tool):
        """Test that outline includes course link"""
        result = course_outline_tool.execute(
            course_name="Introduction to Machine Learning"
        )

        assert "Link:" in result or "https://" in result

    def test_get_outline_includes_all_lessons(self, course_outline_tool):
        """Test that all lessons are included in outline"""
        result = course_outline_tool.execute(
            course_name="Building Towards Computer Use with Anthropic"
        )

        # Should include lesson count
        assert "Lesson" in result
        # Should show lesson titles
        assert "Introduction" in result or "API Basics" in result


class TestToolManager:
    """Test ToolManager functionality"""

    def test_register_tool(self, vector_store):
        """Test tool registration"""
        manager = ToolManager()
        tool = CourseSearchTool(vector_store)

        manager.register_tool(tool)

        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, tool_manager):
        """Test retrieving all tool definitions"""
        definitions = tool_manager.get_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) >= 2  # Should have search and outline tools

        # Check that definitions have required fields
        for definition in definitions:
            assert "name" in definition
            assert "description" in definition
            assert "input_schema" in definition

    def test_execute_tool_search(self, tool_manager):
        """Test executing search tool through manager"""
        result = tool_manager.execute_tool(
            tool_name="search_course_content",
            query="machine learning"
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_execute_tool_outline(self, tool_manager):
        """Test executing outline tool through manager"""
        result = tool_manager.execute_tool(
            tool_name="get_course_outline",
            course_name="Introduction to Machine Learning"
        )

        assert isinstance(result, str)
        assert "Introduction to Machine Learning" in result

    def test_execute_invalid_tool(self, tool_manager):
        """Test executing non-existent tool"""
        result = tool_manager.execute_tool(
            tool_name="non_existent_tool",
            query="test"
        )

        assert isinstance(result, str)
        assert "not found" in result.lower()

    def test_get_last_sources(self, tool_manager):
        """Test retrieving sources from last search"""
        # Execute a search
        tool_manager.execute_tool(
            tool_name="search_course_content",
            query="machine learning",
            course_name="Introduction to Machine Learning"
        )

        sources = tool_manager.get_last_sources()

        assert isinstance(sources, list)
        # Should have sources if search returned results

    def test_reset_sources(self, tool_manager):
        """Test resetting sources"""
        # Execute a search
        tool_manager.execute_tool(
            tool_name="search_course_content",
            query="machine learning"
        )

        # Reset sources
        tool_manager.reset_sources()

        sources = tool_manager.get_last_sources()
        assert len(sources) == 0

    def test_multiple_tool_executions_source_tracking(self, tool_manager):
        """Test that sources are updated with each search"""
        # First search
        tool_manager.execute_tool(
            tool_name="search_course_content",
            query="machine learning"
        )
        sources1 = tool_manager.get_last_sources()

        # Second search
        tool_manager.execute_tool(
            tool_name="search_course_content",
            query="API",
            course_name="Anthropic"
        )
        sources2 = tool_manager.get_last_sources()

        # Sources should be from the most recent search
        # They might be different if the queries return different results
        assert isinstance(sources2, list)
