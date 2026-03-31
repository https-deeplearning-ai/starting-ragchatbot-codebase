"""
Tests for CourseSearchTool.execute() in search_tools.py.

Unit tests use a mocked VectorStore to isolate CourseSearchTool logic.
The integration test uses a real in-memory ChromaDB with max_results=0
to expose the configuration bug.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add backend to path so imports work when running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool
from vector_store import SearchResults, VectorStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_store(docs=None, metadata=None, error=None):
    """Return a MagicMock VectorStore whose search() returns controlled data."""
    store = MagicMock(spec=VectorStore)
    if error:
        store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=error
        )
    else:
        store.search.return_value = SearchResults(
            documents=docs or [],
            metadata=metadata or [],
            distances=[0.1] * len(docs or []),
        )
    return store


# ---------------------------------------------------------------------------
# Unit tests — all use mocked VectorStore
# ---------------------------------------------------------------------------

class TestCourseSearchToolExecuteUnit:

    def test_execute_returns_formatted_results(self):
        """execute() formats documents with course/lesson context headers."""
        store = make_mock_store(
            docs=["Transformers are attention-based models."],
            metadata=[{"course_title": "AI Basics", "lesson_number": 2}],
        )
        tool = CourseSearchTool(store)
        result = tool.execute(query="what are transformers")

        assert "AI Basics" in result
        assert "Lesson 2" in result
        assert "Transformers are attention-based models." in result

    def test_execute_returns_empty_message_when_no_results(self):
        """execute() returns a human-readable 'not found' string when empty."""
        store = make_mock_store(docs=[], metadata=[])
        tool = CourseSearchTool(store)
        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_returns_empty_message_includes_course_filter(self):
        """Empty result message includes the course filter name."""
        store = make_mock_store(docs=[], metadata=[])
        tool = CourseSearchTool(store)
        result = tool.execute(query="something", course_name="Python 101")

        assert "No relevant content found" in result
        assert "Python 101" in result

    def test_execute_returns_error_string_on_search_error(self):
        """When VectorStore returns an error, execute() returns that error string."""
        store = make_mock_store(error="Search error: n_results must be a positive integer")
        tool = CourseSearchTool(store)
        result = tool.execute(query="anything")

        assert "Search error" in result

    def test_execute_populates_last_sources(self):
        """After a successful search, last_sources contains course+lesson strings."""
        store = make_mock_store(
            docs=["Content A", "Content B"],
            metadata=[
                {"course_title": "Course X", "lesson_number": 1},
                {"course_title": "Course X", "lesson_number": 3},
            ],
        )
        tool = CourseSearchTool(store)
        tool.execute(query="something")

        assert len(tool.last_sources) == 2
        assert "Course X - Lesson 1" in tool.last_sources
        assert "Course X - Lesson 3" in tool.last_sources

    def test_execute_last_sources_empty_on_error(self):
        """last_sources stays empty when the search returns an error."""
        store = make_mock_store(error="Search error: n_results must be a positive integer")
        tool = CourseSearchTool(store)
        tool.execute(query="something")

        assert tool.last_sources == []

    def test_execute_passes_course_name_to_store(self):
        """course_name kwarg is forwarded to VectorStore.search()."""
        store = make_mock_store(docs=[], metadata=[])
        tool = CourseSearchTool(store)
        tool.execute(query="topic", course_name="MCP Course")

        store.search.assert_called_once_with(
            query="topic", course_name="MCP Course", lesson_number=None
        )

    def test_execute_passes_lesson_number_to_store(self):
        """lesson_number kwarg is forwarded to VectorStore.search()."""
        store = make_mock_store(docs=[], metadata=[])
        tool = CourseSearchTool(store)
        tool.execute(query="topic", lesson_number=4)

        store.search.assert_called_once_with(
            query="topic", course_name=None, lesson_number=4
        )


# ---------------------------------------------------------------------------
# Integration test — uses a real in-memory ChromaDB with max_results=0
# This test is EXPECTED TO FAIL on the broken system, exposing the bug.
# ---------------------------------------------------------------------------

class TestCourseSearchToolIntegration:

    @pytest.fixture()
    def in_memory_store_broken(self, tmp_path):
        """VectorStore backed by ChromaDB with max_results=0 (broken config)."""
        store = VectorStore(
            chroma_path=str(tmp_path / "chroma"),
            embedding_model="all-MiniLM-L6-v2",
            max_results=0,  # Mirrors the broken config value
        )
        # Add one document so the collection is non-empty
        from models import Course, Lesson, CourseChunk
        course = Course(
            title="Test Course",
            course_link="http://example.com",
            instructor="Test Instructor",
            lessons=[Lesson(lesson_number=1, title="Intro", lesson_link="http://example.com/1")],
        )
        store.add_course_metadata(course)
        store.add_course_content([
            CourseChunk(
                content="This lesson covers the basics of Python.",
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
            )
        ])
        return store

    @pytest.fixture()
    def in_memory_store_fixed(self, tmp_path):
        """VectorStore backed by ChromaDB with max_results=5 (correct config)."""
        store = VectorStore(
            chroma_path=str(tmp_path / "chroma_fixed"),
            embedding_model="all-MiniLM-L6-v2",
            max_results=5,  # Correct value
        )
        from models import Course, Lesson, CourseChunk
        course = Course(
            title="Test Course",
            course_link="http://example.com",
            instructor="Test Instructor",
            lessons=[Lesson(lesson_number=1, title="Intro", lesson_link="http://example.com/1")],
        )
        store.add_course_metadata(course)
        store.add_course_content([
            CourseChunk(
                content="This lesson covers the basics of Python.",
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
            )
        ])
        return store

    def test_search_with_zero_max_results_returns_error(self, in_memory_store_broken):
        """
        Documents the bug: with max_results=0, ChromaDB raises ValueError and
        VectorStore wraps it as a 'Search error' string instead of returning content.
        This test PASSES because it asserts the broken behavior exists.
        The FIX is in config.py: MAX_RESULTS=5 so the production store never uses 0.
        """
        tool = CourseSearchTool(in_memory_store_broken)
        result = tool.execute(query="Python basics")

        # max_results=0 causes ChromaDB to raise:
        # "Number of requested results 0, cannot be negative, or zero."
        assert "Search error" in result, (
            "Expected a search error with max_results=0 — "
            "the bug behavior is not reproducible."
        )

    def test_search_with_positive_max_results_returns_content(self, in_memory_store_fixed):
        """With max_results=5, search returns actual course content."""
        tool = CourseSearchTool(in_memory_store_fixed)
        result = tool.execute(query="Python basics")

        assert "Search error" not in result
        assert "Test Course" in result
