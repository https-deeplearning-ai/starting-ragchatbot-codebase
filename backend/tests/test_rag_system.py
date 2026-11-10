"""3. How RAGSystem handles content questions, end to end (Claude and ChromaDB mocked)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from conftest import MCP, make_results, response, text_block, tool_use_block

import rag_system


@pytest.fixture
def rag(mock_store):
    cfg = SimpleNamespace(
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=100,
        CHROMA_PATH="unused",
        EMBEDDING_MODEL="unused",
        MAX_RESULTS=5,
        ANTHROPIC_API_KEY="test-key",
        ANTHROPIC_MODEL="test-model",
        MAX_HISTORY=2,
    )
    with patch.object(rag_system, "VectorStore", return_value=mock_store):
        system = rag_system.RAGSystem(cfg)
    system.ai_generator.client = MagicMock()
    return system


def claude_searches(rag, tool_input, answer):
    rag.ai_generator.client.messages.create.side_effect = [
        response(
            tool_use_block("search_course_content", tool_input), stop_reason="tool_use"
        ),
        response(text_block(answer)),
    ]


def test_both_tools_are_offered(rag):
    names = {d["name"] for d in rag.tool_manager.get_tool_definitions()}
    assert names == {"search_course_content", "get_course_outline"}


def test_content_query_returns_answer_and_sources(rag, mock_store):
    mock_store.search.return_value = make_results([("MCP is a protocol.", MCP, 1, 3)])
    claude_searches(
        rag, {"query": "what is MCP", "course_name": "MCP"}, "MCP is a protocol."
    )

    answer, sources = rag.query("What is MCP?")

    assert answer == "MCP is a protocol."
    assert sources == [
        {"label": f"{MCP} - Lesson 1", "url": "https://example.com/mcp/lesson1"}
    ]
    mock_store.search.assert_called_once_with(
        query="what is MCP", course_name="MCP", lesson_number=None
    )


def test_lesson_detail_query_succeeds(rag, mock_store):
    """The 'Details of a course's lesson' suggested question."""
    mock_store.search.return_value = make_results(
        [
            ("Building the client.", MCP, 5, 51),
            ("Intro to the client.", MCP, 5, 50),
        ]
    )
    claude_searches(
        rag,
        {"query": "lesson 5 content", "course_name": "MCP", "lesson_number": 5},
        "Lesson 5 builds an MCP client.",
    )

    answer, sources = rag.query("What was covered in lesson 5 of the MCP course?")

    assert answer == "Lesson 5 builds an MCP client."
    assert sources == [
        {"label": f"{MCP} - Lesson 5", "url": "https://example.com/mcp/lesson5"}
    ]


def test_no_results_still_answers_with_no_sources(rag, mock_store):
    mock_store.search.return_value = make_results([])
    claude_searches(rag, {"query": "quantum", "course_name": "MCP"}, "Not covered.")

    answer, sources = rag.query("Does MCP cover quantum?")

    assert answer == "Not covered."
    assert sources == []


def test_general_question_does_not_search(rag, mock_store):
    rag.ai_generator.client.messages.create.return_value = response(text_block("4"))

    answer, sources = rag.query("What is 2+2?")

    assert (answer, sources) == ("4", [])
    mock_store.search.assert_not_called()


def test_sources_do_not_leak_into_next_query(rag, mock_store):
    mock_store.search.return_value = make_results([("x", MCP, 1, 0)])
    claude_searches(rag, {"query": "x"}, "first")
    rag.query("first")

    rag.ai_generator.client.messages.create.side_effect = None
    rag.ai_generator.client.messages.create.return_value = response(
        text_block("second")
    )
    _, sources = rag.query("second")

    assert sources == []


def test_session_history_is_recorded_and_sent(rag, mock_store):
    mock_store.search.return_value = make_results([("x", MCP, 1, 0)])
    claude_searches(rag, {"query": "x"}, "First answer")
    sid = rag.session_manager.create_session()
    rag.query("First question", session_id=sid)

    rag.ai_generator.client.messages.create.side_effect = None
    rag.ai_generator.client.messages.create.return_value = response(text_block("ok"))
    rag.query("Follow-up", session_id=sid)

    system = rag.ai_generator.client.messages.create.call_args.kwargs["system"]
    assert "First question" in system and "First answer" in system
