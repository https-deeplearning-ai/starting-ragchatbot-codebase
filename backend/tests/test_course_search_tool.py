"""
Tests for CourseSearchTool.execute method
Tests various scenarios including filters, error handling, and source tracking
"""

from unittest.mock import Mock

import pytest
from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test suite for CourseSearchTool.execute method"""

    @pytest.fixture
    def search_tool(self, mock_vector_store):
        """Create a CourseSearchTool instance with mocked vector store"""
        return CourseSearchTool(mock_vector_store)

    def test_execute_with_query_only(self, search_tool, mock_vector_store):
        """Test execute with just a query, no filters"""
        # Setup mock response
        mock_results = SearchResults(
            documents=["Content about Python basics", "More Python content"],
            metadata=[
                {"course_title": "Python 101", "lesson_number": 1},
                {"course_title": "Python 101", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
            links=["http://example.com/lesson1", "http://example.com/lesson2"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        # Execute
        result = search_tool.execute(query="What is Python?")

        # Verify vector store was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="What is Python?", course_name=None, lesson_number=None
        )

        # Verify result formatting
        assert "[Python 101 - Lesson 1]" in result
        assert "Content about Python basics" in result
        assert "[Python 101 - Lesson 2]" in result
        assert "More Python content" in result

        # Verify sources are tracked correctly
        assert len(search_tool.last_sources) == 2
        assert search_tool.last_sources[0]["text"] == "Python 101 - Lesson 1"
        assert search_tool.last_sources[0]["link"] == "http://example.com/lesson1"
        assert search_tool.last_sources[1]["text"] == "Python 101 - Lesson 2"
        assert search_tool.last_sources[1]["link"] == "http://example.com/lesson2"

    def test_execute_with_course_filter(self, search_tool, mock_vector_store):
        """Test execute with course_name filter"""
        mock_results = SearchResults(
            documents=["MCP server basics"],
            metadata=[
                {"course_title": "Introduction to MCP Servers", "lesson_number": 1}
            ],
            distances=[0.1],
            links=["http://example.com/mcp-lesson1"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(
            query="How do MCP servers work?", course_name="Introduction to MCP Servers"
        )

        # Verify parameters passed correctly
        mock_vector_store.search.assert_called_once_with(
            query="How do MCP servers work?",
            course_name="Introduction to MCP Servers",
            lesson_number=None,
        )

        # Verify formatting
        assert "[Introduction to MCP Servers - Lesson 1]" in result
        assert "MCP server basics" in result

    def test_execute_with_lesson_filter(self, search_tool, mock_vector_store):
        """Test execute with lesson_number filter"""
        mock_results = SearchResults(
            documents=["Lesson 3 content"],
            metadata=[{"course_title": "Advanced Topics", "lesson_number": 3}],
            distances=[0.15],
            links=["http://example.com/lesson3"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="Explain advanced concepts", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="Explain advanced concepts", course_name=None, lesson_number=3
        )
        assert "Lesson 3" in result

    def test_execute_with_both_filters(self, search_tool, mock_vector_store):
        """Test execute with both course_name and lesson_number filters"""
        mock_results = SearchResults(
            documents=["Specific lesson content about decorators"],
            metadata=[{"course_title": "Python 101", "lesson_number": 5}],
            distances=[0.05],
            links=["http://example.com/python-lesson5"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(
            query="decorators", course_name="Python 101", lesson_number=5
        )

        mock_vector_store.search.assert_called_once_with(
            query="decorators", course_name="Python 101", lesson_number=5
        )
        assert "[Python 101 - Lesson 5]" in result
        assert "decorators" in result

    def test_execute_with_error(self, search_tool, mock_vector_store):
        """Test execute when vector store returns an error"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            links=[],
            error="No course found matching 'NonexistentCourse'",
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(
            query="test query", course_name="NonexistentCourse"
        )

        # Should return error message directly
        assert result == "No course found matching 'NonexistentCourse'"
        # No sources should be tracked on error
        assert len(search_tool.last_sources) == 0

    def test_execute_with_empty_results(self, search_tool, mock_vector_store):
        """Test execute when search returns no results"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], links=[], error=None
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="obscure topic", course_name="Python 101")

        # Should return appropriate message
        assert "No relevant content found in course 'Python 101'" in result
        assert len(search_tool.last_sources) == 0

    def test_execute_with_empty_results_and_lesson_filter(
        self, search_tool, mock_vector_store
    ):
        """Test execute with no results and lesson filter"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], links=[], error=None
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(
            query="test", course_name="Course X", lesson_number=7
        )

        # Should mention both filters in the message
        assert "No relevant content found in course 'Course X' in lesson 7" in result

    def test_execute_tracks_sources_correctly(self, search_tool, mock_vector_store):
        """Test that execute properly tracks sources for the UI"""
        mock_results = SearchResults(
            documents=["Doc 1", "Doc 2", "Doc 3"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course A", "lesson_number": 2},
                {"course_title": "Course B", "lesson_number": 1},
            ],
            distances=[0.1, 0.2, 0.3],
            links=["link1", "link2", "link3"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        search_tool.execute(query="test")

        # Verify all sources are tracked with correct format
        assert len(search_tool.last_sources) == 3
        assert search_tool.last_sources[0] == {
            "text": "Course A - Lesson 1",
            "link": "link1",
        }
        assert search_tool.last_sources[1] == {
            "text": "Course A - Lesson 2",
            "link": "link2",
        }
        assert search_tool.last_sources[2] == {
            "text": "Course B - Lesson 1",
            "link": "link3",
        }

    def test_execute_without_lesson_links(self, search_tool, mock_vector_store):
        """Test execute when results have no links"""
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Course X", "lesson_number": 1}],
            distances=[0.1],
            links=[None],  # No link available
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="test")

        # Should still work and track source with None link
        assert len(search_tool.last_sources) == 1
        assert search_tool.last_sources[0]["link"] is None
        assert search_tool.last_sources[0]["text"] == "Course X - Lesson 1"

    def test_execute_formats_results_correctly(self, search_tool, mock_vector_store):
        """Test that results are formatted with proper headers and separation"""
        mock_results = SearchResults(
            documents=["First document content", "Second document content"],
            metadata=[
                {"course_title": "Python Basics", "lesson_number": 1},
                {"course_title": "Python Basics", "lesson_number": 2},
            ],
            distances=[0.1, 0.15],
            links=["link1", "link2"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="test")

        # Check exact format with headers and content
        assert "[Python Basics - Lesson 1]\nFirst document content" in result
        assert "[Python Basics - Lesson 2]\nSecond document content" in result
        # Check separation (two newlines between results)
        assert "\n\n" in result

    def test_execute_without_lesson_number_in_metadata(
        self, search_tool, mock_vector_store
    ):
        """Test execute when metadata doesn't include lesson_number (edge case)"""
        mock_results = SearchResults(
            documents=["General course content"],
            metadata=[{"course_title": "General Course"}],  # No lesson_number
            distances=[0.1],
            links=[None],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="test")

        # Should still format correctly without lesson number
        assert "[General Course]" in result
        assert "General course content" in result
        # Source should not include lesson info
        assert search_tool.last_sources[0]["text"] == "General Course"

    def test_get_tool_definition(self, search_tool):
        """Test that tool definition is correctly formatted for Anthropic"""
        definition = search_tool.get_tool_definition()

        # Verify structure
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition

        # Verify input schema
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]
        assert schema["required"] == ["query"]

        # Verify property types
        assert schema["properties"]["query"]["type"] == "string"
        assert schema["properties"]["course_name"]["type"] == "string"
        assert schema["properties"]["lesson_number"]["type"] == "integer"
