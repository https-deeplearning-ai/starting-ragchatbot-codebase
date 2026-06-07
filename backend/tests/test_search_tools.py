"""
Tests for CourseSearchTool.execute() in search_tools.py.

Covers:
- Unit tests using a mocked VectorStore (fast, no ChromaDB I/O)
- Integration tests using a real temp ChromaDB (validates the full retrieval path)
"""

from unittest.mock import MagicMock
import pytest

from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_search_results(docs, metas):
    """Build a SearchResults from lists of docs and metadata dicts."""
    return SearchResults(
        documents=docs,
        metadata=metas,
        distances=[0.1] * len(docs),
    )


def _make_error_results(msg):
    return SearchResults.empty(msg)


# ---------------------------------------------------------------------------
# Unit tests — VectorStore is mocked
# ---------------------------------------------------------------------------

class TestCourseSearchToolExecute:

    def setup_method(self):
        self.mock_store = MagicMock()
        self.tool = CourseSearchTool(self.mock_store)

    # --- happy path ---

    def test_execute_returns_formatted_results_when_results_exist(self):
        self.mock_store.search.return_value = _make_search_results(
            docs=["RAG combines retrieval with generation."],
            metas=[{"course_title": "Introduction to RAG", "lesson_number": 1}],
        )
        result = self.tool.execute(query="what is RAG")

        assert "Introduction to RAG" in result
        assert "Lesson 1" in result
        assert "RAG combines retrieval with generation." in result

    def test_execute_passes_query_to_store(self):
        self.mock_store.search.return_value = _make_search_results(
            docs=["some content"],
            metas=[{"course_title": "Course A", "lesson_number": 0}],
        )
        self.tool.execute(query="vector databases")

        self.mock_store.search.assert_called_once_with(
            query="vector databases",
            course_name=None,
            lesson_number=None,
        )

    def test_execute_forwards_course_name_filter(self):
        self.mock_store.search.return_value = _make_search_results(
            docs=["content"], metas=[{"course_title": "RAG Course", "lesson_number": 1}]
        )
        self.tool.execute(query="embeddings", course_name="RAG")

        self.mock_store.search.assert_called_once_with(
            query="embeddings", course_name="RAG", lesson_number=None
        )

    def test_execute_forwards_lesson_number_filter(self):
        self.mock_store.search.return_value = _make_search_results(
            docs=["content"], metas=[{"course_title": "RAG Course", "lesson_number": 2}]
        )
        self.tool.execute(query="chroma", lesson_number=2)

        self.mock_store.search.assert_called_once_with(
            query="chroma", course_name=None, lesson_number=2
        )

    # --- empty results ---

    def test_execute_returns_no_results_message_when_empty(self):
        self.mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        result = self.tool.execute(query="something obscure")

        assert "No relevant content found" in result

    def test_execute_no_results_message_includes_course_name_filter(self):
        self.mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        result = self.tool.execute(query="test", course_name="Nonexistent Course")

        assert "Nonexistent Course" in result

    def test_execute_no_results_message_includes_lesson_filter(self):
        self.mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        result = self.tool.execute(query="test", lesson_number=99)

        assert "lesson 99" in result

    # --- error handling ---

    def test_execute_returns_error_string_when_store_errors(self):
        self.mock_store.search.return_value = _make_error_results(
            "No course found matching 'XYZ'"
        )
        result = self.tool.execute(query="anything", course_name="XYZ")

        assert "No course found matching 'XYZ'" in result

    # --- source tracking ---

    def test_execute_updates_last_sources_with_course_and_lesson(self):
        self.mock_store.search.return_value = _make_search_results(
            docs=["doc1", "doc2"],
            metas=[
                {"course_title": "RAG Course", "lesson_number": 1},
                {"course_title": "RAG Course", "lesson_number": 2},
            ],
        )
        self.tool.execute(query="test")

        assert self.tool.last_sources == [
            "RAG Course - Lesson 1",
            "RAG Course - Lesson 2",
        ]

    def test_execute_clears_last_sources_from_previous_call(self):
        self.mock_store.search.return_value = _make_search_results(
            docs=["doc"],
            metas=[{"course_title": "Course A", "lesson_number": 1}],
        )
        self.tool.execute(query="first")

        self.mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        self.tool.execute(query="second that returns nothing")

        assert self.tool.last_sources == [], (
            "last_sources was not cleared before the second search. "
            "Sources from the previous call leaked through — the UI would "
            "show stale citations for the new response."
        )


# ---------------------------------------------------------------------------
# ToolManager unit tests
# ---------------------------------------------------------------------------

class TestToolManager:

    def test_register_and_execute_tool(self):
        manager = ToolManager()
        mock_store = MagicMock()
        mock_store.search.return_value = _make_search_results(
            ["content"], [{"course_title": "T", "lesson_number": 1}]
        )
        tool = CourseSearchTool(mock_store)
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="test")

        assert "content" in result

    def test_execute_unknown_tool_returns_error_string(self):
        manager = ToolManager()
        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result.lower()

    def test_get_last_sources_returns_sources_from_search_tool(self):
        manager = ToolManager()
        mock_store = MagicMock()
        mock_store.search.return_value = _make_search_results(
            ["doc"], [{"course_title": "Course", "lesson_number": 1}]
        )
        tool = CourseSearchTool(mock_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="test")
        sources = manager.get_last_sources()

        assert sources == ["Course - Lesson 1"]

    def test_reset_sources_clears_last_sources(self):
        manager = ToolManager()
        mock_store = MagicMock()
        mock_store.search.return_value = _make_search_results(
            ["doc"], [{"course_title": "Course", "lesson_number": 1}]
        )
        tool = CourseSearchTool(mock_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="test")
        manager.reset_sources()

        assert manager.get_last_sources() == []


# ---------------------------------------------------------------------------
# Integration tests — real temp ChromaDB
# ---------------------------------------------------------------------------

class TestCourseSearchToolIntegration:
    """Uses a real populated VectorStore fixture (temp ChromaDB)."""

    def test_search_returns_results_for_relevant_query(self, populated_vector_store):
        tool = CourseSearchTool(populated_vector_store)
        result = tool.execute(query="retrieval augmented generation")

        assert "Introduction to RAG" in result
        assert "No relevant content found" not in result

    def test_search_with_exact_course_name(self, populated_vector_store):
        tool = CourseSearchTool(populated_vector_store)
        result = tool.execute(query="embeddings", course_name="Introduction to RAG")

        assert "Introduction to RAG" in result

    def test_search_with_lesson_filter(self, populated_vector_store):
        tool = CourseSearchTool(populated_vector_store)
        result = tool.execute(query="vector database", lesson_number=2)

        assert "Lesson 2" in result

    def test_search_with_nonexistent_course_resolves_to_closest_match(self, populated_vector_store):
        # _resolve_course_name uses vector similarity — it always returns the
        # nearest course in the catalog, so no "No course found" error is raised
        # for a fabricated name; instead the closest real course's content is returned.
        tool = CourseSearchTool(populated_vector_store)
        result = tool.execute(query="test", course_name="Does Not Exist At All")

        # The catalog only contains "Introduction to RAG"; that will be matched.
        assert "Introduction to RAG" in result

    def test_search_populates_last_sources(self, populated_vector_store):
        tool = CourseSearchTool(populated_vector_store)
        tool.execute(query="chromadb vector database")

        assert len(tool.last_sources) > 0
        assert all("Introduction to RAG" in s for s in tool.last_sources)
