"""
Tests for CourseSearchTool.execute()

Covers:
- Error propagation from the vector store
- Empty-result messages (with and without filter annotations)
- Correct result formatting (headers, content)
- Source tracking and deduplication
- Parameter passthrough to VectorStore.search()
"""

import pytest
from unittest.mock import MagicMock, call
from search_tools import CourseSearchTool
from vector_store import SearchResults
from tests.conftest import make_search_results, make_error_results

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_store(search_return=None):
    """Return a mock VectorStore with search() pre-configured."""
    store = MagicMock()
    store.search.return_value = search_return or SearchResults(
        documents=[], metadata=[], distances=[], error=None
    )
    store.get_lesson_link.return_value = "https://example.com/lesson"
    return store


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_returns_error_string_from_store(self):
        """Tool must pass the raw error string back so Claude can report it."""
        store = make_store(make_error_results("Search error: db timeout"))
        tool = CourseSearchTool(store)

        result = tool.execute(query="what is RAG?")

        assert result == "Search error: db timeout"

    def test_error_result_prevents_formatting(self):
        """When an error is present, _format_results must never be called."""
        store = make_store(make_error_results("Search error: embedding failed"))
        tool = CourseSearchTool(store)
        tool._format_results = MagicMock()

        tool.execute(query="something")

        tool._format_results.assert_not_called()


# ---------------------------------------------------------------------------
# Empty results
# ---------------------------------------------------------------------------


class TestEmptyResults:
    def test_no_content_found_message_baseline(self):
        store = make_store()  # empty results, no error
        tool = CourseSearchTool(store)

        result = tool.execute(query="what is RAG?")

        assert result == "No relevant content found."

    def test_no_content_includes_course_name(self):
        store = make_store()
        tool = CourseSearchTool(store)

        result = tool.execute(query="what is RAG?", course_name="AI Fundamentals")

        assert "No relevant content found" in result
        assert "AI Fundamentals" in result

    def test_no_content_includes_lesson_number(self):
        store = make_store()
        tool = CourseSearchTool(store)

        result = tool.execute(query="what is RAG?", lesson_number=3)

        assert "No relevant content found" in result
        assert "3" in result

    def test_no_content_with_both_filters(self):
        store = make_store()
        tool = CourseSearchTool(store)

        result = tool.execute(
            query="embeddings", course_name="MCP Course", lesson_number=2
        )

        assert "MCP Course" in result
        assert "2" in result


# ---------------------------------------------------------------------------
# Successful result formatting
# ---------------------------------------------------------------------------


class TestResultFormatting:
    def test_result_header_contains_course_title(self):
        store = make_store(
            make_search_results(
                documents=["Embeddings are dense vectors."],
                metadata=[{"course_title": "Vector DB Deep Dive", "lesson_number": 1}],
            )
        )
        tool = CourseSearchTool(store)

        result = tool.execute(query="what are embeddings?")

        assert "[Vector DB Deep Dive - Lesson 1]" in result

    def test_result_body_contains_document_text(self):
        store = make_store(
            make_search_results(
                documents=["RAG retrieves relevant chunks before generation."],
                metadata=[{"course_title": "RAG Course", "lesson_number": 2}],
            )
        )
        tool = CourseSearchTool(store)

        result = tool.execute(query="what is RAG?")

        assert "RAG retrieves relevant chunks before generation." in result

    def test_header_omits_lesson_when_none(self):
        """If lesson_number is None in metadata, the header should not show 'Lesson'."""
        store = make_store(
            make_search_results(
                documents=["Course intro text."],
                metadata=[{"course_title": "Intro Course", "lesson_number": None}],
            )
        )
        tool = CourseSearchTool(store)

        result = tool.execute(query="intro")

        assert "[Intro Course]" in result
        assert "Lesson" not in result

    def test_multiple_results_separated_by_blank_lines(self):
        store = make_store(
            make_search_results(
                documents=["Chunk A.", "Chunk B."],
                metadata=[
                    {"course_title": "Course X", "lesson_number": 1},
                    {"course_title": "Course X", "lesson_number": 2},
                ],
            )
        )
        tool = CourseSearchTool(store)

        result = tool.execute(query="something")

        assert "Chunk A." in result
        assert "Chunk B." in result
        # Results are joined with double newlines
        assert "\n\n" in result


# ---------------------------------------------------------------------------
# Source tracking
# ---------------------------------------------------------------------------


class TestSourceTracking:
    def test_last_sources_populated_after_search(self):
        store = make_store(
            make_search_results(
                documents=["content"],
                metadata=[{"course_title": "AI Course", "lesson_number": 1}],
            )
        )
        store.get_lesson_link.return_value = "https://example.com/lesson1"
        tool = CourseSearchTool(store)

        tool.execute(query="something")

        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["label"] == "AI Course - Lesson 1"
        assert tool.last_sources[0]["url"] == "https://example.com/lesson1"

    def test_sources_deduplicated_for_same_lesson(self):
        """Two chunks from the same lesson should produce only one source entry."""
        store = make_store(
            make_search_results(
                documents=["chunk 1", "chunk 2"],
                metadata=[
                    {"course_title": "AI Course", "lesson_number": 1},
                    {"course_title": "AI Course", "lesson_number": 1},
                ],
            )
        )
        tool = CourseSearchTool(store)

        tool.execute(query="something")

        assert len(tool.last_sources) == 1

    def test_sources_empty_on_error(self):
        """An errored search must not populate last_sources."""
        store = make_store(make_error_results())
        tool = CourseSearchTool(store)

        tool.execute(query="something")

        assert tool.last_sources == []

    def test_sources_empty_on_empty_results(self):
        """No results means no sources."""
        store = make_store()
        tool = CourseSearchTool(store)

        tool.execute(query="something")

        assert tool.last_sources == []


# ---------------------------------------------------------------------------
# Parameter passthrough
# ---------------------------------------------------------------------------


class TestParameterPassthrough:
    def test_query_passed_to_store(self):
        store = make_store()
        tool = CourseSearchTool(store)

        tool.execute(query="what is transformer architecture?")

        store.search.assert_called_once_with(
            query="what is transformer architecture?",
            course_name=None,
            lesson_number=None,
        )

    def test_course_name_passed_to_store(self):
        store = make_store()
        tool = CourseSearchTool(store)

        tool.execute(query="test", course_name="MCP")

        store.search.assert_called_once_with(
            query="test", course_name="MCP", lesson_number=None
        )

    def test_lesson_number_passed_to_store(self):
        store = make_store()
        tool = CourseSearchTool(store)

        tool.execute(query="test", lesson_number=5)

        store.search.assert_called_once_with(
            query="test", course_name=None, lesson_number=5
        )

    def test_all_params_passed_together(self):
        store = make_store()
        tool = CourseSearchTool(store)

        tool.execute(query="embeddings", course_name="Vector DB", lesson_number=3)

        store.search.assert_called_once_with(
            query="embeddings", course_name="Vector DB", lesson_number=3
        )
