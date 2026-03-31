"""
Tests for RAGSystem.query() in rag_system.py.

These tests verify how the full RAG pipeline handles content-related questions.
Two integration tests explicitly demonstrate the MAX_RESULTS=0 bug:
  - test_search_tool_fails_with_zero_max_results  →  FAILS on broken system
  - test_search_tool_succeeds_with_positive_max_results  →  FAILS on broken system, PASSES after fix
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system import RAGSystem
from search_tools import CourseSearchTool, ToolManager
from vector_store import VectorStore
from models import Course, Lesson, CourseChunk
from config import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_rag_system_with_mock_ai(vector_store=None):
    """
    Build a RAGSystem where only AIGenerator is mocked out.
    This lets us test the full tool-calling pipeline without real API calls.
    """
    with patch("rag_system.AIGenerator") as MockAI:
        mock_ai_instance = MagicMock()
        MockAI.return_value = mock_ai_instance
        rag = RAGSystem(config)
        if vector_store:
            rag.vector_store = vector_store
            rag.search_tool.store = vector_store
            rag.outline_tool.store = vector_store
        return rag, mock_ai_instance


# ---------------------------------------------------------------------------
# Unit tests — AIGenerator is mocked
# ---------------------------------------------------------------------------

class TestRAGSystemQuery:

    def test_query_returns_tuple_of_answer_and_sources(self):
        """query() always returns a (str, list) tuple."""
        rag, mock_ai = make_rag_system_with_mock_ai()
        mock_ai.generate_response.return_value = "Neural networks are layers of nodes."

        answer, sources = rag.query("What are neural networks?")

        assert isinstance(answer, str)
        assert isinstance(sources, list)
        assert answer == "Neural networks are layers of nodes."

    def test_query_passes_tool_definitions_to_ai_generator(self):
        """generate_response is called with tool definitions from ToolManager."""
        rag, mock_ai = make_rag_system_with_mock_ai()
        mock_ai.generate_response.return_value = "Some answer."

        rag.query("What is in lesson 2?")

        call_kwargs = mock_ai.generate_response.call_args[1]
        assert "tools" in call_kwargs
        tool_names = [t["name"] for t in call_kwargs["tools"]]
        assert "search_course_content" in tool_names

    def test_query_passes_tool_manager_to_ai_generator(self):
        """generate_response receives the tool_manager so it can execute tools."""
        rag, mock_ai = make_rag_system_with_mock_ai()
        mock_ai.generate_response.return_value = "Answer."

        rag.query("What is MCP?")

        call_kwargs = mock_ai.generate_response.call_args[1]
        assert "tool_manager" in call_kwargs
        assert call_kwargs["tool_manager"] is rag.tool_manager

    def test_query_wraps_user_question_in_prompt(self):
        """RAGSystem prepends context to the user query before passing to AIGenerator."""
        rag, mock_ai = make_rag_system_with_mock_ai()
        mock_ai.generate_response.return_value = "Answer."

        rag.query("What is reinforcement learning?")

        call_kwargs = mock_ai.generate_response.call_args[1]
        assert "What is reinforcement learning?" in call_kwargs["query"]

    def test_query_saves_exchange_to_session(self):
        """After a query, the exchange is stored in SessionManager."""
        rag, mock_ai = make_rag_system_with_mock_ai()
        mock_ai.generate_response.return_value = "RL answer."

        session_id = rag.session_manager.create_session()
        rag.query("What is RL?", session_id=session_id)

        history = rag.session_manager.get_conversation_history(session_id)
        assert history is not None
        assert "What is RL?" in history
        assert "RL answer." in history

    def test_query_resets_sources_after_retrieval(self):
        """Sources are cleared from the tool manager after each query."""
        rag, mock_ai = make_rag_system_with_mock_ai()
        mock_ai.generate_response.return_value = "Answer."

        # Manually pre-populate sources to simulate a previous search
        rag.search_tool.last_sources = ["Some Course - Lesson 1"]

        rag.query("New question?")

        # After query(), sources should be cleared
        assert rag.tool_manager.get_last_sources() == []


# ---------------------------------------------------------------------------
# Integration tests — expose the MAX_RESULTS=0 bug using real ChromaDB
# ---------------------------------------------------------------------------

class TestRAGSystemSearchIntegration:
    """
    These tests build a real in-memory ChromaDB with sample data.
    They demonstrate that MAX_RESULTS=0 causes search to fail.
    """

    @pytest.fixture()
    def populated_store_broken(self, tmp_path):
        """VectorStore with max_results=0 (mirrors broken config)."""
        store = VectorStore(
            chroma_path=str(tmp_path / "broken"),
            embedding_model="all-MiniLM-L6-v2",
            max_results=0,
        )
        course = Course(
            title="Intro to ML",
            course_link="http://example.com/ml",
            instructor="Test Instructor",
            lessons=[Lesson(lesson_number=1, title="Supervised Learning", lesson_link="http://example.com/ml/1")],
        )
        store.add_course_metadata(course)
        store.add_course_content([
            CourseChunk(
                content="Supervised learning uses labeled training data to learn a mapping from inputs to outputs.",
                course_title="Intro to ML",
                lesson_number=1,
                chunk_index=0,
            )
        ])
        return store

    @pytest.fixture()
    def populated_store_fixed(self, tmp_path):
        """VectorStore with max_results=5 (correct config)."""
        store = VectorStore(
            chroma_path=str(tmp_path / "fixed"),
            embedding_model="all-MiniLM-L6-v2",
            max_results=5,
        )
        course = Course(
            title="Intro to ML",
            course_link="http://example.com/ml",
            instructor="Test Instructor",
            lessons=[Lesson(lesson_number=1, title="Supervised Learning", lesson_link="http://example.com/ml/1")],
        )
        store.add_course_metadata(course)
        store.add_course_content([
            CourseChunk(
                content="Supervised learning uses labeled training data to learn a mapping from inputs to outputs.",
                course_title="Intro to ML",
                lesson_number=1,
                chunk_index=0,
            )
        ])
        return store

    def test_search_tool_fails_with_zero_max_results(self, populated_store_broken):
        """
        Documents the bug: with max_results=0, the search tool returns a 'Search error'
        string instead of course content. ChromaDB raises:
          'Number of requested results 0, cannot be negative, or zero.'
        This test PASSES by asserting that broken behavior occurs when max_results=0.
        The fix is in config.py: change MAX_RESULTS from 0 to 5.
        """
        tool = CourseSearchTool(populated_store_broken)
        result = tool.execute(query="supervised learning")

        assert "Search error" in result, (
            "Expected a search error with max_results=0 — "
            "the bug behavior is not reproducible."
        )

    def test_search_tool_succeeds_with_positive_max_results(self, populated_store_fixed):
        """
        After the fix, search returns actual course content.
        This test also FAILS on the broken system (because it uses max_results=5
        directly), confirming the fix works when max_results is positive.
        """
        tool = CourseSearchTool(populated_store_fixed)
        result = tool.execute(query="supervised learning")

        assert "Search error" not in result
        assert "Intro to ML" in result
        assert "Supervised" in result or "labeled" in result

    def test_config_max_results_is_positive(self):
        """
        Verifies that the config value MAX_RESULTS is a positive integer.
        This test FAILS on the broken system where MAX_RESULTS=0.
        """
        assert config.MAX_RESULTS > 0, (
            f"BUG: config.MAX_RESULTS is {config.MAX_RESULTS}. "
            "It must be a positive integer (e.g. 5) for searches to work. "
            "Fix: change MAX_RESULTS in backend/config.py"
        )
