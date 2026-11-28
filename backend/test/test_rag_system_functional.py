"""Functional tests for RAGSystem.query retrieval logic.

Most tests script the model (a fake generator that calls the tools through the real
ToolManager, as Claude would) so retrieval, sources and sessions are verified without
the Anthropic API. The last test uses the real API.
"""
import pytest


class ScriptedGenerator:
    """Stands in for AIGenerator: runs the given (tool, kwargs) calls, returns text."""

    def __init__(self, calls, answer="scripted answer"):
        self.calls, self.answer, self.seen = calls, answer, []

    def generate_response(self, query, conversation_history=None, tools=None,
                          tool_manager=None):
        self.seen.append((query, conversation_history, tools))
        for name, kwargs in self.calls:
            tool_manager.execute_tool(name, **kwargs)
        return self.answer


@pytest.fixture
def scripted(rag):
    real = rag.ai_generator

    def install(calls, answer="scripted answer"):
        rag.ai_generator = ScriptedGenerator(calls, answer)
        return rag.ai_generator

    yield install
    rag.ai_generator = real
    rag.tool_manager.reset_sources()


def test_query_passes_both_tools_to_model(rag, scripted):
    gen = scripted([])
    rag.query("hello")
    query, history, tools = gen.seen[0]
    assert "hello" in query and history is None
    assert {t["name"] for t in tools} == {"search_course_content", "get_course_outline"}


def test_query_returns_sources_from_search_then_resets(rag, scripted):
    scripted([("search_course_content",
               {"query": "introduction", "course_name": "Computer Use",
                "lesson_number": 0})])
    answer, sources = rag.query("what's in lesson 0?")
    assert answer == "scripted answer"
    assert sources and sources[0]["text"].endswith("Lesson 0")
    assert sources[0]["url"].startswith("http")
    assert rag.tool_manager.get_last_sources() == []  # reset after read


def test_query_without_tool_use_has_no_sources(rag, scripted):
    scripted([])
    assert rag.query("general question")[1] == []


def test_query_outline_source_is_course_link(rag, scripted):
    scripted([("get_course_outline", {"course_name": "MCP"})])
    _, sources = rag.query("outline of MCP course")
    assert len(sources) == 1 and sources[0]["url"].startswith("http")


def test_session_history_is_stored_and_injected(rag, scripted):
    sid = rag.session_manager.create_session()
    gen = scripted([], answer="first answer")
    rag.query("first question", sid)
    rag.query("second question", sid)
    history = gen.seen[1][1]
    assert "User: first question" in history  # raw question, not the wrapped prompt
    assert "Assistant: first answer" in history
    assert gen.seen[0][1] is None


def test_generator_error_propagates(rag):
    class Boom:
        def generate_response(self, **kw):
            raise RuntimeError("api down")

    real, rag.ai_generator = rag.ai_generator, Boom()
    try:
        with pytest.raises(RuntimeError, match="api down"):
            rag.query("x")
    finally:
        rag.ai_generator = real


def test_course_analytics(rag):
    a = rag.get_course_analytics()
    assert a["total_courses"] == len(a["course_titles"]) == 4


@pytest.mark.functional
def test_real_model_query_uses_search_and_returns_sources(rag, api_key):
    answer, sources = rag.query(
        "In the Computer Use course, what does lesson 0 introduce?"
    )
    assert answer.strip()
    assert sources and "Computer Use" in sources[0]["text"]


@pytest.mark.functional
def test_real_model_two_step_query(rag, api_key):
    answer, sources = rag.query(
        "Get the outline of the MCP course, then search the course content "
        "for what its first lesson covers."
    )
    assert answer.strip()
