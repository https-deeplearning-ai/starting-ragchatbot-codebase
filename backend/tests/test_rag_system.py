"""
Integration tests for RAGSystem.

These tests reveal the MAX_RESULTS=0 bug through integration testing.
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag_system import RAGSystem
from vector_store import SearchResults


class TestRAGSystemInitialization:
    """Test RAGSystem initialization"""

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.SessionManager')
    def test_init_creates_all_components(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vector_store, config_with_bug
    ):
        """Verify all components are initialized"""
        rag = RAGSystem(config_with_bug)

        mock_vector_store.assert_called_once()
        mock_ai_gen.assert_called_once()
        mock_doc_proc.assert_called_once()
        mock_session.assert_called_once()

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.SessionManager')
    def test_init_registers_tools(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vector_store, config_with_bug
    ):
        """Verify search and outline tools are registered"""
        rag = RAGSystem(config_with_bug)

        # Both tools should be registered
        assert "search_course_content" in rag.tool_manager.tools
        assert "get_course_outline" in rag.tool_manager.tools

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.SessionManager')
    def test_init_with_max_results_zero(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vector_store, config_with_bug
    ):
        """
        BUG DETECTION: VectorStore receives MAX_RESULTS=0 from config
        """
        rag = RAGSystem(config_with_bug)

        # Verify VectorStore was initialized with max_results=0
        call_args = mock_vector_store.call_args
        assert call_args[0][2] == 0  # Third positional arg is max_results


class TestRAGSystemQuery:
    """Test RAGSystem.query() method"""

    @pytest.fixture
    def mock_rag_system(self, config_with_bug):
        """RAGSystem with mocked components"""
        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager') as mock_session:

            # Configure mocks
            mock_vs_instance = Mock()
            mock_vs.return_value = mock_vs_instance

            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.return_value = "Generated response"

            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get_conversation_history.return_value = None

            rag = RAGSystem(config_with_bug)
            return rag

    def test_query_calls_ai_generator(self, mock_rag_system):
        """Test that query calls AI generator"""
        mock_rag_system.ai_generator.generate_response.return_value = "Response"

        response, sources = mock_rag_system.query("What is MCP?")

        mock_rag_system.ai_generator.generate_response.assert_called_once()

    def test_query_passes_tools_to_ai_generator(self, mock_rag_system):
        """Test that tools are passed to AI generator"""
        mock_rag_system.ai_generator.generate_response.return_value = "Response"

        mock_rag_system.query("What is MCP?")

        call_kwargs = mock_rag_system.ai_generator.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tool_manager"] == mock_rag_system.tool_manager

    def test_query_retrieves_session_history(self, mock_rag_system):
        """Test that session history is retrieved for existing session"""
        mock_rag_system.session_manager.get_conversation_history.return_value = "Previous chat"
        mock_rag_system.ai_generator.generate_response.return_value = "Response"

        mock_rag_system.query("Follow up question", session_id="session_1")

        mock_rag_system.session_manager.get_conversation_history.assert_called_with("session_1")

    def test_query_updates_session_after_response(self, mock_rag_system):
        """Test that session is updated after generating response"""
        mock_rag_system.ai_generator.generate_response.return_value = "Response"

        mock_rag_system.query("Question", session_id="session_1")

        mock_rag_system.session_manager.add_exchange.assert_called_once()

    def test_query_retrieves_sources_from_tool_manager(self, mock_rag_system):
        """Test that sources are retrieved from tool manager"""
        mock_rag_system.ai_generator.generate_response.return_value = "Response"
        mock_rag_system.tool_manager.get_last_sources = Mock(return_value=["Source 1"])

        response, sources = mock_rag_system.query("Question")

        assert sources == ["Source 1"]

    def test_query_resets_sources_after_retrieval(self, mock_rag_system):
        """Test that sources are reset after being retrieved"""
        mock_rag_system.ai_generator.generate_response.return_value = "Response"
        mock_rag_system.tool_manager.get_last_sources = Mock(return_value=["Source 1"])
        mock_rag_system.tool_manager.reset_sources = Mock()

        mock_rag_system.query("Question")

        mock_rag_system.tool_manager.reset_sources.assert_called_once()


class TestRAGSystemWithBug:
    """
    Integration tests that specifically reveal the MAX_RESULTS=0 bug.
    These tests simulate the full query flow with the buggy configuration.
    """

    @pytest.fixture
    def rag_with_empty_search(self, config_with_bug):
        """RAGSystem configured to return empty search results"""
        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager') as mock_session:

            # VectorStore returns empty results (MAX_RESULTS=0 behavior)
            mock_vs_instance = Mock()
            mock_vs_instance.search.return_value = SearchResults(
                documents=[],
                metadata=[],
                distances=[]
            )
            mock_vs_instance.max_results = 0
            mock_vs.return_value = mock_vs_instance

            # AI generator configured for tool use flow
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance

            mock_session_instance = Mock()
            mock_session_instance.get_conversation_history.return_value = None
            mock_session.return_value = mock_session_instance

            rag = RAGSystem(config_with_bug)
            return rag, mock_ai_instance

    def test_content_query_returns_no_results_with_bug(self, rag_with_empty_search):
        """
        CRITICAL BUG DETECTION TEST

        With MAX_RESULTS=0, any content-related query will fail because
        the search tool always returns empty results.
        """
        rag, mock_ai = rag_with_empty_search

        # Simulate Claude using the search tool
        mock_ai.generate_response.return_value = "I couldn't find relevant information."

        response, sources = rag.query("What is MCP protocol?")

        # Sources should be empty because search returned nothing
        assert sources == [] or len(sources) == 0

    def test_search_tool_receives_empty_results_from_vector_store(self, rag_with_empty_search):
        """
        Verify that search tool execution path leads to empty results
        when MAX_RESULTS=0.
        """
        rag, _ = rag_with_empty_search

        # Execute search tool directly
        result = rag.search_tool.execute(query="What is MCP?")

        assert "No relevant content found" in result

    def test_sources_never_populated_with_bug(self, rag_with_empty_search):
        """
        Verify sources list remains empty throughout the query flow
        when MAX_RESULTS=0.
        """
        rag, mock_ai = rag_with_empty_search
        mock_ai.generate_response.return_value = "No content found"

        # Execute multiple queries
        for query in ["What is MCP?", "Explain tool calling", "Course overview"]:
            response, sources = rag.query(query)
            assert sources == []


class TestRAGSystemFixed:
    """
    Tests that verify correct behavior when MAX_RESULTS is properly set.
    These should PASS with fixed configuration.
    """

    @pytest.fixture
    def rag_with_working_search(self, config_fixed):
        """RAGSystem configured to return valid search results"""
        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager') as mock_session:

            # VectorStore returns valid results
            mock_vs_instance = Mock()
            mock_vs_instance.search.return_value = SearchResults(
                documents=["MCP is a protocol for AI tool integration."],
                metadata=[{"course_title": "MCP Course", "lesson_number": 1}],
                distances=[0.2]
            )
            mock_vs_instance.max_results = 5
            mock_vs.return_value = mock_vs_instance

            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance

            mock_session_instance = Mock()
            mock_session_instance.get_conversation_history.return_value = None
            mock_session.return_value = mock_session_instance

            rag = RAGSystem(config_fixed)
            return rag, mock_ai_instance

    def test_content_query_returns_results_when_fixed(self, rag_with_working_search):
        """
        With MAX_RESULTS=5, content queries should return results.
        """
        rag, mock_ai = rag_with_working_search
        mock_ai.generate_response.return_value = "MCP is a protocol..."

        # Execute search tool directly
        result = rag.search_tool.execute(query="What is MCP?")

        # Should NOT contain "No relevant content found"
        assert "No relevant content found" not in result
        assert "MCP" in result

    def test_sources_populated_when_fixed(self, rag_with_working_search):
        """
        With proper configuration, sources should be populated after search.
        """
        rag, _ = rag_with_working_search

        # Execute search
        rag.search_tool.execute(query="What is MCP?")

        # Sources should be populated
        assert len(rag.search_tool.last_sources) > 0


class TestVectorStoreMaxResultsBehavior:
    """
    Direct tests for VectorStore search limit behavior.
    These tests explicitly verify the MAX_RESULTS parameter effect.
    """

    def test_vector_store_search_with_limit_zero(self):
        """
        CRITICAL: When n_results=0, ChromaDB returns empty results.
        This is the root cause of the bug.
        """
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]]
            }
            mock_client.return_value.get_or_create_collection.return_value = mock_collection

            from vector_store import VectorStore
            store = VectorStore("./test_db", "test-model", max_results=0)

            result = store.search("test query")

            # With max_results=0, query is called with n_results=0
            call_args = mock_collection.query.call_args[1]
            assert call_args["n_results"] == 0

            # Result should be empty
            assert result.is_empty()

    def test_vector_store_search_with_proper_limit(self):
        """
        With max_results=5, search should return up to 5 results.
        """
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [["doc1", "doc2"]],
                'metadatas': [[{"title": "Course1"}, {"title": "Course2"}]],
                'distances': [[0.1, 0.2]]
            }
            mock_client.return_value.get_or_create_collection.return_value = mock_collection

            from vector_store import VectorStore
            store = VectorStore("./test_db", "test-model", max_results=5)

            result = store.search("test query")

            call_args = mock_collection.query.call_args[1]
            assert call_args["n_results"] == 5

            # Result should have documents
            assert not result.is_empty()
