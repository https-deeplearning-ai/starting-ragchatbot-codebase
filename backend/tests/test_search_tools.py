"""
Tests for search_tools.py: CourseSearchTool, CourseOutlineTool, ToolManager.

Covers:
- CourseSearchTool.execute() result formatting and error handling
- Source tracking (last_sources) for the UI
- CourseOutlineTool formatting
- ToolManager registration, execution, and source lifecycle
"""
import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults

from helpers import make_search_results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_lesson_link.return_value = None  # default: no URL
    return store


@pytest.fixture
def search_tool(mock_store):
    return CourseSearchTool(mock_store)


@pytest.fixture
def outline_tool(mock_store):
    return CourseOutlineTool(mock_store)


@pytest.fixture
def tool_manager(search_tool):
    tm = ToolManager()
    tm.register_tool(search_tool)
    return tm


# ---------------------------------------------------------------------------
# CourseSearchTool.execute() — happy path
# ---------------------------------------------------------------------------

class TestCourseSearchToolExecuteHappyPath:

    def test_execute_happy_path_formats_header(self, search_tool, mock_store):
        """Result must contain [CourseName - Lesson N] bracketed header."""
        mock_store.search.return_value = make_search_results(
            docs=["Neural networks intro text"],
            meta=[{"course_title": "Deep Learning", "lesson_number": 2}],
        )
        result = search_tool.execute(query="what is a neural network")
        assert "[Deep Learning - Lesson 2]" in result
        assert "Neural networks intro text" in result

    def test_execute_happy_path_no_lesson_number(self, search_tool, mock_store):
        """Header without lesson number when lesson_number metadata is absent."""
        mock_store.search.return_value = make_search_results(
            docs=["Intro content"],
            meta=[{"course_title": "Intro Course"}],  # no lesson_number key
        )
        result = search_tool.execute(query="intro")
        assert "[Intro Course]" in result
        assert "Intro content" in result

    def test_execute_multiple_results_all_formatted(self, search_tool, mock_store):
        """All returned documents are included in the output."""
        mock_store.search.return_value = make_search_results(
            docs=["Chunk A", "Chunk B"],
            meta=[
                {"course_title": "ML Basics", "lesson_number": 1},
                {"course_title": "ML Basics", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
        )
        result = search_tool.execute(query="machine learning")
        assert "Chunk A" in result
        assert "Chunk B" in result
        assert "[ML Basics - Lesson 1]" in result
        assert "[ML Basics - Lesson 2]" in result

    def test_execute_passes_query_to_vector_store(self, search_tool, mock_store):
        """execute() forwards the query argument to VectorStore.search()."""
        mock_store.search.return_value = make_search_results()
        search_tool.execute(query="gradient descent explained")
        mock_store.search.assert_called_once()
        call_kwargs = mock_store.search.call_args.kwargs
        assert call_kwargs["query"] == "gradient descent explained"

    def test_execute_passes_course_name_filter(self, search_tool, mock_store):
        """course_name filter is forwarded to VectorStore.search()."""
        mock_store.search.return_value = make_search_results()
        search_tool.execute(query="q", course_name="Deep Learning")
        call_kwargs = mock_store.search.call_args.kwargs
        assert call_kwargs["course_name"] == "Deep Learning"

    def test_execute_passes_lesson_number_filter(self, search_tool, mock_store):
        """lesson_number filter is forwarded to VectorStore.search()."""
        mock_store.search.return_value = make_search_results()
        search_tool.execute(query="q", lesson_number=3)
        call_kwargs = mock_store.search.call_args.kwargs
        assert call_kwargs["lesson_number"] == 3


# ---------------------------------------------------------------------------
# CourseSearchTool.execute() — empty results
# ---------------------------------------------------------------------------

class TestCourseSearchToolExecuteEmptyResults:

    def test_execute_empty_results_no_filters(self, search_tool, mock_store):
        """Returns 'No relevant content found.' when results are empty and no filters."""
        mock_store.search.return_value = SearchResults.empty(None)
        result = search_tool.execute(query="obscure topic")
        assert result == "No relevant content found."

    def test_execute_empty_results_with_course_filter(self, search_tool, mock_store):
        """Includes course filter info in empty-results message."""
        mock_store.search.return_value = SearchResults.empty(None)
        result = search_tool.execute(query="x", course_name="MCP Course")
        assert result == "No relevant content found in course 'MCP Course'."

    def test_execute_empty_results_with_lesson_filter(self, search_tool, mock_store):
        """Includes lesson filter info in empty-results message."""
        mock_store.search.return_value = SearchResults.empty(None)
        result = search_tool.execute(query="x", lesson_number=3)
        assert result == "No relevant content found in lesson 3."

    def test_execute_empty_results_with_both_filters(self, search_tool, mock_store):
        """Includes both course and lesson filter info in empty-results message."""
        mock_store.search.return_value = SearchResults.empty(None)
        result = search_tool.execute(query="x", course_name="ML Basics", lesson_number=1)
        assert "in course 'ML Basics'" in result
        assert "in lesson 1" in result


# ---------------------------------------------------------------------------
# CourseSearchTool.execute() — error handling
# ---------------------------------------------------------------------------

class TestCourseSearchToolExecuteErrors:

    def test_execute_returns_error_message_from_vector_store(self, search_tool, mock_store):
        """When VectorStore returns an error, execute() returns the error string (does NOT raise)."""
        mock_store.search.return_value = SearchResults.empty("Search error: collection is empty")
        result = search_tool.execute(query="anything")
        assert result == "Search error: collection is empty"

    def test_execute_error_does_not_raise(self, search_tool, mock_store):
        """A VectorStore error must never raise an exception from execute()."""
        mock_store.search.return_value = SearchResults.empty("ChromaDB filter error")
        # Should not raise
        result = search_tool.execute(query="test")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# CourseSearchTool — source tracking
# ---------------------------------------------------------------------------

class TestCourseSearchToolSources:

    def test_sources_empty_before_any_search(self, search_tool):
        """Fresh tool instance has empty last_sources."""
        assert search_tool.last_sources == []

    def test_sources_tracked_after_successful_search(self, search_tool, mock_store):
        """last_sources is populated after a successful search."""
        mock_store.search.return_value = make_search_results(
            docs=["content"],
            meta=[{"course_title": "Intro to ML", "lesson_number": 1}],
        )
        mock_store.get_lesson_link.return_value = None
        search_tool.execute(query="gradient descent")
        assert search_tool.last_sources == ["Intro to ML - Lesson 1"]

    def test_sources_include_url_when_lesson_link_present(self, search_tool, mock_store):
        """Sources use 'CourseName - Lesson N||url' format when URL is available."""
        mock_store.search.return_value = make_search_results(
            docs=["content"],
            meta=[{"course_title": "Intro to ML", "lesson_number": 1}],
        )
        mock_store.get_lesson_link.return_value = "https://example.com/lesson1"
        search_tool.execute(query="gradient descent")
        assert search_tool.last_sources == ["Intro to ML - Lesson 1||https://example.com/lesson1"]

    def test_sources_no_url_when_no_lesson_number(self, search_tool, mock_store):
        """When lesson_number is absent in metadata, source has no lesson suffix and no URL lookup."""
        mock_store.search.return_value = make_search_results(
            docs=["content"],
            meta=[{"course_title": "General Course"}],  # no lesson_number
        )
        search_tool.execute(query="test")
        assert search_tool.last_sources == ["General Course"]
        mock_store.get_lesson_link.assert_not_called()

    def test_sources_overwritten_on_subsequent_search(self, search_tool, mock_store):
        """last_sources reflects only the most recent search (no accumulation)."""
        mock_store.search.return_value = make_search_results(
            docs=["A"],
            meta=[{"course_title": "Course A", "lesson_number": 1}],
        )
        mock_store.get_lesson_link.return_value = None
        search_tool.execute(query="first")

        mock_store.search.return_value = make_search_results(
            docs=["B"],
            meta=[{"course_title": "Course B", "lesson_number": 2}],
        )
        search_tool.execute(query="second")
        assert search_tool.last_sources == ["Course B - Lesson 2"]

    def test_sources_empty_after_empty_results(self, search_tool, mock_store):
        """last_sources stays empty when search returns no results."""
        mock_store.search.return_value = SearchResults.empty(None)
        search_tool.execute(query="nothing")
        assert search_tool.last_sources == []


# ---------------------------------------------------------------------------
# CourseOutlineTool
# ---------------------------------------------------------------------------

class TestCourseOutlineTool:

    def test_outline_happy_path_all_fields(self, outline_tool, mock_store):
        """Full outline with title, link, and lessons is formatted correctly."""
        mock_store.get_course_outline.return_value = {
            "title": "Intro to Python",
            "course_link": "https://example.com/course",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Basics"},
                {"lesson_number": 2, "lesson_title": "Functions"},
            ],
        }
        result = outline_tool.execute(course_name="Intro")
        assert "Course: Intro to Python" in result
        assert "Link: https://example.com/course" in result
        assert "Lesson 1: Basics" in result
        assert "Lesson 2: Functions" in result

    def test_outline_not_found_returns_message(self, outline_tool, mock_store):
        """Returns a 'not found' message when no matching course exists."""
        mock_store.get_course_outline.return_value = None
        result = outline_tool.execute(course_name="Nonexistent Course")
        assert result == "No course found matching 'Nonexistent Course'."

    def test_outline_no_course_link(self, outline_tool, mock_store):
        """'Link:' line is omitted when course_link is None."""
        mock_store.get_course_outline.return_value = {
            "title": "No Link Course",
            "course_link": None,
            "lessons": [{"lesson_number": 1, "lesson_title": "Lesson One"}],
        }
        result = outline_tool.execute(course_name="No Link Course")
        assert "Link:" not in result
        assert "Course: No Link Course" in result

    def test_outline_empty_lessons(self, outline_tool, mock_store):
        """Outline with no lessons has the 'Lessons:' header but no lesson entries."""
        mock_store.get_course_outline.return_value = {
            "title": "Empty Course",
            "course_link": "https://example.com",
            "lessons": [],
        }
        result = outline_tool.execute(course_name="Empty")
        assert "Course: Empty Course" in result
        # 'Lessons:' header is always present; no 'Lesson N:' entries
        assert "Lessons:" in result
        assert "Lesson 1:" not in result


# ---------------------------------------------------------------------------
# ToolManager
# ---------------------------------------------------------------------------

class TestToolManager:

    def test_tool_manager_register_and_execute(self, tool_manager, mock_store):
        """Registered tool is callable via execute_tool()."""
        mock_store.search.return_value = SearchResults.empty(None)
        result = tool_manager.execute_tool("search_course_content", query="test")
        assert isinstance(result, str)

    def test_tool_manager_unknown_tool_returns_error_string(self, tool_manager):
        """execute_tool() with an unknown name returns an error string (does NOT raise)."""
        result = tool_manager.execute_tool("nonexistent_tool", query="test")
        assert result == "Tool 'nonexistent_tool' not found"

    def test_tool_manager_get_tool_definitions_contains_registered_tools(self, mock_store):
        """get_tool_definitions() returns definitions for all registered tools."""
        tm = ToolManager()
        tm.register_tool(CourseSearchTool(mock_store))
        tm.register_tool(CourseOutlineTool(mock_store))
        defs = tm.get_tool_definitions()
        names = [d["name"] for d in defs]
        assert "search_course_content" in names
        assert "get_course_outline" in names
        assert len(defs) == 2

    def test_tool_manager_get_last_sources_empty_before_search(self, tool_manager):
        """get_last_sources() returns [] before any search."""
        assert tool_manager.get_last_sources() == []

    def test_tool_manager_get_last_sources_returns_search_tool_sources(self, tool_manager, mock_store):
        """get_last_sources() returns what CourseSearchTool set in last_sources."""
        mock_store.search.return_value = make_search_results(
            docs=["content"],
            meta=[{"course_title": "ML Basics", "lesson_number": 3}],
        )
        mock_store.get_lesson_link.return_value = None
        tool_manager.execute_tool("search_course_content", query="backprop")
        sources = tool_manager.get_last_sources()
        assert sources == ["ML Basics - Lesson 3"]

    def test_tool_manager_reset_sources_clears_all(self, tool_manager, mock_store):
        """reset_sources() clears last_sources from all tools."""
        mock_store.search.return_value = make_search_results()
        mock_store.get_lesson_link.return_value = None
        tool_manager.execute_tool("search_course_content", query="test")
        assert tool_manager.get_last_sources() != []  # sanity check
        tool_manager.reset_sources()
        assert tool_manager.get_last_sources() == []
