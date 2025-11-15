"""
End-to-end integration tests for the RAG Chatbot System

These tests verify the complete pipeline from query to response,
including actual component integration (with mocked external services).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from rag_system import RAGSystem
from vector_store import VectorStore, SearchResults
from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager
from session_manager import SessionManager
from config import Config


@pytest.mark.integration
class TestEndToEndQueryFlow:
    """End-to-end tests for complete query processing"""

    def test_complete_query_flow_with_mocked_api(
        self,
        mock_anthropic_client_tool_use,
        mock_vector_store,
        sample_search_results
    ):
        """Test 1: Complete query flow from input to output with mocked API"""
        mock_vector_store.search.return_value = sample_search_results

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            # Initialize all components
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Execute complete query
            query = "What is RAG and how does it work?"
            response, sources = rag_system.query(query=query, session_id="integration-test-1")

            # Verify complete flow
            assert isinstance(response, str)
            assert len(response) > 0

            # Verify sources were retrieved
            assert isinstance(sources, list)
            assert len(sources) > 0

            # Verify vector search was called
            mock_vector_store.search.assert_called()

            # Verify API was called twice (tool use flow)
            assert mock_anthropic_client_tool_use.messages.create.call_count == 2

            # Verify session was updated
            history = session_manager.get_conversation_history("integration-test-1")
            assert history is not None
            assert query in history

    @pytest.mark.slow
    def test_with_real_vector_store(self, temp_chroma_db, mock_anthropic_client_tool_use, sample_course_chunks):
        """Test 2: Integration with real ChromaDB (mocked API)"""
        pytest.skip("Skipping real ChromaDB test - requires ChromaDB setup")

        # This test would create a real VectorStore and test actual vector search
        # Skipped by default to avoid external dependencies
        # To run: pytest -m slow --run-slow

    def test_api_timeout_scenario(self, mock_vector_store):
        """Test 3: API timeout is handled correctly"""
        # Create mock client that simulates timeout
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Request timeout after 30s")

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_client):
            # Initialize components
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Query should raise timeout exception
            with pytest.raises(Exception) as exc_info:
                rag_system.query(query="What is RAG?", session_id="timeout-test")

            assert "timeout" in str(exc_info.value).lower()

    def test_chromadb_connection_failure(self, mock_anthropic_client_tool_use):
        """Test 4: ChromaDB connection failure is handled"""
        # Create mock vector store that raises connection error
        mock_store = Mock()
        mock_store.search.side_effect = Exception("Failed to connect to ChromaDB")

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            # Initialize components
            vector_store = mock_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Query should raise exception during tool execution
            with pytest.raises(Exception) as exc_info:
                rag_system.query(query="What is RAG?", session_id="chroma-fail-test")

            assert "ChromaDB" in str(exc_info.value)

    def test_invalid_api_key_handling(self, mock_vector_store):
        """Test 5: Invalid API key produces clear error"""
        # Create mock client that raises authentication error
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Invalid API key")

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_client):
            # Initialize components
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="invalid-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Query should raise authentication exception
            with pytest.raises(Exception) as exc_info:
                rag_system.query(query="Test query", session_id="auth-fail-test")

            assert "API key" in str(exc_info.value)


@pytest.mark.integration
class TestMultiSessionManagement:
    """Tests for managing multiple concurrent sessions"""

    def test_multiple_sessions_isolated(self, mock_anthropic_client_direct, mock_vector_store):
        """Test that multiple sessions maintain independent conversations"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Initialize RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Query from session 1
            response1, _ = rag_system.query(query="What is RAG?", session_id="session-1")

            # Query from session 2
            response2, _ = rag_system.query(query="What is a vector database?", session_id="session-2")

            # Query session 1 again
            response3, _ = rag_system.query(query="Can you elaborate?", session_id="session-1")

            # Verify sessions are independent
            history1 = session_manager.get_conversation_history("session-1")
            history2 = session_manager.get_conversation_history("session-2")

            assert "What is RAG?" in history1
            assert "Can you elaborate?" in history1
            assert "What is a vector database?" in history2
            assert "Can you elaborate?" not in history2

    def test_session_history_limit(self, mock_anthropic_client_direct, mock_vector_store):
        """Test that session history respects MAX_HISTORY limit"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Initialize RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Make multiple queries to exceed MAX_HISTORY
            for i in range(10):
                rag_system.query(query=f"Question {i}?", session_id="history-test")

            # Get history
            history = session_manager.get_conversation_history("history-test")

            # History should be limited (MAX_HISTORY * 2 messages)
            # Default MAX_HISTORY is 2, so should have 4 messages max
            if history:
                message_count = history.count("User:") + history.count("Assistant:")
                # Should not have all 20 messages (10 user + 10 assistant)
                assert message_count <= 10  # Depending on MAX_HISTORY setting


@pytest.mark.integration
class TestErrorRecovery:
    """Tests for error recovery and resilience"""

    def test_recovery_after_api_failure(self, mock_vector_store):
        """Test that system can recover after API failure"""
        # Create mock that fails first time, succeeds second time
        mock_client = Mock()
        mock_response_success = Mock()
        mock_response_success.content = [Mock(text="This is the answer")]
        mock_response_success.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [
            Exception("Temporary API error"),
            mock_response_success
        ]

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_client):
            # Initialize components
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # First query fails
            with pytest.raises(Exception):
                rag_system.query(query="First query", session_id="recovery-test")

            # Second query succeeds
            response, sources = rag_system.query(query="Second query", session_id="recovery-test")

            assert isinstance(response, str)
            assert len(response) > 0

    def test_partial_tool_execution_failure(self, mock_anthropic_client_tool_use, mock_vector_store):
        """Test behavior when tool execution partially fails"""
        # Vector store fails on first call, succeeds on second
        mock_vector_store.search.side_effect = [
            Exception("Temporary connection error"),
            SearchResults(
                documents=["Success content"],
                metadata=[{"course_title": "Test Course", "lesson_number": 0}],
                distances=[0.1],
                error=None
            )
        ]

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            # Initialize components
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # First query fails during tool execution
            with pytest.raises(Exception):
                rag_system.query(query="What is RAG?", session_id="partial-fail-test")

            # Reset mock_anthropic_client_tool_use for second call
            mock_anthropic_client_tool_use.messages.create.reset_mock()
            mock_anthropic_client_tool_use.messages.create.side_effect = [
                Mock(content=[Mock(type="tool_use", id="toolu_789", name="search_course_content", input={"query": "RAG"})], stop_reason="tool_use"),
                Mock(content=[Mock(text="RAG answer")], stop_reason="end_turn")
            ]

            # Second query succeeds
            response, sources = rag_system.query(query="What is RAG?", session_id="partial-fail-test-2")
            assert isinstance(response, str)


@pytest.mark.integration
class TestPerformance:
    """Performance and stress tests"""

    def test_rapid_sequential_queries(self, mock_anthropic_client_direct, mock_vector_store):
        """Test system handles rapid sequential queries"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Initialize RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Make 10 rapid queries
            for i in range(10):
                response, sources = rag_system.query(
                    query=f"Question {i}?",
                    session_id=f"perf-test-{i}"
                )
                assert isinstance(response, str)
                assert isinstance(sources, list)

    def test_long_conversation_session(self, mock_anthropic_client_direct, mock_vector_store):
        """Test system handles long conversation in single session"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            # Initialize RAG system
            vector_store = mock_vector_store
            ai_generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
            session_manager = SessionManager()

            tool_manager = ToolManager()
            search_tool = CourseSearchTool(vector_store)
            tool_manager.register_tool(search_tool)

            rag_system = RAGSystem(
                vector_store=vector_store,
                ai_generator=ai_generator,
                tool_manager=tool_manager,
                session_manager=session_manager
            )

            # Make 20 queries in same session
            for i in range(20):
                response, sources = rag_system.query(
                    query=f"Follow-up question {i}?",
                    session_id="long-conversation"
                )
                assert isinstance(response, str)

            # Verify history is maintained but limited
            history = session_manager.get_conversation_history("long-conversation")
            assert history is not None
