"""1. Outputs of CourseSearchTool.execute"""

from conftest import MCP, make_results

from search_tools import CourseSearchTool


def test_formats_results_with_course_and_lesson_headers(mock_store):
    mock_store.search.return_value = make_results(
        [
            ("MCP is a protocol.", MCP, 1, 3),
            ("Servers expose tools.", MCP, 2, 7),
        ]
    )
    tool = CourseSearchTool(mock_store)

    out = tool.execute(query="what is MCP")

    assert out == (
        f"[{MCP} - Lesson 1]\nMCP is a protocol.\n\n"
        f"[{MCP} - Lesson 2]\nServers expose tools."
    )


def test_passes_filters_through_to_store(mock_store):
    mock_store.search.return_value = make_results([("x", MCP, 5, 1)])
    CourseSearchTool(mock_store).execute(query="q", course_name="MCP", lesson_number=5)

    mock_store.search.assert_called_once_with(
        query="q", course_name="MCP", lesson_number=5
    )


def test_lesson_filtered_search_returns_formatted_text(mock_store):
    """The 'Details of a course's lesson' path: several chunks from one lesson."""
    mock_store.search.return_value = make_results(
        [
            ("Second part.", MCP, 5, 41),
            ("First part.", MCP, 5, 40),
        ]
    )

    out = CourseSearchTool(mock_store).execute(
        query="lesson 5", course_name="MCP", lesson_number=5
    )

    assert isinstance(out, str)
    assert "First part." in out and "Second part." in out


def test_lesson_filtered_chunks_are_in_reading_order(mock_store):
    mock_store.search.return_value = make_results(
        [
            ("Third.", MCP, 5, 42),
            ("First.", MCP, 5, 40),
            ("Second.", MCP, 5, 41),
        ]
    )

    out = CourseSearchTool(mock_store).execute(query="q", lesson_number=5)

    assert out.index("First.") < out.index("Second.") < out.index("Third.")


def test_sources_are_deduplicated_per_lesson_with_links(mock_store):
    mock_store.search.return_value = make_results(
        [
            ("a", MCP, 1, 1),
            ("b", MCP, 1, 2),
            ("c", MCP, 2, 9),
        ]
    )
    tool = CourseSearchTool(mock_store)
    tool.execute(query="q")

    assert tool.last_sources == [
        {"label": f"{MCP} - Lesson 1", "url": "https://example.com/mcp/lesson1"},
        {"label": f"{MCP} - Lesson 2", "url": "https://example.com/mcp/lesson2"},
    ]
    # Link lookups are cached: one per lesson, not per chunk
    assert mock_store.get_lesson_link.call_count == 2


def test_chunk_without_lesson_has_no_link(mock_store):
    mock_store.search.return_value = make_results([("intro", MCP, None, 0)])
    tool = CourseSearchTool(mock_store)

    out = tool.execute(query="q")

    assert out == f"[{MCP}]\nintro"
    assert tool.last_sources == [{"label": MCP, "url": None}]
    mock_store.get_lesson_link.assert_not_called()


def test_store_error_is_returned_as_text(mock_store):
    mock_store.search.return_value = make_results(
        [], error="No course found matching 'Zzz'"
    )
    tool = CourseSearchTool(mock_store)

    assert (
        tool.execute(query="q", course_name="Zzz") == "No course found matching 'Zzz'"
    )
    assert tool.last_sources == []


def test_empty_results_message_includes_filters(mock_store):
    mock_store.search.return_value = make_results([])
    out = CourseSearchTool(mock_store).execute(
        query="q", course_name="MCP", lesson_number=3
    )

    assert out == "No relevant content found in course 'MCP' in lesson 3."


def test_empty_results_message_mentions_lesson_zero(mock_store):
    """Lesson 0 (Introduction) is a real lesson and should be reported like any other."""
    mock_store.search.return_value = make_results([])
    out = CourseSearchTool(mock_store).execute(
        query="q", course_name="MCP", lesson_number=0
    )

    assert out == "No relevant content found in course 'MCP' in lesson 0."
