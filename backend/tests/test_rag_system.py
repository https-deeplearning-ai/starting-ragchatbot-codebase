"""Tests for RAGSystem content-query handling and search diagnostics."""

from unittest.mock import MagicMock, patch

import pytest

from config import config
from rag_system import RAGSystem
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults, VectorStore


@pytest.fixture
def rag_system_with_mocks():
    """RAGSystem with heavy dependencies mocked out."""
    with (
        patch("rag_system.DocumentProcessor"),
        patch("rag_system.VectorStore") as mock_vs_cls,
        patch("rag_system.AIGenerator") as mock_ai_cls,
        patch("rag_system.SessionManager") as mock_sm_cls,
    ):
        mock_vector_store = MagicMock()
        mock_vs_cls.return_value = mock_vector_store

        mock_ai = MagicMock()
        mock_ai_cls.return_value = mock_ai

        mock_session = MagicMock()
        mock_session.get_conversation_history.return_value = None
        mock_sm_cls.return_value = mock_session

        rag = RAGSystem(config)
        rag.ai_generator = mock_ai
        rag.session_manager = mock_session
        rag.vector_store = mock_vector_store
        # Re-bind search tool to the mocked store
        rag.search_tool = CourseSearchTool(mock_vector_store)
        rag.tool_manager = ToolManager()
        rag.tool_manager.register_tool(rag.search_tool)

        yield rag, mock_ai, mock_vector_store, mock_session


class TestRAGSystemContentQueries:
    def test_query_passes_search_tool_definitions_to_ai(self, rag_system_with_mocks):
        rag, mock_ai, _, _ = rag_system_with_mocks
        mock_ai.generate_response.return_value = "Answer about course content"

        rag.query("What is RAG in the Chroma course?")

        mock_ai.generate_response.assert_called_once()
        call_kwargs = mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["tool_manager"] is rag.tool_manager

        tool_names = [t["name"] for t in call_kwargs["tools"]]
        assert "search_course_content" in tool_names

    def test_query_returns_sources_from_tool_and_resets_them(
        self, rag_system_with_mocks
    ):
        rag, mock_ai, mock_store, _ = rag_system_with_mocks
        mock_store.search.return_value = SearchResults(
            documents=["Chunk about retrieval."],
            metadata=[{
                "course_title": "Advanced Retrieval for AI with Chroma",
                "lesson_number": 1,
            }],
            distances=[0.1],
        )
        mock_store.get_lesson_link.return_value = None

        def generate_side_effect(*, query, conversation_history, tools, tool_manager):
            # Simulate AI invoking the search tool during generation
            tool_manager.execute_tool(
                "search_course_content",
                query="What is RAG?",
                course_name="Chroma",
            )
            return "RAG retrieves relevant documents then generates answers."

        mock_ai.generate_response.side_effect = generate_side_effect

        answer, sources = rag.query("What is RAG?")

        assert "RAG retrieves" in answer
        assert sources == ["Advanced Retrieval for AI with Chroma - Lesson 1"]
        # Sources should be reset after retrieval
        assert rag.tool_manager.get_last_sources() == []

    def test_content_search_succeeds_with_config_max_results(self):
        """Diagnostic: CourseSearchTool + VectorStore must not error under config.MAX_RESULTS."""
        store = VectorStore.__new__(VectorStore)
        store.max_results = config.MAX_RESULTS
        store.course_content = MagicMock()
        store.get_lesson_link = MagicMock(return_value=None)

        if config.MAX_RESULTS <= 0:
            store.course_content.query.side_effect = Exception(
                f"Expected n_results to be a positive number, got {config.MAX_RESULTS}"
            )
        else:
            store.course_content.query.return_value = {
                "documents": [["Valid chunk about MCP servers"]],
                "metadatas": [[{"course_title": "MCP Course", "lesson_number": 2}]],
                "distances": [[0.05]],
            }

        tool = CourseSearchTool(store)
        # No course_name: avoid _resolve_course_name; exercise content query only
        result = tool.execute(query="What is an MCP server?")

        assert not result.startswith("Search error:"), (
            f"Content search failed due to MAX_RESULTS={config.MAX_RESULTS}: {result}"
        )
        assert "Valid chunk about MCP servers" in result
        assert "[MCP Course - Lesson 2]" in result

    def test_config_max_results_positive_for_rag_pipeline(self):
        assert config.MAX_RESULTS > 0, (
            "RAG content queries require MAX_RESULTS > 0; "
            f"current value is {config.MAX_RESULTS}"
        )

    def test_query_prompt_wraps_user_question(self, rag_system_with_mocks):
        rag, mock_ai, _, _ = rag_system_with_mocks
        mock_ai.generate_response.return_value = "ok"

        rag.query("How does prompt compression work?")

        call_kwargs = mock_ai.generate_response.call_args.kwargs
        assert "How does prompt compression work?" in call_kwargs["query"]
        assert "course materials" in call_kwargs["query"].lower()
