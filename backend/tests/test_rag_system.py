"""
Tests for RAGSystem.query()

All heavy dependencies (VectorStore, AIGenerator, SessionManager, etc.) are
patched at the constructor level so no real I/O occurs.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def rag_system():
    """Yield (RAGSystem, mock_ag, mock_tm, mock_sm) with all deps patched"""
    mock_ag = MagicMock()
    mock_ag.generate_response.return_value = "Test answer"

    mock_tm = MagicMock()
    mock_tm.get_tool_definitions.return_value = [{"name": "search_course_content"}]
    mock_tm.get_last_sources.return_value = []

    mock_sm = MagicMock()
    mock_sm.get_conversation_history.return_value = None

    with (
        patch("rag_system.DocumentProcessor"),
        patch("rag_system.VectorStore"),
        patch("rag_system.AIGenerator", return_value=mock_ag),
        patch("rag_system.SessionManager", return_value=mock_sm),
        patch("rag_system.ToolManager", return_value=mock_tm),
        patch("rag_system.CourseSearchTool"),
        patch("rag_system.CourseOutlineTool"),
    ):

        from rag_system import RAGSystem

        config = MagicMock()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "./test_chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-test"
        config.MAX_HISTORY = 2

        yield RAGSystem(config), mock_ag, mock_tm, mock_sm


# ── return type ───────────────────────────────────────────────────────────────


def test_query_returns_tuple_of_str_and_list(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    result = rag.query("What is Python?")
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], list)


def test_query_returns_ai_generator_response_as_answer(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    mock_ag.generate_response.return_value = "AI response text"
    answer, _ = rag.query("What is Python?")
    assert answer == "AI response text"


# ── tool forwarding (core bug check) ─────────────────────────────────────────


def test_query_passes_tool_definitions_to_generate_response(rag_system):
    """If tools are not forwarded, Claude never calls search — most likely root cause"""
    rag, mock_ag, mock_tm, mock_sm = rag_system
    tool_defs = [{"name": "search_course_content"}]
    mock_tm.get_tool_definitions.return_value = tool_defs

    rag.query("What is Python?")

    call_kwargs = mock_ag.generate_response.call_args[1]
    assert "tools" in call_kwargs, "tools not forwarded to generate_response"
    assert call_kwargs["tools"] == tool_defs


def test_query_passes_tool_manager_instance_to_generate_response(rag_system):
    """If tool_manager is not passed, execute_tool() is never called"""
    rag, mock_ag, mock_tm, mock_sm = rag_system
    rag.query("What is Python?")

    call_kwargs = mock_ag.generate_response.call_args[1]
    assert "tool_manager" in call_kwargs, "tool_manager not forwarded"
    assert call_kwargs["tool_manager"] is rag.tool_manager


# ── sources ───────────────────────────────────────────────────────────────────


def test_query_retrieves_sources_from_tool_manager(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    sources_data = [{"label": "Course - Lesson 1", "url": "http://example.com"}]
    mock_tm.get_last_sources.return_value = sources_data

    _, sources = rag.query("What is Python?")
    assert sources == sources_data


def test_query_calls_reset_sources_after_retrieval(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    rag.query("What is Python?")
    mock_tm.reset_sources.assert_called_once()


# ── session / history ─────────────────────────────────────────────────────────


def test_query_with_session_id_fetches_conversation_history(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    rag.query("What is Python?", session_id="session-123")
    mock_sm.get_conversation_history.assert_called_once_with("session-123")


def test_query_without_session_id_does_not_fetch_history(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    rag.query("What is Python?")
    mock_sm.get_conversation_history.assert_not_called()


def test_query_with_session_id_saves_exchange(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    mock_ag.generate_response.return_value = "My answer"
    rag.query("What is Python?", session_id="session-123")
    mock_sm.add_exchange.assert_called_once_with(
        "session-123", "What is Python?", "My answer"
    )


def test_query_passes_history_to_generate_response(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    mock_sm.get_conversation_history.return_value = "Past history"

    rag.query("What is Python?", session_id="session-123")

    call_kwargs = mock_ag.generate_response.call_args[1]
    assert call_kwargs.get("conversation_history") == "Past history"


# ── error propagation ─────────────────────────────────────────────────────────


def test_query_exception_in_generate_response_propagates(rag_system):
    rag, mock_ag, mock_tm, mock_sm = rag_system
    mock_ag.generate_response.side_effect = RuntimeError("AI failure")

    with pytest.raises(RuntimeError, match="AI failure"):
        rag.query("What is Python?")
