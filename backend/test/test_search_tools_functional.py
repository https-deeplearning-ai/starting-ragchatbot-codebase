"""Functional tests: CourseSearchTool / CourseOutlineTool / ToolManager against a real
(temporary) ChromaDB with local embeddings. No Anthropic calls."""
import pytest

from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager

COMPUTER_USE = "Building Towards Computer Use with Anthropic"


@pytest.fixture
def search(rag):
    return CourseSearchTool(rag.vector_store)


@pytest.fixture
def outline(rag):
    return CourseOutlineTool(rag.vector_store)


def test_search_returns_formatted_results_and_sources(search):
    out = search.execute("computer use screenshot mouse clicks")
    assert out.startswith("[")  # "[Course - Lesson N]" header
    assert "Lesson" in out
    assert search.last_sources
    assert all({"text", "url"} <= s.keys() for s in search.last_sources)
    texts = [s["text"] for s in search.last_sources]
    assert len(texts) == len(set(texts))  # de-duplicated


def test_search_partial_course_name_resolves(search):
    out = search.execute("what is covered", course_name="Computer Use")
    assert COMPUTER_USE in out
    assert all(s["text"].startswith(COMPUTER_USE) for s in search.last_sources)


def test_search_lesson_filter(search):
    out = search.execute("introduction", course_name="Computer Use", lesson_number=0)
    assert "Lesson 0" in out
    assert all(s["text"].endswith("Lesson 0") for s in search.last_sources)
    assert all(s["url"] and s["url"].startswith("http") for s in search.last_sources)


def test_search_no_results_message(search):
    out = search.execute("anything", course_name="Computer Use", lesson_number=999)
    assert out == "No relevant content found in course 'Computer Use' in lesson 999."


def test_outline_returns_full_lesson_list(outline, rag):
    out = outline.execute("Computer Use")
    assert f"Course: {COMPUTER_USE}" in out
    assert "Instructor: Colt Steele" in out
    assert "Course link: https://" in out
    lessons = rag.vector_store.get_course_outline("Computer Use")["lessons"]
    assert f"Lessons ({len(lessons)}):" in out
    for lesson in lessons:
        assert f"Lesson {lesson['lesson_number']}: {lesson['lesson_title']}" in out
    assert outline.last_sources == [
        {"text": COMPUTER_USE, "url": outline.last_sources[0]["url"]}
    ]


def test_outline_unknown_course_still_resolves_nearest(outline):
    # Fuzzy top-1 matching means any non-empty name resolves to some course.
    assert outline.execute("zzzz").startswith("Course:")


def test_tool_manager_dispatch_sources_and_reset(rag):
    tm = ToolManager()
    tm.register_tool(CourseSearchTool(rag.vector_store))
    tm.register_tool(CourseOutlineTool(rag.vector_store))
    names = {d["name"] for d in tm.get_tool_definitions()}
    assert names == {"search_course_content", "get_course_outline"}

    assert "Course:" in tm.execute_tool("get_course_outline", course_name="MCP")
    assert tm.get_last_sources()
    tm.reset_sources()
    assert tm.get_last_sources() == []
    assert tm.execute_tool("nope") == "Tool 'nope' not found"
