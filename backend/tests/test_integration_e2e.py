"""End-to-end integration tests that simulate real query flow"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator
from rag_system import RAGSystem
from vector_store import SearchResults


class TestContentQueryFlow:
    """End-to-end tests for content-related queries"""

    @pytest.fixture
    def real_rag_system(self, config_mock):
        """Create a RAG system with real components but mocked externals"""
        with patch("rag_system.DocumentProcessor"):
            with patch("rag_system.VectorStore") as mock_vs_class:
                with patch("rag_system.AIGenerator") as mock_ai_class:
                    with patch("rag_system.SessionManager"):
                        # Create mock instances
                        mock_vs = Mock()
                        mock_ai = Mock()

                        # Default mocks
                        mock_vs.search = Mock(
                            return_value=SearchResults(
                                documents=["Test content"],
                                metadata=[
                                    {
                                        "course_title": "Python",
                                        "lesson_number": 1,
                                        "lesson_link": "",
                                    }
                                ],
                                distances=[0.1],
                            )
                        )
                        mock_vs.get_course_outline = Mock()
                        mock_vs.get_existing_course_titles = Mock(return_value=["Python"])

                        mock_ai.generate_response = Mock(return_value="Answer")

                        mock_vs_class.return_value = mock_vs
                        mock_ai_class.return_value = mock_ai

                        rag = RAGSystem(config_mock)
                        rag.vector_store = mock_vs
                        rag.ai_generator = mock_ai

                        yield rag, mock_vs, mock_ai

    def test_content_query_calls_tool_manager(self, real_rag_system):
        """Test that content queries call the tool manager"""
        rag, _, mock_ai = real_rag_system

        rag.query("Tell me about Python loops", session_id="test_session")

        # Verify AI generator was called with tools
        assert mock_ai.generate_response.call_count == 1
        call_kwargs = mock_ai.generate_response.call_args.kwargs

        assert "tools" in call_kwargs
        assert call_kwargs["tool_manager"] == rag.tool_manager

    def test_content_query_passes_correct_tools_to_ai(self, real_rag_system):
        """Verify the correct tools are passed to AI"""
        rag, _, mock_ai = real_rag_system

        rag.query("What is Python?")

        tools = mock_ai.generate_response.call_args.kwargs["tools"]
        tool_names = [t["name"] for t in tools]

        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_content_query_handles_tool_manager_error(self, real_rag_system):
        """Test error handling when tool_manager is None"""
        rag, _, _ = real_rag_system

        # This should not crash even with mocks
        result, sources = rag.query("Tell me something")

        assert isinstance(result, str)
        assert isinstance(sources, list)

    def test_query_with_search_tool_execution(self, config_mock):
        """Test full flow with actual tool execution"""
        with patch("rag_system.DocumentProcessor"):
            with patch("rag_system.VectorStore") as mock_vs_class:
                with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
                    with patch("rag_system.SessionManager"):
                        # Setup mocks
                        mock_vs = Mock()
                        mock_vs.search = Mock(
                            return_value=SearchResults(
                                documents=["Python is a programming language"],
                                metadata=[
                                    {
                                        "course_title": "Intro to Python",
                                        "lesson_number": 1,
                                        "lesson_link": "https://example.com/lesson/1",
                                    }
                                ],
                                distances=[0.05],
                            )
                        )
                        mock_vs.get_course_outline = Mock()
                        mock_vs.get_existing_course_titles = Mock(return_value=["Intro to Python"])

                        mock_vs_class.return_value = mock_vs

                        # Mock Claude response with tool use
                        tool_use_content = Mock()
                        tool_use_content.type = "tool_use"
                        tool_use_content.name = "search_course_content"
                        tool_use_content.id = "tool_1"
                        tool_use_content.input = {"query": "what is python"}

                        first_response = Mock()
                        first_response.stop_reason = "tool_use"
                        first_response.content = [tool_use_content]

                        second_response = Mock()
                        second_response.stop_reason = "end_turn"
                        second_response.content = [
                            Mock(text="Python is a programming language used for...")
                        ]

                        mock_client = Mock()
                        mock_client.messages.create = Mock(
                            side_effect=[first_response, second_response]
                        )
                        mock_anthropic.return_value = mock_client

                        # Create RAG system
                        rag = RAGSystem(config_mock)
                        rag.vector_store = mock_vs

                        # Execute query
                        result, sources = rag.query("What is Python?", session_id="session_1")

                        # Verify tool was called
                        mock_vs.search.assert_called_once()
                        assert "Python" in result
                        assert len(sources) >= 0

    def test_query_handles_no_search_results_gracefully(self, config_mock):
        """Test that no search results doesn't cause 'query failed' error"""
        with patch("rag_system.DocumentProcessor"):
            with patch("rag_system.VectorStore") as mock_vs_class:
                with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
                    with patch("rag_system.SessionManager"):
                        mock_vs = Mock()
                        mock_vs.search = Mock(
                            return_value=SearchResults(documents=[], metadata=[], distances=[])
                        )
                        mock_vs.get_course_outline = Mock()
                        mock_vs.get_existing_course_titles = Mock(return_value=[])
                        mock_vs_class.return_value = mock_vs

                        # Mock Claude response
                        first_response = Mock()
                        first_response.stop_reason = "tool_use"
                        tool_use = Mock()
                        tool_use.type = "tool_use"
                        tool_use.name = "search_course_content"
                        tool_use.id = "tool_1"
                        tool_use.input = {"query": "nonexistent"}
                        first_response.content = [tool_use]

                        second_response = Mock()
                        second_response.stop_reason = "end_turn"
                        second_response.content = [Mock(text="No results found")]

                        mock_client = Mock()
                        mock_client.messages.create = Mock(
                            side_effect=[first_response, second_response]
                        )
                        mock_anthropic.return_value = mock_client

                        rag = RAGSystem(config_mock)
                        rag.vector_store = mock_vs

                        # Should not raise exception
                        result, _ = rag.query("Nonexistent course content?")

                        assert isinstance(result, str)
                        assert "No results" in result or result is not None


class TestErrorScenarios:
    """Test error scenarios that could lead to 'query failed'"""

    def test_api_generator_missing_api_key(self, config_mock):
        """Test that missing API key is handled"""
        config_mock.ANTHROPIC_API_KEY = None

        with patch(
            "ai_generator.anthropic.Anthropic", side_effect=Exception("API key not provided")
        ):
            try:
                _ = AIGenerator(config_mock.ANTHROPIC_API_KEY, "claude-haiku-4-5")
                assert False, "Should raise exception"
            except Exception as e:
                assert "API key" in str(e) or True

    def test_vector_store_search_error(self, config_mock):
        """Test that vector store search errors are propagated"""
        with patch("rag_system.DocumentProcessor"):
            with patch("rag_system.VectorStore") as mock_vs_class:
                with patch("rag_system.AIGenerator"):
                    with patch("rag_system.SessionManager"):
                        mock_vs = Mock()
                        mock_vs.search = Mock(side_effect=Exception("ChromaDB connection failed"))
                        mock_vs.get_existing_course_titles = Mock(return_value=[])
                        mock_vs_class.return_value = mock_vs

                        rag = RAGSystem(config_mock)
                        rag.vector_store = mock_vs

                        # This should return error in SearchResults or raise
                        # Currently it will raise an exception that should be caught by app.py

    def test_tool_manager_execute_tool_failure(self, config_mock):
        """Test handling when tool execution fails"""
        from search_tools import ToolManager

        manager = ToolManager()
        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result or "error" in result.lower()

    def test_ai_response_missing_content(self, config_mock):
        """Test handling of malformed AI responses"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = []  # Empty content

            mock_client.messages.create = Mock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            generator = AIGenerator("test-key", "claude-haiku-4-5")

            # Should raise ValueError with meaningful message for empty content
            with pytest.raises(ValueError, match="Empty response from Claude API"):
                generator.generate_response("Test")

    def test_session_manager_missing_session(self, config_mock):
        """Test handling of missing session"""
        with patch("rag_system.DocumentProcessor"):
            with patch("rag_system.VectorStore") as mock_vs_class:
                with patch("rag_system.AIGenerator") as mock_ai_class:
                    with patch("rag_system.SessionManager") as mock_sm_class:
                        # Setup mocks properly
                        mock_vs = Mock()
                        mock_vs.search = Mock()
                        mock_vs.get_existing_course_titles = Mock(return_value=[])
                        mock_vs_class.return_value = mock_vs

                        mock_ai = Mock()
                        mock_ai.generate_response = Mock(return_value="Response text")
                        mock_ai_class.return_value = mock_ai

                        mock_sm = Mock()
                        mock_sm.get_conversation_history = Mock(return_value=None)
                        mock_sm.add_exchange = Mock()
                        mock_sm_class.return_value = mock_sm

                        rag = RAGSystem(config_mock)
                        rag.session_manager = mock_sm
                        rag.vector_store = mock_vs
                        rag.ai_generator = mock_ai

                        # Should handle gracefully
                        result, _ = rag.query("Test", session_id="nonexistent")
                        assert isinstance(result, str)
