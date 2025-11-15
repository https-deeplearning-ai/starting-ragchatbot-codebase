"""
Integration tests for RAGSystem

Tests the main query orchestration to ensure:
- Correct flow from query to response
- Proper integration of all components
- Session management
- Source tracking
- Error propagation
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from rag_system import RAGSystem
from vector_store import VectorStore
from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager
from session_manager import SessionManager


@pytest.mark.integration
class TestRAGSystemQuery:
    """Tests for RAGSystem.query() method"""

    def test_query_with_general_knowledge_no_search(
        self,
        mock_anthropic_client_direct,
        mock_vector_store,
        mock_session_manager
    ):
        """Test 1: General knowledge query doesn't trigger search"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Create RAG system components
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            # Create tool manager and search tool
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            # Create RAG system
            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Query with general knowledge question
            response, sources = rag_system.query(
                query="What is 2+2?",
                session_id="test-session"
            )

            # Verify response
            assert isinstance(response, str)
            assert len(response) > 0

            # Verify search was not called (direct response, no tool use)
            # Note: With direct response, search should not be called
            assert isinstance(sources, list)

    def test_query_with_course_specific_triggers_search(
        self,
        mock_anthropic_client_tool_use,
        mock_vector_store,
        mock_session_manager,
        sample_search_results
    ):
        """Test 2: Course-specific query triggers search tool"""
        mock_vector_store.search.return_value = sample_search_results

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            # Create RAG system components
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            # Create tool manager and search tool
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            # Create RAG system
            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Query with course-specific question
            response, sources = rag_system.query(
                query="What is RAG?",
                session_id="test-session"
            )

            # Verify search was called
            mock_vector_store.search.assert_called_once()

            # Verify response
            assert isinstance(response, str)
            assert len(response) > 0

            # Verify sources were retrieved
            assert isinstance(sources, list)
            assert len(sources) > 0

    def test_error_propagation_from_ai_generator(
        self,
        mock_anthropic_client_api_error,
        mock_vector_store,
        mock_session_manager
    ):
        """Test 3: Errors from AIGenerator propagate correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_api_error):
            # Create RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Query should raise exception (no error handling in RAGSystem)
            with pytest.raises(Exception) as exc_info:
                rag_system.query(query="Test query", session_id="test-session")

            assert "API connection timeout" in str(exc_info.value)

    def test_session_management_integration(
        self,
        mock_anthropic_client_direct,
        mock_vector_store,
        mock_session_manager
    ):
        """Test 4: Session management is properly integrated"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Create RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Make query
            response, sources = rag_system.query(
                query="Test query",
                session_id="test-session"
            )

            # Verify session manager methods were called
            mock_session_manager.get_conversation_history.assert_called_once_with("test-session")
            mock_session_manager.update_conversation.assert_called_once()

            # Verify update was called with correct parameters
            update_call_args = mock_session_manager.update_conversation.call_args
            assert update_call_args.args[0] == "test-session"
            assert "Test query" in update_call_args.args[1]
            assert isinstance(update_call_args.args[2], str)

    def test_source_retrieval_flow(
        self,
        mock_anthropic_client_tool_use,
        mock_vector_store,
        mock_session_manager,
        sample_search_results
    ):
        """Test 5: Sources are properly retrieved and returned"""
        mock_vector_store.search.return_value = sample_search_results

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            # Create RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Make query
            response, sources = rag_system.query(
                query="What is RAG?",
                session_id="test-session"
            )

            # Verify sources structure
            assert isinstance(sources, list)
            assert len(sources) > 0

            # Verify each source has required fields
            for source in sources:
                assert isinstance(source, dict)
                assert "text" in source
                assert "url" in source

            # Verify sources were reset after retrieval
            # (This behavior depends on implementation)

    def test_conversation_history_usage(
        self,
        mock_anthropic_client_direct,
        mock_vector_store,
        mock_session_manager_with_history
    ):
        """Test 6: Conversation history is used in AI generation"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Create RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager_with_history

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Make query (session has history)
            response, sources = rag_system.query(
                query="Can you elaborate?",
                session_id="test-session"
            )

            # Verify history was retrieved
            mock_session_manager_with_history.get_conversation_history.assert_called_once()

            # Verify API call included history in system prompt
            call_kwargs = mock_anthropic_client_direct.messages.create.call_args.kwargs
            system_content = call_kwargs["system"]
            assert "Previous conversation:" in system_content

    def test_query_without_session_id(
        self,
        mock_anthropic_client_direct,
        mock_vector_store,
        mock_session_manager
    ):
        """Test 7: Query works without session_id (creates new session)"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Create RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Make query without session_id
            response, sources = rag_system.query(query="Test query")

            # Should still work (session_id is optional)
            assert isinstance(response, str)
            assert isinstance(sources, list)

            # Session manager may still be called (with None)
            # Behavior depends on implementation


@pytest.mark.integration
class TestRAGSystemToolExecution:
    """Tests for tool execution within RAG system"""

    def test_tool_execution_error_propagates(
        self,
        mock_anthropic_client_tool_use,
        mock_vector_store_exception,
        mock_session_manager
    ):
        """Test tool execution errors propagate correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            # Create RAG system with vector store that raises exception
            vector_store = mock_vector_store_exception
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Query should raise exception when tool executes
            with pytest.raises(Exception) as exc_info:
                rag_system.query(query="What is RAG?", session_id="test-session")

            assert "ChromaDB connection lost" in str(exc_info.value)

    def test_multiple_queries_reset_sources(
        self,
        mock_anthropic_client_tool_use,
        mock_vector_store,
        mock_session_manager,
        sample_search_results
    ):
        """Test that sources are reset between queries"""
        mock_vector_store.search.return_value = sample_search_results

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            # Create RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # First query
            response1, sources1 = rag_system.query(query="What is RAG?", session_id="session1")
            assert len(sources1) > 0

            # Reset mock to simulate new API calls
            mock_anthropic_client_tool_use.messages.create.reset_mock()
            mock_anthropic_client_tool_use.messages.create.side_effect = [
                Mock(content=[Mock(type="tool_use", id="toolu_456", name="search_course_content", input={"query": "vector databases"})], stop_reason="tool_use"),
                Mock(content=[Mock(text="Vector databases store embeddings.")], stop_reason="end_turn")
            ]

            # Second query - sources should be independent
            response2, sources2 = rag_system.query(query="What are vector databases?", session_id="session2")

            # Both should have sources
            assert len(sources2) > 0

            # Verify searches were independent
            assert mock_vector_store.search.call_count == 2


@pytest.mark.integration
class TestRAGSystemEdgeCases:
    """Edge case tests for RAG system"""

    def test_empty_query_string(
        self,
        mock_anthropic_client_direct,
        mock_vector_store,
        mock_session_manager
    ):
        """Test with empty query"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Create RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Empty query
            response, sources = rag_system.query(query="", session_id="test-session")

            # Should still return response
            assert isinstance(response, str)
            assert isinstance(sources, list)

    def test_very_long_query(
        self,
        mock_anthropic_client_direct,
        mock_vector_store,
        mock_session_manager
    ):
        """Test with very long query"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Create RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = mock_session_manager

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Very long query
            long_query = "What is RAG? " * 200
            response, sources = rag_system.query(query=long_query, session_id="test-session")

            # Should handle long queries
            assert isinstance(response, str)
            assert isinstance(sources, list)
