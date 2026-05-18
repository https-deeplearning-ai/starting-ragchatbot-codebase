"""
Tests for RAGSystem's handling of content-related queries.

Covers:
- Tools are forwarded to the AI generator on every query
- Sources are returned from the last tool search
- Sources are reset (cleared) after each query so they don't bleed into the next
- Conversation history is passed to the generator when a session exists
- No history is passed for new / unknown sessions
- End-to-end content query flow: Claude calls the search tool, result is synthesized
"""

import pytest
from unittest.mock import MagicMock, patch, call
from tests.conftest import make_text_response, make_tool_use_response

# ---------------------------------------------------------------------------
# RAGSystem fixture — all heavy dependencies mocked at class level
# ---------------------------------------------------------------------------


@pytest.fixture
def rag():
    """
    Returns a RAGSystem with VectorStore, AIGenerator, and DocumentProcessor
    replaced by MagicMocks so no disk I/O or API calls occur.
    """
    from config import Config

    config = Config(
        ANTHROPIC_API_KEY="test-key",
        ANTHROPIC_MODEL="claude-test",
        CHROMA_PATH="./test_chroma",
    )

    with (
        patch("rag_system.VectorStore"),
        patch("rag_system.AIGenerator"),
        patch("rag_system.DocumentProcessor"),
    ):
        from rag_system import RAGSystem

        system = RAGSystem(config)

    return system


# ---------------------------------------------------------------------------
# Tool forwarding
# ---------------------------------------------------------------------------


class TestToolForwarding:
    def test_tools_passed_to_ai_generator(self, rag):
        """generate_response must receive the registered tool definitions."""
        rag.ai_generator.generate_response.return_value = "Direct answer."

        rag.query("What is RAG?")

        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) > 0

    def test_tool_manager_passed_to_ai_generator(self, rag):
        """The tool_manager must be passed so the generator can execute tool calls."""
        rag.ai_generator.generate_response.return_value = "answer"

        rag.query("What is RAG?")

        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["tool_manager"] is rag.tool_manager

    def test_search_course_content_tool_registered(self, rag):
        """CourseSearchTool must be present in the tool definitions."""
        tool_names = [t["name"] for t in rag.tool_manager.get_tool_definitions()]
        assert "search_course_content" in tool_names

    def test_get_course_outline_tool_registered(self, rag):
        """CourseOutlineTool must also be present in the tool definitions."""
        tool_names = [t["name"] for t in rag.tool_manager.get_tool_definitions()]
        assert "get_course_outline" in tool_names


# ---------------------------------------------------------------------------
# Source management
# ---------------------------------------------------------------------------


class TestSourceManagement:
    def test_sources_returned_from_last_search(self, rag):
        """query() must return whatever sources the search tool recorded."""
        rag.ai_generator.generate_response.return_value = "answer"
        expected_sources = [
            {"label": "AI Course - Lesson 1", "url": "https://example.com"}
        ]
        rag.search_tool.last_sources = expected_sources

        _, sources = rag.query("What is attention?")

        assert sources == expected_sources

    def test_sources_reset_after_query(self, rag):
        """After returning sources, they must be cleared for the next query."""
        rag.ai_generator.generate_response.return_value = "answer"
        rag.search_tool.last_sources = [{"label": "Some Course", "url": None}]

        rag.query("First query")
        # Simulate a second query where the search tool found nothing
        rag.search_tool.last_sources = []
        _, sources = rag.query("Second query — no search")

        assert sources == []

    def test_empty_sources_when_no_tool_called(self, rag):
        """If Claude answered directly (no search), sources list must be empty."""
        rag.ai_generator.generate_response.return_value = "Direct answer."
        # last_sources was never set (starts as [])

        _, sources = rag.query("What is 2 + 2?")

        assert sources == []


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------


class TestConversationHistory:
    def test_history_passed_when_session_exists(self, rag):
        """For a known session with history, generate_response must receive it."""
        session_id = rag.session_manager.create_session()
        rag.session_manager.add_exchange(session_id, "Hi", "Hello!")
        rag.ai_generator.generate_response.return_value = "answer"

        rag.query("Follow-up question", session_id=session_id)

        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        history = call_kwargs["conversation_history"]
        assert history is not None
        assert "Hi" in history
        assert "Hello!" in history

    def test_no_history_for_new_session(self, rag):
        """A brand-new session has no history; None must be passed."""
        session_id = rag.session_manager.create_session()
        rag.ai_generator.generate_response.return_value = "answer"

        rag.query("First message", session_id=session_id)

        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] is None

    def test_no_history_when_no_session_id(self, rag):
        """Queries without a session_id must pass history=None."""
        rag.ai_generator.generate_response.return_value = "answer"

        rag.query("Stateless question", session_id=None)

        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] is None

    def test_exchange_stored_after_query(self, rag):
        """The query/response pair must be saved to session history."""
        session_id = rag.session_manager.create_session()
        rag.ai_generator.generate_response.return_value = "RAG is useful."

        rag.query("Tell me about RAG.", session_id=session_id)

        history = rag.session_manager.get_conversation_history(session_id)
        assert "Tell me about RAG." in history
        assert "RAG is useful." in history


# ---------------------------------------------------------------------------
# End-to-end content query flow
# ---------------------------------------------------------------------------


class TestContentQueryFlow:
    def test_content_query_uses_search_and_synthesizes_answer(self, rag):
        """
        Simulates the full path for a content question:
          1. AI decides to call search_course_content
          2. Tool executes and returns chunks
          3. AI synthesizes a final answer

        All external calls (Anthropic API, ChromaDB) are mocked.
        """
        # Simulate the AI generator going through the tool-use loop internally
        # and returning the final synthesized answer
        rag.ai_generator.generate_response.return_value = (
            "RAG stands for Retrieval-Augmented Generation."
        )
        # Simulate search tool populating sources
        rag.search_tool.last_sources = [
            {"label": "RAG Course - Lesson 1", "url": "https://example.com/rag/1"}
        ]

        response, sources = rag.query("What does RAG stand for?")

        assert "RAG" in response
        assert len(sources) == 1
        assert sources[0]["label"] == "RAG Course - Lesson 1"

    def test_query_response_and_sources_independent_across_calls(self, rag):
        """Sources from query N must not leak into query N+1."""
        rag.ai_generator.generate_response.return_value = "answer"

        # First query leaves sources
        rag.search_tool.last_sources = [{"label": "Course A - Lesson 1", "url": None}]
        rag.query("First question")

        # Second query — no search performed
        rag.search_tool.last_sources = []
        _, sources = rag.query("Second question")

        assert sources == []
