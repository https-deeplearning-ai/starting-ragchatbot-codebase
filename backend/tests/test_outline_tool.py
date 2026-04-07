"""
Tests for CourseOutlineTool.execute() in search_tools.py.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from search_tools import CourseOutlineTool
from vector_store import VectorStore
from config import config


@pytest.fixture(scope="module")
def tool():
    store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
    return CourseOutlineTool(store)


def test_tool_definition_shape(tool):
    """get_tool_definition() must return a valid Anthropic tool schema."""
    defn = tool.get_tool_definition()
    assert defn["name"] == "get_course_outline"
    assert "description" in defn
    assert defn["input_schema"]["required"] == ["course_title"]


def test_known_course_returns_title_and_lessons(tool):
    """A known course name should return its title and at least one lesson."""
    result = tool.execute(course_title="MCP")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert "Course:" in result, f"Missing 'Course:' header: {result!r}"
    assert "Lesson" in result, f"Expected lesson list, got: {result!r}"


def test_known_course_includes_link(tool):
    """Result for a known course should include a course link."""
    result = tool.execute(course_title="MCP")
    assert "Link:" in result, f"Expected 'Link:' in result: {result!r}"


def test_unknown_course_returns_error_string(tool):
    """An unknown course name must return an informative error string, not raise."""
    result = tool.execute(course_title="ZZZ_TOTALLY_NONEXISTENT_COURSE_XYZ")
    assert isinstance(result, str)
    assert "no course found" in result.lower(), (
        f"Expected 'No course found' message, got: {result!r}"
    )


def test_execute_never_raises(tool):
    """execute() must not raise for any input."""
    try:
        result = tool.execute(course_title="asdfjkl qwerty")
        assert isinstance(result, str)
    except Exception as e:
        pytest.fail(f"CourseOutlineTool.execute() raised: {e}")
