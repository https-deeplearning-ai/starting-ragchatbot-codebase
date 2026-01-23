"""Tests for RAGSystem - main orchestrator"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestRAGSystemQuery:
    """Test RAGSystem.query() method"""

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_returns_response_and_sources(
        self, mock_session, mock_doc_proc, mock_vector, mock_ai
    ):
        """Test successful query returns response and sources"""
        from rag_system import RAGSystem

        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "Test answer"
        mock_ai.return_value = mock_ai_instance

        mock_vector_instance = Mock()
        mock_vector.return_value = mock_vector_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance

        # Create config with proper MAX_RESULTS
        config = Mock()
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "test-model"
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "/tmp/test"
        config.EMBEDDING_MODEL = "test-embed"
        config.MAX_HISTORY = 2

        rag = RAGSystem(config)

        # Mock the tool manager
        rag.tool_manager.get_last_sources = Mock(
            return_value=[{"text": "Course - Lesson 1", "link": "https://example.com"}]
        )
        rag.tool_manager.reset_sources = Mock()

        response, sources = rag.query("What is ML?")

        assert response == "Test answer"
        assert len(sources) == 1
        mock_ai_instance.generate_response.assert_called_once()

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_with_session_uses_history(
        self, mock_session, mock_doc_proc, mock_vector, mock_ai
    ):
        """Test that session history is passed to AI generator"""
        from rag_system import RAGSystem

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "Answer"
        mock_ai.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = "Previous chat"
        mock_session.return_value = mock_session_instance

        config = Mock()
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "test-model"
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "/tmp/test"
        config.EMBEDDING_MODEL = "test-embed"
        config.MAX_HISTORY = 2

        rag = RAGSystem(config)
        rag.tool_manager.get_last_sources = Mock(return_value=[])
        rag.tool_manager.reset_sources = Mock()

        rag.query("Follow up", session_id="session_1")

        call_args = mock_ai_instance.generate_response.call_args
        assert call_args.kwargs["conversation_history"] == "Previous chat"

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_updates_session_history(
        self, mock_session, mock_doc_proc, mock_vector, mock_ai
    ):
        """Test that session history is updated after query"""
        from rag_system import RAGSystem

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "The answer"
        mock_ai.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance

        config = Mock()
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "test-model"
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "/tmp/test"
        config.EMBEDDING_MODEL = "test-embed"
        config.MAX_HISTORY = 2

        rag = RAGSystem(config)
        rag.tool_manager.get_last_sources = Mock(return_value=[])
        rag.tool_manager.reset_sources = Mock()

        rag.query("Test question", session_id="session_1")

        mock_session_instance.add_exchange.assert_called_once_with(
            "session_1", "Test question", "The answer"
        )

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_resets_sources_after_retrieval(
        self, mock_session, mock_doc_proc, mock_vector, mock_ai
    ):
        """Test that sources are reset after being retrieved"""
        from rag_system import RAGSystem

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "Answer"
        mock_ai.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance

        config = Mock()
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "test-model"
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "/tmp/test"
        config.EMBEDDING_MODEL = "test-embed"
        config.MAX_HISTORY = 2

        rag = RAGSystem(config)
        mock_reset = Mock()
        rag.tool_manager.get_last_sources = Mock(return_value=[{"text": "src"}])
        rag.tool_manager.reset_sources = mock_reset

        rag.query("Test")

        mock_reset.assert_called_once()


class TestRAGSystemWithConfigBug:
    """Tests that demonstrate the MAX_RESULTS=0 bug"""

    def test_diagnose_config_bug(self):
        """Directly test for the configuration bug

        This test checks the actual config value and will FAIL
        if MAX_RESULTS is 0, documenting the bug.
        """
        from config import config

        if config.MAX_RESULTS == 0:
            pytest.fail(
                "BUG FOUND: MAX_RESULTS is 0 in config.py line 21.\n"
                "This causes VectorStore.search() to request 0 results from ChromaDB.\n"
                "All content searches return empty, making the chatbot unable to answer.\n"
                "FIX: Change 'MAX_RESULTS: int = 0' to 'MAX_RESULTS: int = 5'"
            )

    def test_config_propagates_to_vector_store(self):
        """Test that config MAX_RESULTS reaches VectorStore"""
        from config import config

        # Document the propagation path
        propagation = f"""
        Config Propagation Path:
        1. config.py:21 - MAX_RESULTS = {config.MAX_RESULTS}
        2. rag_system.py:18 - VectorStore(..., config.MAX_RESULTS)
        3. vector_store.py:37 - self.max_results = max_results
        4. vector_store.py:90 - search_limit = self.max_results
        5. vector_store.py:95 - n_results=search_limit

        When MAX_RESULTS=0, ChromaDB returns 0 results for every search.
        """

        if config.MAX_RESULTS == 0:
            pytest.fail(f"Bug in config propagation:{propagation}")


class TestRAGSystemToolIntegration:
    """Test tool integration in RAGSystem"""

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_passes_tools_to_ai_generator(
        self, mock_session, mock_doc_proc, mock_vector, mock_ai
    ):
        """Test that tools are passed to AIGenerator"""
        from rag_system import RAGSystem

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "Answer"
        mock_ai.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance

        config = Mock()
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "test-model"
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "/tmp/test"
        config.EMBEDDING_MODEL = "test-embed"
        config.MAX_HISTORY = 2

        rag = RAGSystem(config)
        rag.tool_manager.get_last_sources = Mock(return_value=[])
        rag.tool_manager.reset_sources = Mock()

        rag.query("Test question")

        call_args = mock_ai_instance.generate_response.call_args
        assert "tools" in call_args.kwargs
        assert "tool_manager" in call_args.kwargs
        assert len(call_args.kwargs["tools"]) == 2  # search + outline tools
