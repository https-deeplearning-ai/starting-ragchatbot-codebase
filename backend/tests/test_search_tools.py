"""Tests for CourseSearchTool - the search tool used by AI"""

import os
import sys
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() method"""

    def test_execute_returns_formatted_results(
        self, mock_vector_store, sample_search_results
    ):
        """Test successful search returns formatted content"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="machine learning")

        assert "[ML Fundamentals - Lesson 1]" in result
        assert "machine learning basics" in result
        mock_vector_store.search.assert_called_once_with(
            query="machine learning", course_name=None, lesson_number=None
        )

    def test_execute_with_empty_results_returns_message(self, mock_vector_store):
        """Test empty results returns informative message"""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_with_error_returns_error_message(self, mock_vector_store):
        """Test search error is propagated correctly"""
        mock_vector_store.search.return_value = SearchResults.empty(
            "No course found matching 'BadCourse'"
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test", course_name="BadCourse")

        assert "No course found matching 'BadCourse'" in result

    def test_execute_with_course_filter(self, mock_vector_store, sample_search_results):
        """Test search with course name filter"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test", course_name="ML Course")

        mock_vector_store.search.assert_called_with(
            query="test", course_name="ML Course", lesson_number=None
        )

    def test_execute_with_lesson_filter(self, mock_vector_store, sample_search_results):
        """Test search with lesson number filter"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test", lesson_number=2)

        mock_vector_store.search.assert_called_with(
            query="test", course_name=None, lesson_number=2
        )

    def test_execute_with_both_filters(self, mock_vector_store, sample_search_results):
        """Test search with both course and lesson filters"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test", course_name="ML Course", lesson_number=3)

        mock_vector_store.search.assert_called_with(
            query="test", course_name="ML Course", lesson_number=3
        )

    def test_execute_tracks_sources(self, mock_vector_store, sample_search_results):
        """Test that sources are tracked for UI display"""
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "ML Fundamentals - Lesson 1"
        assert tool.last_sources[0]["link"] == "https://example.com/lesson"

    def test_execute_with_max_results_zero_bug(self, mock_vector_store_zero_results):
        """CRITICAL: Demonstrate the MAX_RESULTS=0 bug effect on tool

        When VectorStore is configured with max_results=0, all searches
        return empty results, causing this tool to always return
        "No relevant content found" regardless of the query.
        """
        tool = CourseSearchTool(mock_vector_store_zero_results)
        result = tool.execute(query="machine learning")

        # With MAX_RESULTS=0, we always get "No relevant content found"
        assert "No relevant content found" in result

    def test_execute_with_course_filter_empty_results(self, mock_vector_store):
        """Test empty results with course filter shows filter info"""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test", course_name="ML Course")

        assert "No relevant content found" in result
        assert "ML Course" in result


class TestCourseOutlineTool:
    """Test CourseOutlineTool functionality"""

    def test_execute_returns_formatted_outline(self):
        """Test successful outline retrieval"""
        mock_store = Mock()
        mock_store.get_course_metadata.return_value = {
            "title": "ML Fundamentals",
            "course_link": "https://example.com/ml",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Intro"},
                {"lesson_number": 2, "lesson_title": "Basics"},
            ],
        }

        tool = CourseOutlineTool(mock_store)
        result = tool.execute(course_name="ML")

        assert "ML Fundamentals" in result
        assert "Lesson 1: Intro" in result
        assert "Lesson 2: Basics" in result

    def test_execute_course_not_found(self):
        """Test outline for non-existent course"""
        mock_store = Mock()
        mock_store.get_course_metadata.return_value = None

        tool = CourseOutlineTool(mock_store)
        result = tool.execute(course_name="NonExistent")

        assert "No course found matching 'NonExistent'" in result


class TestToolManager:
    """Test ToolManager functionality"""

    def test_register_and_execute_tool(self, mock_vector_store, sample_search_results):
        """Test tool registration and execution"""
        mock_vector_store.search.return_value = sample_search_results

        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="test")

        assert "ML Fundamentals" in result

    def test_execute_unknown_tool(self):
        """Test executing non-existent tool"""
        manager = ToolManager()
        result = manager.execute_tool("unknown_tool", query="test")

        assert "Tool 'unknown_tool' not found" in result

    def test_get_tool_definitions(self, mock_vector_store):
        """Test getting tool definitions for Claude API"""
        manager = ToolManager()
        manager.register_tool(CourseSearchTool(mock_vector_store))

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"
        assert "input_schema" in definitions[0]
        assert definitions[0]["input_schema"]["properties"]["query"]

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """Test retrieving sources after search"""
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com"

        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="test")
        sources = manager.get_last_sources()

        assert len(sources) == 1

    def test_reset_sources(self, mock_vector_store, sample_search_results):
        """Test resetting sources after retrieval"""
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = None

        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="test")
        manager.reset_sources()

        sources = manager.get_last_sources()
        assert len(sources) == 0

    def test_register_multiple_tools(self, mock_vector_store):
        """Test registering multiple tools"""
        manager = ToolManager()
        manager.register_tool(CourseSearchTool(mock_vector_store))
        manager.register_tool(CourseOutlineTool(mock_vector_store))

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 2
        names = [d["name"] for d in definitions]
        assert "search_course_content" in names
        assert "get_course_outline" in names
