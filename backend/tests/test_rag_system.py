"""Tests for the RAG system query pipeline in rag_system.py.

These tests verify the tool-calling orchestration:
  query() resets sources → passes tools + executor to AIGenerator → collects sources → returns response.

All external dependencies (VectorStore, Ollama) are mocked to isolate the logic.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import httpx

from vector_store import SearchResults


# ---------------------------------------------------------------------------
# Helpers to build a RAGSystem with mocked internals
# ---------------------------------------------------------------------------

@pytest.fixture
def rag_system(mock_config, mock_vector_store):
    """Build a RAGSystem with mocked VectorStore and AIGenerator."""
    with patch("rag_system.VectorStore", return_value=mock_vector_store), \
         patch("rag_system.AIGenerator") as MockAI, \
         patch("rag_system.DocumentProcessor"):

        mock_ai = MockAI.return_value
        mock_ai.generate_response.return_value = "RAG is a technique that combines retrieval and generation."

        from rag_system import RAGSystem
        system = RAGSystem(mock_config)

        # Replace the vector store in the search tools with our mock
        system.search_tool.store = mock_vector_store
        system.outline_tool.store = mock_vector_store
        system.ai_generator = mock_ai

        yield system


@pytest.fixture
def rag_system_with_ollama_error(mock_config, mock_vector_store):
    """RAGSystem where the AI generator raises a connection error."""
    with patch("rag_system.VectorStore", return_value=mock_vector_store), \
         patch("rag_system.AIGenerator") as MockAI, \
         patch("rag_system.DocumentProcessor"):

        mock_ai = MockAI.return_value
        mock_ai.generate_response.side_effect = httpx.ConnectError("Connection refused")

        from rag_system import RAGSystem
        system = RAGSystem(mock_config)

        system.search_tool.store = mock_vector_store
        system.outline_tool.store = mock_vector_store
        system.ai_generator = mock_ai

        yield system


# ---------------------------------------------------------------------------
# Core query pipeline tests — tool-calling flow
# ---------------------------------------------------------------------------

class TestRAGQueryPipeline:
    """Test the main query() method orchestration."""

    def test_query_passes_tool_definitions(self, rag_system):
        """generate_response should receive tool definitions from the tool manager."""
        rag_system.query("What is RAG?")

        call_args = rag_system.ai_generator.generate_response.call_args
        tools = call_args.kwargs.get("tools")
        assert tools is not None
        assert isinstance(tools, list)
        assert len(tools) == 2  # search + outline tools

        # Verify tool names
        names = {t["function"]["name"] for t in tools}
        assert "search_course_content" in names
        assert "get_course_outline" in names

    def test_query_passes_tool_executor(self, rag_system):
        """generate_response should receive tool_executor bound to the tool manager."""
        rag_system.query("What is RAG?")

        call_args = rag_system.ai_generator.generate_response.call_args
        executor = call_args.kwargs.get("tool_executor")
        # Bound methods create new objects each access, so compare underlying function + instance
        assert executor.__func__ is rag_system.tool_manager.execute_tool.__func__
        assert executor.__self__ is rag_system.tool_manager

    def test_query_returns_response_and_sources(self, rag_system):
        """query() should return a (response_text, sources_list) tuple."""
        response, sources = rag_system.query("What is RAG?")

        assert response == "RAG is a technique that combines retrieval and generation."
        assert isinstance(sources, list)

    def test_query_collects_sources_after_response(self, rag_system):
        """Sources should be gathered from tools after the LLM finishes."""
        # Simulate the tool executor populating sources during generate_response
        def fake_generate(**kwargs):
            # Mimic what happens when the LLM calls the search tool
            rag_system.tool_manager.execute_tool("search_course_content", query="RAG")
            return "Here's what I found about RAG."

        rag_system.ai_generator.generate_response.side_effect = fake_generate

        response, sources = rag_system.query("What is RAG?")

        assert response == "Here's what I found about RAG."
        titles = [s["title"] for s in sources]
        assert any("Building RAG Chatbots" in t for t in titles)

    def test_query_resets_sources_before_each_query(self, rag_system):
        """reset_sources() should be called at the start of each query."""
        # Seed leftover sources from a "previous" query
        rag_system.search_tool.last_sources = [{"title": "stale", "link": None}]

        # The new query should reset before doing anything
        rag_system.query("What is RAG?")

        # After the query, the stale source should be gone.
        # Since generate_response is a plain mock (no tool calls), sources should be empty.
        _, sources = rag_system.query("Second question")
        assert all(s["title"] != "stale" for s in sources)


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestRAGQueryErrorHandling:
    """Tests that expose error handling issues in the RAG pipeline."""

    def test_ollama_connection_error_returns_friendly_message(self, rag_system_with_ollama_error):
        """Ollama being down returns a friendly error instead of crashing."""
        response, sources = rag_system_with_ollama_error.query("What is RAG?")

        assert "trouble generating a response" in response


# ---------------------------------------------------------------------------
# Session handling tests
# ---------------------------------------------------------------------------

class TestRAGSessionHandling:
    """Test conversation session integration."""

    def test_query_without_session(self, rag_system):
        """Query without session_id should still work (no history)."""
        response, sources = rag_system.query("What is RAG?")

        call_args = rag_system.ai_generator.generate_response.call_args
        history = call_args.kwargs.get("conversation_history")
        assert history is None

    def test_query_with_new_session(self, rag_system):
        """First query with a session_id should have no history."""
        response, sources = rag_system.query("What is RAG?", session_id="session_1")

        assert response is not None

    def test_query_with_existing_session(self, rag_system):
        """Second query in same session should include history from first query."""
        rag_system.query("What is RAG?", session_id="session_1")
        rag_system.query("Tell me more", session_id="session_1")

        # Second call should have conversation history
        calls = rag_system.ai_generator.generate_response.call_args_list
        second_call = calls[1]
        history = second_call.kwargs.get("conversation_history")
        assert history is not None
        assert "What is RAG?" in history
