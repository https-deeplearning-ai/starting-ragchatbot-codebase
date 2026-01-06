"""
Tests for CourseSearchTool - Focus on error handling and link retrieval
"""

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test CourseSearchTool.execute() method"""

    def test_execute_successful_search(self, mock_vector_store):
        """Test normal search returns formatted results"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test query")

        assert "Test Course" in result
        assert "Lesson 1" in result or "lesson 1" in result
        assert isinstance(result, str)

    def test_execute_empty_results(self, mock_vector_store):
        """Test empty search returns 'No relevant content found' message"""
        # Configure mock to return empty results
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="nonexistent content")

        assert "No relevant content found" in result

    def test_execute_with_error(self, mock_vector_store):
        """Test error propagation from vector store"""
        # Configure mock to return error
        error_results = SearchResults.empty("Database connection failed")
        mock_vector_store.search.return_value = error_results

        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test")

        assert "Database connection failed" in result

    def test_execute_with_course_filter(self, mock_vector_store):
        """Test course_name filter is passed correctly"""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test", course_name="MCP")

        # Verify search was called with course_name
        mock_vector_store.search.assert_called_once()
        call_kwargs = mock_vector_store.search.call_args.kwargs
        assert call_kwargs["course_name"] == "MCP"

    def test_execute_with_lesson_filter(self, mock_vector_store):
        """Test lesson_number filter is passed correctly"""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test", lesson_number=2)

        # Verify search was called with lesson_number
        call_kwargs = mock_vector_store.search.call_args.kwargs
        assert call_kwargs["lesson_number"] == 2


class TestFormatResultsLinkRetrieval:
    """Test _format_results() link retrieval - Bug #4"""

    def test_format_results_with_valid_links(self, mock_vector_store):
        """Test successful link retrieval"""
        tool = CourseSearchTool(mock_vector_store)

        _result = tool.execute(query="test")  # noqa: F841

        # Should have populated last_sources with links
        assert len(tool.last_sources) > 0
        assert tool.last_sources[0]["link"] is not None
        assert "https://" in tool.last_sources[0]["link"]

    def test_format_results_link_retrieval_exception(self, mock_vector_store):
        """
        CRITICAL TEST: Tests Bug #4 - No error handling in _format_results()

        This test will FAIL with current code because:
        - get_lesson_link() and get_course_link() calls are not wrapped in try-except
        - If they raise exceptions, the entire search fails

        Expected: Should catch exceptions and fallback to None for links
        """
        # Configure mock to raise exception when getting links
        mock_vector_store.get_lesson_link.side_effect = Exception("Link retrieval failed")
        mock_vector_store.get_course_link.side_effect = Exception("Link retrieval failed")

        tool = CourseSearchTool(mock_vector_store)

        # This should NOT raise exception - should handle gracefully
        result = tool.execute(query="test")

        # Should still return results, just without links
        assert "Test Course" in result
        # Links should be None in sources
        assert tool.last_sources[0]["link"] is None

    def test_format_results_missing_lesson_link(self, mock_vector_store):
        """Test graceful handling when lesson link is None"""
        # Lesson link returns None, should fallback to course link
        mock_vector_store.get_lesson_link.return_value = None
        mock_vector_store.get_course_link.return_value = "https://example.com/course"

        tool = CourseSearchTool(mock_vector_store)

        _result = tool.execute(query="test")  # noqa: F841

        # Should have course link as fallback
        assert tool.last_sources[0]["link"] == "https://example.com/course"
        assert tool.last_sources[0]["type"] == "course"

    def test_format_results_all_links_none(self, mock_vector_store):
        """Test when both lesson and course links are None"""
        mock_vector_store.get_lesson_link.return_value = None
        mock_vector_store.get_course_link.return_value = None

        tool = CourseSearchTool(mock_vector_store)

        _result = tool.execute(query="test")  # noqa: F841

        # Should handle gracefully with None links
        assert tool.last_sources[0]["link"] is None

    def test_source_tracking(self, mock_vector_store):
        """Test that sources are properly tracked"""
        # Configure specific metadata
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
            distances=[0.3, 0.5],
        )

        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test")

        # Should have 2 sources
        assert len(tool.last_sources) == 2
        assert tool.last_sources[0]["text"] == "Course A - Lesson 1"
        assert tool.last_sources[1]["text"] == "Course B - Lesson 2"

    def test_source_without_lesson_number(self, mock_vector_store):
        """Test source formatting when lesson_number is None"""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test Course"}],  # No lesson_number
            distances=[0.5],
        )

        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test")

        # Should just have course title without lesson number
        assert tool.last_sources[0]["text"] == "Test Course"
        assert tool.last_sources[0]["type"] == "course"


class TestToolDefinition:
    """Test tool definition for Anthropic API"""

    def test_get_tool_definition(self, mock_vector_store):
        """Test that tool definition is properly formatted"""
        tool = CourseSearchTool(mock_vector_store)

        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert "query" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]
