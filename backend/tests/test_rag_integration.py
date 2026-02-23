"""Tests for RAG system query pipeline with mocked dependencies."""

import pytest
from unittest.mock import MagicMock, patch


class TestRAGQueryPipeline:
    """Test the full query pipeline with mocked external dependencies."""

    @pytest.fixture
    def mock_deps(self):
        """Set up mocked RAG system with all dependencies mocked."""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
            patch("rag_system.CourseSearchTool"),
            patch("rag_system.CourseOutlineTool"),
            patch("rag_system.ToolManager") as mock_tm_cls,
        ):
            from rag_system import RAGSystem
            from helpers import MockConfig

            config = MockConfig()
            rag = RAGSystem(config)

            # rag.tool_manager is now a MagicMock instance
            rag.ai_generator.generate_response.return_value = "This is the answer."
            rag.tool_manager.get_last_sources.return_value = ["Course A - Lesson 1"]
            rag.tool_manager.get_last_source_links.return_value = [
                "https://example.com/1"
            ]
            rag.session_manager.get_conversation_history.return_value = None

            yield rag

    def test_query_returns_response_and_sources(self, mock_deps):
        """Happy path: returns (answer, sources, source_links) tuple."""
        rag = mock_deps

        response, sources, source_links = rag.query("What is MCP?")

        assert response == "This is the answer."
        assert sources == ["Course A - Lesson 1"]
        assert source_links == ["https://example.com/1"]

    def test_query_passes_tools_to_generator(self, mock_deps):
        """get_tool_definitions() is passed to ai_generator.generate_response()."""
        rag = mock_deps
        rag.tool_manager.get_tool_definitions.return_value = [
            {"name": "search_course_content"}
        ]

        rag.query("test question")

        call_kwargs = rag.ai_generator.generate_response.call_args
        assert call_kwargs.kwargs["tools"] == [{"name": "search_course_content"}]

    def test_query_passes_tool_manager(self, mock_deps):
        """tool_manager instance is passed to generator for tool dispatch."""
        rag = mock_deps

        rag.query("test question")

        call_kwargs = rag.ai_generator.generate_response.call_args
        assert call_kwargs.kwargs["tool_manager"] is rag.tool_manager

    def test_query_collects_sources_after_response(self, mock_deps):
        """Sources retrieved via get_last_sources() after generation."""
        rag = mock_deps

        rag.query("test")

        gen_call_order = rag.ai_generator.generate_response.call_args_list
        src_call_order = rag.tool_manager.get_last_sources.call_args_list
        assert len(gen_call_order) == 1
        assert len(src_call_order) == 1

    def test_query_resets_sources(self, mock_deps):
        """reset_sources() called after source collection."""
        rag = mock_deps

        rag.query("test")

        rag.tool_manager.reset_sources.assert_called_once()

    def test_query_exception_propagates_to_caller(self, mock_deps):
        """When generator raises, exception propagates (no try/except in query())."""
        rag = mock_deps
        rag.ai_generator.generate_response.side_effect = Exception("API auth failed")

        with pytest.raises(Exception, match="API auth failed"):
            rag.query("test question")

    def test_query_with_session_passes_history(self, mock_deps):
        """Session history is passed as conversation_history parameter."""
        rag = mock_deps
        rag.session_manager.get_conversation_history.return_value = (
            "User: hi\nAssistant: hello"
        )

        rag.query("follow up question", session_id="session_1")

        call_kwargs = rag.ai_generator.generate_response.call_args
        assert (
            call_kwargs.kwargs["conversation_history"] == "User: hi\nAssistant: hello"
        )
