"""Tests for CourseSearchTool.execute() in search_tools.py.

These tests mock the VectorStore to isolate the search tool logic and verify:
- Correct result formatting
- Error handling
- Filter pass-through (course_name, lesson_number)
- Source tracking and deduplication
"""

import pytest
from unittest.mock import MagicMock, call
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


# ---------------------------------------------------------------------------
# CourseSearchTool.execute() tests
# ---------------------------------------------------------------------------

class TestCourseSearchToolExecute:
    """Tests for the execute method of CourseSearchTool."""

    def test_execute_returns_formatted_results(self, mock_vector_store, sample_search_results):
        """Successful search should return formatted text with course/lesson headers."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?")

        assert "[Building RAG Chatbots - Lesson 1]" in result
        assert "[Building RAG Chatbots - Lesson 2]" in result
        assert "RAG stands for Retrieval-Augmented Generation" in result
        assert "Vector databases store embeddings" in result

    def test_execute_with_empty_results(self, mock_vector_store, empty_search_results):
        """Empty results should return a 'no content found' message."""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_with_error(self, mock_vector_store, error_search_results):
        """When VectorStore returns an error, execute should return the error string."""
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="anything")

        assert "Search error" in result

    def test_execute_passes_course_name_filter(self, mock_vector_store, sample_search_results):
        """course_name parameter should be forwarded to VectorStore.search()."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="RAG", course_name="Building RAG Chatbots")

        mock_vector_store.search.assert_called_once_with(
            query="RAG",
            course_name="Building RAG Chatbots",
            lesson_number=None,
        )

    def test_execute_passes_lesson_number_filter(self, mock_vector_store, sample_search_results):
        """lesson_number parameter should be forwarded to VectorStore.search()."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="RAG", lesson_number=2)

        mock_vector_store.search.assert_called_once_with(
            query="RAG",
            course_name=None,
            lesson_number=2,
        )

    def test_execute_passes_both_filters(self, mock_vector_store, sample_search_results):
        """Both course_name and lesson_number should be forwarded together."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="RAG", course_name="RAG Course", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="RAG",
            course_name="RAG Course",
            lesson_number=3,
        )

    def test_execute_tracks_sources(self, mock_vector_store, sample_search_results):
        """After a successful search, last_sources should contain source info."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="What is RAG?")

        assert len(tool.last_sources) > 0
        assert tool.last_sources[0]["title"] == "Building RAG Chatbots - Lesson 1"
        assert tool.last_sources[0]["link"] is not None

    def test_execute_deduplicates_sources(self, mock_vector_store):
        """Multiple chunks from same course+lesson should produce one source entry."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["chunk 1 from lesson 1", "chunk 2 from lesson 1"],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 1},
            ],
            distances=[0.1, 0.2],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/l1"
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test")

        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["title"] == "Test Course - Lesson 1"

    def test_execute_empty_results_includes_filter_info(self, mock_vector_store, empty_search_results):
        """Empty results message should mention the active filters."""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test", course_name="MCP", lesson_number=5)

        assert "in course 'MCP'" in result
        assert "in lesson 5" in result

    def test_execute_error_does_not_update_sources(self, mock_vector_store, error_search_results):
        """When search errors, last_sources should NOT be updated (stays from init)."""
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="anything")

        # last_sources should still be the initial empty list
        assert tool.last_sources == []

    def test_execute_handles_metadata_without_lesson_number(self, mock_vector_store):
        """Results without lesson_number should format without ' - Lesson X'."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["some general content"],
            metadata=[{"course_title": "Intro Course", "chunk_index": 0}],
            distances=[0.3],
        )
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="general")

        assert "[Intro Course]" in result
        assert "Lesson" not in result.split("]")[0]  # no lesson in header


# ---------------------------------------------------------------------------
# ToolManager tests
# ---------------------------------------------------------------------------

class TestToolManager:
    """Tests for ToolManager registration and execution."""

    def test_register_and_execute_tool(self, mock_vector_store, sample_search_results):
        """Registered tools should be executable by name."""
        mock_vector_store.search.return_value = sample_search_results
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="RAG")

        assert result  # non-empty string
        mock_vector_store.search.assert_called_once()

    def test_execute_unknown_tool(self):
        """Executing an unregistered tool should return an error message."""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """get_last_sources should return sources from the most recent search."""
        mock_vector_store.search.return_value = sample_search_results
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="RAG")
        sources = manager.get_last_sources()

        assert len(sources) > 0

    def test_reset_sources(self, mock_vector_store, sample_search_results):
        """reset_sources should clear sources from all tools."""
        mock_vector_store.search.return_value = sample_search_results
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="RAG")
        manager.reset_sources()

        assert manager.get_last_sources() == []
