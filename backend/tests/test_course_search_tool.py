"""Tests for CourseSearchTool.execute and MAX_RESULTS diagnostics."""

from unittest.mock import MagicMock

import pytest

from config import config
from search_tools import CourseSearchTool
from vector_store import SearchResults, VectorStore


class TestCourseSearchToolExecute:
    def test_formats_successful_results_and_sets_sources(
        self, mock_vector_store, sample_search_results
    ):
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?")

        assert "[Advanced Retrieval for AI with Chroma - Lesson 1]" in result
        assert "RAG combines retrieval with generation" in result
        assert tool.last_sources == [
            "Advanced Retrieval for AI with Chroma - Lesson 1|https://example.com/lesson/1"
        ]
        mock_vector_store.search.assert_called_once_with(
            query="What is RAG?",
            course_name=None,
            lesson_number=None,
        )

    def test_empty_results_returns_no_content_message(
        self, mock_vector_store, empty_search_results
    ):
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="obscure topic")

        assert result == "No relevant content found."

    def test_empty_results_includes_filter_info(
        self, mock_vector_store, empty_search_results
    ):
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(
            query="topic",
            course_name="MCP",
            lesson_number=3,
        )

        assert "No relevant content found in course 'MCP' in lesson 3." == result

    def test_returns_error_string_from_search_results(
        self, mock_vector_store, error_search_results
    ):
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="anything")

        assert result == "Search error: n_results must be a positive integer"

    def test_forwards_course_name_and_lesson_number(
        self, mock_vector_store, sample_search_results
    ):
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(
            query="embeddings",
            course_name="Chroma",
            lesson_number=2,
        )

        mock_vector_store.search.assert_called_once_with(
            query="embeddings",
            course_name="Chroma",
            lesson_number=2,
        )

    def test_sources_without_lesson_link(self, mock_vector_store, sample_search_results):
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = None
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="RAG")

        assert tool.last_sources == [
            "Advanced Retrieval for AI with Chroma - Lesson 1"
        ]


class TestMaxResultsConfig:
    """Diagnostic tests that catch MAX_RESULTS=0 breaking Chroma search."""

    def test_config_max_results_is_positive(self):
        assert config.MAX_RESULTS > 0, (
            f"MAX_RESULTS must be a positive integer for ChromaDB n_results; "
            f"got {config.MAX_RESULTS}"
        )

    def test_vector_store_search_passes_positive_n_results(self):
        """VectorStore built with config.MAX_RESULTS must call query with n_results > 0."""
        store = VectorStore.__new__(VectorStore)
        store.max_results = config.MAX_RESULTS
        store.course_content = MagicMock()
        store.course_content.query.return_value = {
            "documents": [["doc"]],
            "metadatas": [[{"course_title": "Test", "lesson_number": 1}]],
            "distances": [[0.1]],
        }

        results = store.search(query="test query")

        assert not results.error, f"Search failed: {results.error}"
        store.course_content.query.assert_called_once()
        n_results = store.course_content.query.call_args.kwargs["n_results"]
        assert n_results > 0, (
            f"n_results must be positive; got {n_results} "
            f"(from config.MAX_RESULTS={config.MAX_RESULTS})"
        )

    def test_course_search_tool_with_zero_max_results_surfaces_search_error(self):
        """Simulate production path: VectorStore(max_results=0) yields Search error."""
        store = VectorStore.__new__(VectorStore)
        store.max_results = 0
        store.course_content = MagicMock()
        store.course_content.query.side_effect = Exception(
            "Expected n_results to be a positive number, got 0"
        )

        tool = CourseSearchTool(store)
        result = tool.execute(query="What is RAG?")

        assert result.startswith("Search error:")
        assert "0" in result or "positive" in result.lower()
