"""
Tests for RAGSystem.query() in rag_system.py.

The Anthropic client is always mocked so these tests run without a real API key.
ChromaDB uses the temporary fixture from conftest.py.
"""

from unittest.mock import MagicMock, patch
import pytest

from models import Course, Lesson, CourseChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text_response(text="Answer"):
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    resp.content = [text_block]
    return resp


def _make_tool_use_response(query="test query", tool_id="tid_1"):
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = tool_id
    tool_block.name = "search_course_content"
    tool_block.input = {"query": query}

    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = [tool_block]
    return resp


def _build_rag_system(tmp_chroma_path, mock_anthropic_client):
    """Build a RAGSystem wired with a temp ChromaDB and a mocked Anthropic client."""
    from dataclasses import dataclass

    @dataclass
    class TestConfig:
        ANTHROPIC_API_KEY: str = "fake-key"
        ANTHROPIC_MODEL: str = "fake-model"
        EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
        CHUNK_SIZE: int = 500
        CHUNK_OVERLAP: int = 100
        MAX_RESULTS: int = 5
        MAX_HISTORY: int = 2
        CHROMA_PATH: str = tmp_chroma_path

    from rag_system import RAGSystem
    rag = RAGSystem(TestConfig())
    rag.ai_generator.client = mock_anthropic_client
    return rag


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRAGSystemQuery:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_chroma_path):
        self.mock_client = MagicMock()
        self.rag = _build_rag_system(tmp_chroma_path, self.mock_client)

    # --- basic contract ---

    def test_query_returns_tuple_of_answer_and_sources(self):
        self.mock_client.messages.create.return_value = _make_text_response("Hello")

        answer, sources = self.rag.query("What is 2+2?")

        assert isinstance(answer, str)
        assert isinstance(sources, list)

    def test_query_returns_non_empty_answer(self):
        self.mock_client.messages.create.return_value = _make_text_response("42")

        answer, _ = self.rag.query("What is 2+2?")

        assert answer == "42"

    def test_query_returns_empty_sources_when_no_tool_used(self):
        self.mock_client.messages.create.return_value = _make_text_response("General answer")

        _, sources = self.rag.query("What is Python?")

        assert sources == []

    # --- session / history ---

    def test_query_creates_session_when_none_provided(self):
        self.mock_client.messages.create.return_value = _make_text_response("ok")

        answer, sources = self.rag.query("test", session_id=None)

        assert answer == "ok"

    def test_query_updates_conversation_history_with_session(self):
        self.mock_client.messages.create.return_value = _make_text_response("first")

        session = self.rag.session_manager.create_session()
        self.rag.query("first question", session_id=session)

        history = self.rag.session_manager.get_conversation_history(session)
        assert history is not None
        assert "first question" in history

    # --- tool use flow ---

    def test_query_with_content_question_triggers_tool_search(self, sample_course, sample_chunks):
        # Load course data so the search tool has something to return
        self.rag.vector_store.add_course_metadata(sample_course)
        self.rag.vector_store.add_course_content(sample_chunks)

        tool_resp = _make_tool_use_response(query="retrieval augmented generation")
        final_resp = _make_text_response("RAG is retrieval augmented generation.")
        self.mock_client.messages.create.side_effect = [tool_resp, final_resp]

        answer, sources = self.rag.query("What is RAG?")

        # Two API calls should have happened: initial + follow-up
        assert self.mock_client.messages.create.call_count == 2
        assert answer == "RAG is retrieval augmented generation."

    def test_query_tool_sources_returned_after_search(self, sample_course, sample_chunks):
        self.rag.vector_store.add_course_metadata(sample_course)
        self.rag.vector_store.add_course_content(sample_chunks)

        tool_resp = _make_tool_use_response(query="RAG retrieval")
        final_resp = _make_text_response("Answer about RAG")
        self.mock_client.messages.create.side_effect = [tool_resp, final_resp]

        _, sources = self.rag.query("Explain RAG")

        assert len(sources) > 0
        assert any("Introduction to RAG" in s for s in sources)

    def test_query_sources_reset_between_calls(self, sample_course, sample_chunks):
        self.rag.vector_store.add_course_metadata(sample_course)
        self.rag.vector_store.add_course_content(sample_chunks)

        # First call uses tool
        tool_resp = _make_tool_use_response(query="RAG")
        final_resp = _make_text_response("answer1")
        self.mock_client.messages.create.side_effect = [tool_resp, final_resp]
        self.rag.query("Content question 1")

        # Second call is a general question (no tool)
        self.mock_client.messages.create.side_effect = None
        self.mock_client.messages.create.return_value = _make_text_response("answer2")
        _, sources2 = self.rag.query("What is Python?")

        assert sources2 == [], (
            "Sources from a previous tool-using query leaked into a subsequent "
            "non-tool query. reset_sources() must be called before each query or "
            "sources must be gathered after the current query only."
        )

    # --- final API call includes tools (mirrors ai_generator test) ---

    def test_final_api_call_in_tool_flow_includes_tools(self, sample_course, sample_chunks):
        """
        Verify that when RAGSystem drives the tool-use flow, the second Anthropic
        API call (the follow-up after tool execution) includes the 'tools' parameter.
        Without it the Anthropic API returns HTTP 400 → 'query failed'.
        """
        self.rag.vector_store.add_course_metadata(sample_course)
        self.rag.vector_store.add_course_content(sample_chunks)

        tool_resp = _make_tool_use_response(query="RAG")
        final_resp = _make_text_response("final")
        self.mock_client.messages.create.side_effect = [tool_resp, final_resp]

        self.rag.query("What is RAG?")

        assert self.mock_client.messages.create.call_count == 2, (
            "Expected exactly two API calls (initial + follow-up after tool execution)."
        )
        second_call_kwargs = self.mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs, (
            "The follow-up API call (after tool execution) is missing 'tools'. "
            "Anthropic API requires 'tools' whenever messages contain tool_use blocks. "
            "This is the root cause of the 'query failed' error."
        )
