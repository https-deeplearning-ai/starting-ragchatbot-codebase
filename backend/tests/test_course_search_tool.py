"""
Objective 1: pure unit tests for CourseSearchTool and ToolManager.
VectorStore is fully mocked -- no real Chroma, no network.
"""

import pytest

from search_tools import CourseOutlineTool, CourseSearchTool, Source, Tool, ToolManager


class TestCourseSearchToolFormatting:
    def test_successful_search_formats_headers_and_joins_with_blank_line(
        self, mock_vector_store, make_results
    ):
        mock_vector_store.search.return_value = make_results(
            documents=["doc1 text", "doc2 text"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course A", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
        )
        mock_vector_store.get_lesson_link.return_value = None
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test")

        assert result == (
            "[Course A - Lesson 1]\ndoc1 text\n\n" "[Course A - Lesson 2]\ndoc2 text"
        )
        mock_vector_store.search.assert_called_once_with(
            query="test", course_name=None, lesson_number=None
        )

    def test_sources_tracked_and_deduped_by_course_and_lesson(
        self, mock_vector_store, make_results
    ):
        mock_vector_store.search.return_value = make_results(
            documents=["chunk1", "chunk2", "chunk3"],
            metadata=[
                {"course_title": "X", "lesson_number": 1},
                {"course_title": "X", "lesson_number": 1},  # duplicate lesson
                {"course_title": "X", "lesson_number": 2},
            ],
        )
        mock_vector_store.get_lesson_link.return_value = "https://lesson-link"
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test")

        assert len(tool.last_sources) == 2
        assert tool.last_sources[0] == Source(
            text="X - Lesson 1", link="https://lesson-link"
        )
        assert tool.last_sources[1] == Source(
            text="X - Lesson 2", link="https://lesson-link"
        )
        # dedup means the second chunk from lesson 1 must NOT trigger a second link lookup
        assert mock_vector_store.get_lesson_link.call_count == 2

    def test_lesson_scoped_source_uses_lesson_link_course_level_uses_course_link(
        self, mock_vector_store, make_results
    ):
        mock_vector_store.search.return_value = make_results(
            documents=["with lesson", "without lesson"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 2},
                {"course_title": "Course B"},  # no lesson_number key -> None
            ],
        )
        mock_vector_store.get_lesson_link.return_value = "https://lesson-link"
        mock_vector_store.get_course_link.return_value = "https://course-link"
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test")

        assert tool.last_sources == [
            Source(text="Course A - Lesson 2", link="https://lesson-link"),
            Source(text="Course B", link="https://course-link"),
        ]
        mock_vector_store.get_lesson_link.assert_called_once_with("Course A", 2)
        mock_vector_store.get_course_link.assert_called_once_with("Course B")


class TestCourseSearchToolEmptyResultsMessage:
    def test_empty_with_course_name_only(self, mock_vector_store, make_results):
        mock_vector_store.search.return_value = make_results()
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="q", course_name="Foo")

        assert result == "No relevant content found in course 'Foo'."

    def test_empty_with_positive_lesson_number_only(
        self, mock_vector_store, make_results
    ):
        mock_vector_store.search.return_value = make_results()
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="q", lesson_number=3)

        assert result == "No relevant content found in lesson 3."

    def test_empty_with_lesson_number_zero_should_mention_lesson_zero(
        self, mock_vector_store, make_results
    ):
        mock_vector_store.search.return_value = make_results()
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="q", lesson_number=0)

        assert result == "No relevant content found in lesson 0."

    def test_empty_with_neither_filter(self, mock_vector_store, make_results):
        mock_vector_store.search.return_value = make_results()
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="q")

        assert result == "No relevant content found."

    def test_error_returned_verbatim_without_formatting(
        self, mock_vector_store, make_results
    ):
        mock_vector_store.search.return_value = make_results(
            error="No course found matching 'Bogus'"
        )
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="q", course_name="Bogus")

        assert result == "No course found matching 'Bogus'"
        mock_vector_store.get_course_link.assert_not_called()
        mock_vector_store.get_lesson_link.assert_not_called()


class TestCourseSearchToolDefinition:
    def test_tool_definition_schema_shape(self, mock_vector_store):
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert definition["input_schema"]["required"] == ["query"]
        props = definition["input_schema"]["properties"]
        assert props["query"]["type"] == "string"
        assert props["course_name"]["type"] == "string"
        assert props["lesson_number"]["type"] == "integer"


class TestToolManager:
    def test_register_tool_requires_a_name(self):
        class NamelessTool(Tool):
            def get_tool_definition(self):
                return {"description": "no name field"}

            def execute(self, **kwargs):
                return "irrelevant"

        manager = ToolManager()
        with pytest.raises(ValueError):
            manager.register_tool(NamelessTool())

    def test_execute_tool_unknown_name_returns_message_not_exception(self):
        manager = ToolManager()
        result = manager.execute_tool("does_not_exist", query="x")
        assert result == "Tool 'does_not_exist' not found"

    def test_get_last_sources_sorted_alphabetically_by_text(
        self, mock_vector_store, make_results
    ):
        tool = CourseSearchTool(mock_vector_store)
        manager = ToolManager()
        manager.register_tool(tool)
        mock_vector_store.search.return_value = make_results(
            documents=["a", "b"],
            metadata=[
                {"course_title": "Zebra Course"},
                {"course_title": "Alpha Course"},
            ],
        )
        mock_vector_store.get_course_link.return_value = None
        tool.execute(query="x")

        sources = manager.get_last_sources()

        assert [s.text for s in sources] == ["Alpha Course", "Zebra Course"]

    def test_reset_sources_clears_all_registered_tools(
        self, mock_vector_store, make_results
    ):
        tool = CourseSearchTool(mock_vector_store)
        manager = ToolManager()
        manager.register_tool(tool)
        mock_vector_store.search.return_value = make_results(
            documents=["a"], metadata=[{"course_title": "X"}]
        )
        mock_vector_store.get_course_link.return_value = None
        tool.execute(query="x")
        assert manager.get_last_sources() != []

        manager.reset_sources()

        assert manager.get_last_sources() == []

    def test_get_last_sources_only_surfaces_first_tool_with_sources(
        self, mock_vector_store
    ):
        """
        Documents existing behavior: get_last_sources returns only the first
        registered tool whose last_sources is non-empty -- it does not merge
        across tools. Only reachable today if the model emits >1 tool_use
        block of different tool types in a single turn (ai_generator.py does
        not prevent that, even though the system prompt asks for at most one
        tool call per query).
        """
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)
        manager = ToolManager()
        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        search_tool.last_sources = [Source(text="From search tool")]
        outline_tool.last_sources = [Source(text="From outline tool")]

        sources = manager.get_last_sources()

        assert [s.text for s in sources] == ["From search tool"]
