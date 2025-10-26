"""
Tests for CourseSearchTool functionality
"""

import os
import sys
from unittest.mock import Mock, call, patch

import pytest

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test cases for CourseSearchTool class"""

    def test_initialization(self, mock_vector_store):
        """Test that CourseSearchTool initializes correctly"""
        tool = CourseSearchTool(mock_vector_store)

        assert tool.store == mock_vector_store
        assert tool.last_sources == []
        assert hasattr(tool, "get_tool_definition")
        assert hasattr(tool, "execute")

    def test_get_tool_definition(self, mock_vector_store):
        """Test tool definition structure"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        # Check required fields
        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition

        # Check tool name
        assert definition["name"] == "search_course_content"

        # Check input schema structure
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

        # Check properties
        properties = schema["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties

        # Check required fields
        assert "query" in schema["required"]
        assert len(schema["required"]) == 1

        # Check property types and descriptions
        assert properties["query"]["type"] == "string"
        assert "What to search for" in properties["query"]["description"]

        assert properties["course_name"]["type"] == "string"
        assert "Course title" in properties["course_name"]["description"]

        assert properties["lesson_number"]["type"] == "integer"
        assert "Specific lesson number" in properties["lesson_number"]["description"]

    def test_execute_successful_search(self, mock_vector_store):
        """Test successful search execution"""
        # Setup mock vector store response
        mock_vector_store.search.return_value = SearchResults(
            documents=["Machine learning is a subset of artificial intelligence."],
            metadata=[
                {
                    "course_title": "Machine Learning Fundamentals",
                    "lesson_number": 1,
                    "chunk_index": 0,
                }
            ],
            distances=[0.1],
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="machine learning")

        # Verify vector store was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="machine learning", course_name=None, lesson_number=None
        )

        # Verify result format
        assert "Machine Learning Fundamentals - Lesson 1" in result
        assert "Machine learning is a subset of artificial intelligence" in result

        # Verify sources were tracked
        assert tool.last_sources == ["Machine Learning Fundamentals - Lesson 1"]

    def test_execute_course_specific_search(self, mock_vector_store):
        """Test search with specific course name"""
        # Setup mock response
        mock_vector_store.search.return_value = SearchResults(
            documents=["Linear regression is a fundamental technique."],
            metadata=[
                {
                    "course_title": "Machine Learning Fundamentals",
                    "lesson_number": 2,
                    "chunk_index": 1,
                }
            ],
            distances=[0.2],
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="linear regression", course_name="Machine Learning")

        # Verify vector store was called with correct parameters
        mock_vector_store.search.assert_called_once_with(
            query="linear regression",
            course_name="Machine Learning",
            lesson_number=None,
        )

        # Verify result
        assert "Machine Learning Fundamentals - Lesson 2" in result
        assert "Linear regression is a fundamental technique" in result

    def test_execute_lesson_specific_search(self, mock_vector_store):
        """Test search with specific lesson number"""
        # Setup mock response
        mock_vector_store.search.return_value = SearchResults(
            documents=["Neural networks are computing systems inspired by biology."],
            metadata=[
                {
                    "course_title": "Machine Learning Fundamentals",
                    "lesson_number": 3,
                    "chunk_index": 0,
                }
            ],
            distances=[0.15],
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(
            query="neural networks",
            course_name="Machine Learning Fundamentals",
            lesson_number=3,
        )

        # Verify vector store was called with all parameters
        mock_vector_store.search.assert_called_once_with(
            query="neural networks",
            course_name="Machine Learning Fundamentals",
            lesson_number=3,
        )

        # Verify result
        assert "Machine Learning Fundamentals - Lesson 3" in result
        assert "Neural networks are computing systems" in result

    def test_execute_multiple_results(self, mock_vector_store):
        """Test search that returns multiple results"""
        # Setup mock response with multiple results
        mock_vector_store.search.return_value = SearchResults(
            documents=[
                "First result about machine learning basics.",
                "Second result about advanced machine learning techniques.",
            ],
            metadata=[
                {
                    "course_title": "Machine Learning Fundamentals",
                    "lesson_number": 1,
                    "chunk_index": 0,
                },
                {
                    "course_title": "Machine Learning Fundamentals",
                    "lesson_number": 2,
                    "chunk_index": 1,
                },
            ],
            distances=[0.1, 0.2],
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="machine learning")

        # Verify both results are included
        assert "Machine Learning Fundamentals - Lesson 1" in result
        assert "Machine Learning Fundamentals - Lesson 2" in result
        assert "First result about machine learning basics" in result
        assert "Second result about advanced machine learning techniques" in result

        # Verify both sources are tracked
        assert len(tool.last_sources) == 2
        assert "Machine Learning Fundamentals - Lesson 1" in tool.last_sources
        assert "Machine Learning Fundamentals - Lesson 2" in tool.last_sources

    def test_execute_no_results_found(self, mock_vector_store):
        """Test search that returns no results"""
        # Setup mock empty response
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="nonexistent topic")

        # Verify empty response message
        assert "No relevant content found" in result
        assert tool.last_sources == []

    def test_execute_no_results_with_course_filter(self, mock_vector_store):
        """Test search with course filter that returns no results"""
        # Setup mock empty response
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic", course_name="Nonexistent Course")

        # Verify empty response with course context
        assert "No relevant content found in course 'Nonexistent Course'" in result

    def test_execute_no_results_with_lesson_filter(self, mock_vector_store):
        """Test search with lesson filter that returns no results"""
        # Setup mock empty response
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic", lesson_number=99)

        # Verify empty response with lesson context
        assert "No relevant content found in lesson 99" in result

    def test_execute_no_results_with_both_filters(self, mock_vector_store):
        """Test search with both course and lesson filters that returns no results"""
        # Setup mock empty response
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic", course_name="Some Course", lesson_number=5)

        # Verify empty response with both contexts
        assert "No relevant content found in course 'Some Course' in lesson 5" in result

    def test_execute_course_not_found_error(self, mock_vector_store):
        """Test search where course name resolution fails"""
        # Setup mock to return error
        mock_vector_store.search.return_value = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="No course found matching 'Nonexistent Course'",
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic", course_name="Nonexistent Course")

        # Verify error message
        assert "No course found matching 'Nonexistent Course'" in result

    def test_execute_search_error(self, mock_vector_store):
        """Test search that encounters an error"""
        # Setup mock to return error
        mock_vector_store.search.return_value = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Search error: Database connection failed",
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic")

        # Verify error message
        assert "Search error: Database connection failed" in result

    def test_execute_lesson_number_none_in_metadata(self, mock_vector_store):
        """Test handling of None lesson_number in metadata"""
        # Setup mock response with None lesson number
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content without lesson number."],
            metadata=[
                {
                    "course_title": "Machine Learning Fundamentals",
                    "lesson_number": None,
                    "chunk_index": 0,
                }
            ],
            distances=[0.1],
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic")

        # Verify result format (should not show lesson number)
        assert "[Machine Learning Fundamentals]" in result
        assert "Content without lesson number" in result
        assert tool.last_sources == ["Machine Learning Fundamentals"]

    def test_format_results_with_missing_metadata(self, mock_vector_store):
        """Test _format_results method with missing metadata fields"""
        # Setup mock response with incomplete metadata
        mock_vector_store.search.return_value = SearchResults(
            documents=["Some content."],
            metadata=[
                {
                    "course_title": "Test Course",
                    # Missing lesson_number
                    "chunk_index": 0,
                }
            ],
            distances=[0.1],
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic")

        # Verify graceful handling of missing metadata
        assert "[Test Course]" in result
        assert "Some content" in result

    def test_sources_reset_on_new_search(self, mock_vector_store):
        """Test that sources are properly tracked across multiple searches"""
        tool = CourseSearchTool(mock_vector_store)

        # First search
        mock_vector_store.search.return_value = SearchResults(
            documents=["First result"],
            metadata=[
                {"course_title": "Course 1", "lesson_number": 1, "chunk_index": 0}
            ],
            distances=[0.1],
        )
        tool.execute(query="first")

        # Verify first search sources
        assert tool.last_sources == ["Course 1 - Lesson 1"]

        # Second search
        mock_vector_store.search.return_value = SearchResults(
            documents=["Second result"],
            metadata=[
                {"course_title": "Course 2", "lesson_number": 2, "chunk_index": 0}
            ],
            distances=[0.1],
        )
        tool.execute(query="second")

        # Verify sources were updated
        assert tool.last_sources == ["Course 2 - Lesson 2"]

    def test_parameter_validation(self, mock_vector_store):
        """Test that execute method handles various parameter combinations"""
        tool = CourseSearchTool(mock_vector_store)

        # Setup mock response
        mock_vector_store.search.return_value = SearchResults(
            documents=["test"],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0}
            ],
            distances=[0.1],
        )

        # Test with just query (required parameter)
        tool.execute(query="test")
        mock_vector_store.search.assert_called_with(
            query="test", course_name=None, lesson_number=None
        )

        # Test with empty string course_name
        tool.execute(query="test", course_name="")
        mock_vector_store.search.assert_called_with(
            query="test", course_name="", lesson_number=None
        )

        # Test with zero lesson_number
        tool.execute(query="test", lesson_number=0)
        mock_vector_store.search.assert_called_with(
            query="test", course_name=None, lesson_number=0
        )

    @patch("search_tools.SearchResults")
    def test_vector_store_exception_handling(
        self, mock_search_results, mock_vector_store
    ):
        """Test handling of exceptions from vector store"""
        # Setup vector store to raise exception
        mock_vector_store.search.side_effect = Exception("Database error")

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        # Verify exception was handled and error message returned
        assert "Search error:" in result
        assert "Database error" in result

    def test_result_formatting_consistency(self, mock_vector_store):
        """Test that result formatting is consistent and well-structured"""
        # Setup mock response
        mock_vector_store.search.return_value = SearchResults(
            documents=[
                "First piece of content about the topic.",
                "Second piece of content about the same topic.",
            ],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 1},
            ],
            distances=[0.1, 0.2],
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="topic")

        # Verify structure: header + content, separated by double newline
        lines = result.split("\n\n")
        assert len(lines) == 2  # Should have two result blocks

        # Each block should have header and content
        for block in lines:
            block_lines = block.split("\n")
            assert len(block_lines) == 2  # Header and content
            assert block_lines[0].startswith("[Test Course - Lesson 1]")
            assert len(block_lines[1]) > 0  # Content should not be empty
