"""
Tests for CourseSearchTool and ToolManager.

VectorStore is mocked — no ChromaDB needed.
"""
import pytest
from unittest.mock import MagicMock
from vector_store import SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_results(docs, metas, error=None):
    sr = MagicMock(spec=SearchResults)
    sr.documents = docs
    sr.metadata = metas
    sr.distances = [0.1] * len(docs)
    sr.error = error
    sr.is_empty = MagicMock(return_value=(len(docs) == 0))
    return sr


def _make_tool(store_search_return=None, lesson_link=None):
    store = MagicMock()
    if store_search_return is not None:
        store.search.return_value = store_search_return
    store.get_lesson_link.return_value = lesson_link
    return CourseSearchTool(store), store


# ---------------------------------------------------------------------------
# execute() happy-path tests
# ---------------------------------------------------------------------------

class TestCourseSearchToolExecute:
    def test_execute_returns_formatted_results(self):
        results = _make_results(
            docs=["Variables hold data"],
            metas=[{"course_title": "Python Basics", "lesson_number": 1}],
        )
        tool, _ = _make_tool(store_search_return=results)

        output = tool.execute(query="what are variables")

        assert "Python Basics" in output
        assert "Variables hold data" in output

    def test_execute_with_course_name_filter_passes_through(self):
        results = _make_results(
            docs=["doc"],
            metas=[{"course_title": "Python Basics", "lesson_number": 1}],
        )
        tool, store = _make_tool(store_search_return=results)

        tool.execute(query="variables", course_name="Python")

        store.search.assert_called_once_with(
            query="variables",
            course_name="Python",
            lesson_number=None,
        )

    def test_execute_with_lesson_number_filter_passes_through(self):
        results = _make_results(
            docs=["doc"],
            metas=[{"course_title": "Python Basics", "lesson_number": 2}],
        )
        tool, store = _make_tool(store_search_return=results)

        tool.execute(query="functions", lesson_number=2)

        store.search.assert_called_once_with(
            query="functions",
            course_name=None,
            lesson_number=2,
        )

    def test_execute_returns_error_message_on_search_error(self):
        results = _make_results(docs=[], metas=[], error="No course found matching 'XYZ'")
        tool, _ = _make_tool(store_search_return=results)

        output = tool.execute(query="anything", course_name="XYZ")

        assert "No course found" in output

    def test_execute_returns_no_content_message_on_empty_results(self):
        results = _make_results(docs=[], metas=[])
        tool, _ = _make_tool(store_search_return=results)

        output = tool.execute(query="obscure topic")

        assert "No relevant content found" in output

    def test_execute_includes_course_and_lesson_in_filter_message(self):
        results = _make_results(docs=[], metas=[])
        tool, _ = _make_tool(store_search_return=results)

        output = tool.execute(query="obscure topic", course_name="Python", lesson_number=3)

        assert "Python" in output
        assert "3" in output


# ---------------------------------------------------------------------------
# Source tracking tests
# ---------------------------------------------------------------------------

class TestCourseSearchToolSources:
    def test_last_sources_includes_url_when_lesson_link_available(self):
        results = _make_results(
            docs=["doc"],
            metas=[{"course_title": "Python Basics", "lesson_number": 1}],
        )
        tool, store = _make_tool(store_search_return=results, lesson_link="https://example.com/1")

        tool.execute(query="variables")

        assert tool.last_sources == ["Python Basics - Lesson 1|https://example.com/1"]

    def test_last_sources_plain_label_when_no_lesson_link(self):
        results = _make_results(
            docs=["doc"],
            metas=[{"course_title": "Python Basics", "lesson_number": 1}],
        )
        tool, store = _make_tool(store_search_return=results, lesson_link=None)

        tool.execute(query="variables")

        assert tool.last_sources == ["Python Basics - Lesson 1"]

    def test_last_sources_reset_between_calls(self):
        results_1 = _make_results(
            docs=["doc1"],
            metas=[{"course_title": "Course A", "lesson_number": 1}],
        )
        results_2 = _make_results(
            docs=["doc2"],
            metas=[{"course_title": "Course B", "lesson_number": 2}],
        )
        store = MagicMock()
        store.search.side_effect = [results_1, results_2]
        store.get_lesson_link.return_value = None
        tool = CourseSearchTool(store)

        tool.execute(query="first query")
        sources_after_first = list(tool.last_sources)

        tool.execute(query="second query")
        sources_after_second = list(tool.last_sources)

        assert sources_after_first == ["Course A - Lesson 1"]
        assert sources_after_second == ["Course B - Lesson 2"]
        # Crucially: no bleed-through from call 1
        assert "Course A" not in " ".join(sources_after_second)

    def test_last_sources_no_lesson_number(self):
        """When lesson_number is None in metadata, source label has no 'Lesson N' suffix."""
        results = _make_results(
            docs=["doc"],
            metas=[{"course_title": "Python Basics", "lesson_number": None}],
        )
        tool, _ = _make_tool(store_search_return=results, lesson_link=None)

        tool.execute(query="variables")

        assert tool.last_sources == ["Python Basics"]


# ---------------------------------------------------------------------------
# ToolManager tests
# ---------------------------------------------------------------------------

class TestToolManager:
    def test_register_and_execute_tool(self):
        manager = ToolManager()
        mock_tool = MagicMock()
        mock_tool.get_tool_definition.return_value = {"name": "my_tool"}
        mock_tool.execute.return_value = "tool output"

        manager.register_tool(mock_tool)
        result = manager.execute_tool("my_tool", foo="bar")

        mock_tool.execute.assert_called_once_with(foo="bar")
        assert result == "tool output"

    def test_execute_unknown_tool_returns_error(self):
        manager = ToolManager()
        result = manager.execute_tool("nonexistent_tool")
        assert "not found" in result

    def test_get_last_sources_aggregates_across_tools(self):
        manager = ToolManager()
        mock_tool = MagicMock()
        mock_tool.get_tool_definition.return_value = {"name": "search_tool"}
        mock_tool.last_sources = ["Source A", "Source B"]

        manager.register_tool(mock_tool)
        sources = manager.get_last_sources()

        assert sources == ["Source A", "Source B"]

    def test_reset_sources_clears_all_tools(self):
        manager = ToolManager()
        mock_tool = MagicMock()
        mock_tool.get_tool_definition.return_value = {"name": "search_tool"}
        mock_tool.last_sources = ["Source A"]

        manager.register_tool(mock_tool)
        manager.reset_sources()

        assert mock_tool.last_sources == []

    def test_get_tool_definitions_returns_all_registered(self):
        manager = ToolManager()
        for name in ("tool_a", "tool_b"):
            t = MagicMock()
            t.get_tool_definition.return_value = {"name": name}
            manager.register_tool(t)

        defs = manager.get_tool_definitions()

        names = [d["name"] for d in defs]
        assert "tool_a" in names
        assert "tool_b" in names

    def test_register_tool_without_name_raises_value_error(self):
        manager = ToolManager()
        bad_tool = MagicMock()
        bad_tool.get_tool_definition.return_value = {}  # no "name" key

        with pytest.raises(ValueError):
            manager.register_tool(bad_tool)


# ---------------------------------------------------------------------------
# CourseOutlineTool tests
# ---------------------------------------------------------------------------

class TestCourseOutlineTool:
    def _make_outline_tool(self, outline_return):
        store = MagicMock()
        store.get_course_outline.return_value = outline_return
        return CourseOutlineTool(store), store

    def test_execute_no_course_returns_not_found_message(self):
        tool, _ = self._make_outline_tool(None)
        result = tool.execute(course_title="Unknown Course")
        assert "No course found" in result
        assert "Unknown Course" in result

    def test_execute_includes_course_title(self):
        outline = {
            "title": "Python Basics",
            "course_link": "https://example.com/python",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Variables", "lesson_link": None}
            ]
        }
        tool, _ = self._make_outline_tool(outline)
        result = tool.execute(course_title="Python")
        assert "Python Basics" in result

    def test_execute_includes_course_link_when_present(self):
        outline = {
            "title": "Python Basics",
            "course_link": "https://example.com/python",
            "lessons": []
        }
        tool, _ = self._make_outline_tool(outline)
        result = tool.execute(course_title="Python")
        assert "https://example.com/python" in result

    def test_execute_omits_link_line_when_absent(self):
        outline = {
            "title": "Python Basics",
            "course_link": None,
            "lessons": []
        }
        tool, _ = self._make_outline_tool(outline)
        result = tool.execute(course_title="Python")
        assert "Link:" not in result

    def test_execute_lists_all_lessons(self):
        outline = {
            "title": "Python Basics",
            "course_link": None,
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Variables", "lesson_link": None},
                {"lesson_number": 2, "lesson_title": "Functions", "lesson_link": None},
                {"lesson_number": 3, "lesson_title": "Classes", "lesson_link": None},
            ]
        }
        tool, _ = self._make_outline_tool(outline)
        result = tool.execute(course_title="Python")
        assert "Lesson 1: Variables" in result
        assert "Lesson 2: Functions" in result
        assert "Lesson 3: Classes" in result

    def test_execute_shows_lesson_count(self):
        outline = {
            "title": "Python Basics",
            "course_link": None,
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Variables", "lesson_link": None},
                {"lesson_number": 2, "lesson_title": "Functions", "lesson_link": None},
            ]
        }
        tool, _ = self._make_outline_tool(outline)
        result = tool.execute(course_title="Python")
        assert "2" in result  # lesson count appears somewhere
