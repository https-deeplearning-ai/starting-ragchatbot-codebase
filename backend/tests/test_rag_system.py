"""End-to-end integration tests for RAGSystem"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from rag_system import RAGSystem
from tests.fixtures.sample_data import (
    SAMPLE_SEARCH_RESULTS_SUCCESS,
    SAMPLE_ANTHROPIC_FINAL_RESPONSE
)


class TestRAGSystemQueryFlow:
    """Test end-to-end query flow through RAGSystem"""

    def test_query_with_zero_max_results_config(self, mock_config_with_zero_max_results):
        """
        CRITICAL END-TO-END TEST: Test query with MAX_RESULTS=0

        This test demonstrates the complete failure path when MAX_RESULTS=0:
        1. RAGSystem initializes VectorStore with max_results=0
        2. User query triggers tool use
        3. Tool searches with n_results=0
        4. No results returned
        5. User sees "query failed" or empty response
        """
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager'):

            # Mock VectorStore with max_results=0
            mock_store = Mock()
            mock_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS
            MockVectorStore.return_value = mock_store

            # Mock AIGenerator
            mock_ai = Mock()
            mock_ai.generate_response.return_value = "I couldn't find any information."
            MockAIGenerator.return_value = mock_ai

            # Initialize RAGSystem with buggy config
            rag_system = RAGSystem(mock_config_with_zero_max_results)

            # Verify VectorStore was initialized with max_results=0 (the bug)
            MockVectorStore.assert_called_once()
            init_call = MockVectorStore.call_args
            assert init_call[0][2] == 0, "Bug: VectorStore initialized with max_results=0"

            # Execute query
            response, sources = rag_system.query("What is MCP?")

            # With max_results=0, the response will be poor or empty
            # This test documents the buggy behavior
            assert isinstance(response, str)

    def test_query_with_valid_max_results_config(self, mock_config):
        """Test that query works correctly with valid MAX_RESULTS"""
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager') as MockSessionManager:

            # Mock components
            mock_store = Mock()
            mock_store.search.return_value = SAMPLE_SEARCH_RESULTS_SUCCESS
            MockVectorStore.return_value = mock_store

            mock_ai = Mock()
            mock_ai.generate_response.return_value = "MCP stands for Model Context Protocol."
            MockAIGenerator.return_value = mock_ai

            mock_session_manager = Mock()
            mock_session_manager.get_conversation_history.return_value = None
            MockSessionManager.return_value = mock_session_manager

            # Initialize RAGSystem with valid config
            rag_system = RAGSystem(mock_config)

            # Verify VectorStore initialized with max_results=5
            init_call = MockVectorStore.call_args
            assert init_call[0][2] == 5, "VectorStore should be initialized with max_results=5"

            # Execute query
            response, sources = rag_system.query("What is MCP?")

            # Should return meaningful response
            assert isinstance(response, str)
            assert len(response) > 0
            assert "Model Context Protocol" in response

    def test_query_sources_are_returned(self, mock_config):
        """Test that sources list is returned from query"""
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager') as MockSessionManager:

            # Setup mocks
            mock_store = Mock()
            MockVectorStore.return_value = mock_store

            mock_ai = Mock()
            mock_ai.generate_response.return_value = "Test response"
            MockAIGenerator.return_value = mock_ai

            MockSessionManager.return_value = Mock()

            # Initialize RAGSystem
            rag_system = RAGSystem(mock_config)

            # Mock tool_manager to return sources
            rag_system.tool_manager.get_last_sources = Mock(return_value=[
                {"text": "MCP - Lesson 1", "url": "https://example.com/lesson1"}
            ])

            # Execute query
            response, sources = rag_system.query("What is MCP?")

            # Verify sources are returned
            assert isinstance(sources, list)
            assert len(sources) == 1
            assert sources[0]['text'] == "MCP - Lesson 1"
            assert sources[0]['url'] == "https://example.com/lesson1"

    def test_query_updates_conversation_history(self, mock_config):
        """Test that queries update conversation history"""
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager') as MockSessionManager:

            # Setup mocks
            MockVectorStore.return_value = Mock()

            mock_ai = Mock()
            mock_ai.generate_response.return_value = "Test response"
            MockAIGenerator.return_value = mock_ai

            mock_session_manager = Mock()
            mock_session_manager.get_conversation_history.return_value = "Previous conversation"
            MockSessionManager.return_value = mock_session_manager

            # Initialize RAGSystem
            rag_system = RAGSystem(mock_config)

            # Execute query with session_id
            session_id = "test_session_123"
            response, sources = rag_system.query("What is MCP?", session_id=session_id)

            # Verify conversation history was retrieved
            mock_session_manager.get_conversation_history.assert_called_once_with(session_id)

            # Verify conversation was updated
            mock_session_manager.add_exchange.assert_called_once()
            add_call = mock_session_manager.add_exchange.call_args
            assert add_call[0][0] == session_id
            assert add_call[0][1] == "What is MCP?"
            assert add_call[0][2] == "Test response"

    def test_query_resets_sources_after_retrieval(self, mock_config):
        """Test that sources are reset after being retrieved"""
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager') as MockSessionManager:

            # Setup mocks
            MockVectorStore.return_value = Mock()
            MockAIGenerator.return_value = Mock(generate_response=Mock(return_value="Test"))
            MockSessionManager.return_value = Mock()

            # Initialize RAGSystem
            rag_system = RAGSystem(mock_config)

            # Mock tool_manager methods
            rag_system.tool_manager.get_last_sources = Mock(return_value=[{"text": "source1", "url": "url1"}])
            rag_system.tool_manager.reset_sources = Mock()

            # Execute query
            response, sources = rag_system.query("test")

            # Verify sources were retrieved and then reset
            rag_system.tool_manager.get_last_sources.assert_called_once()
            rag_system.tool_manager.reset_sources.assert_called_once()

    def test_query_passes_tools_to_ai_generator(self, mock_config):
        """Test that tool definitions are passed to AIGenerator"""
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager') as MockSessionManager:

            # Setup mocks
            MockVectorStore.return_value = Mock()

            mock_ai = Mock()
            mock_ai.generate_response.return_value = "Test response"
            MockAIGenerator.return_value = mock_ai

            MockSessionManager.return_value = Mock()

            # Initialize RAGSystem
            rag_system = RAGSystem(mock_config)

            # Execute query
            response, sources = rag_system.query("What is MCP?")

            # Verify AIGenerator.generate_response was called with tools
            mock_ai.generate_response.assert_called_once()
            call_args = mock_ai.generate_response.call_args
            assert 'tools' in call_args[1]
            assert 'tool_manager' in call_args[1]

            # Verify tools list includes search_course_content and get_course_outline
            tools = call_args[1]['tools']
            assert len(tools) == 2  # Should have 2 tools registered
            tool_names = [t['name'] for t in tools]
            assert 'search_course_content' in tool_names
            assert 'get_course_outline' in tool_names


class TestRAGSystemInitialization:
    """Test RAGSystem initialization with different configurations"""

    def test_initialization_with_valid_config(self, mock_config):
        """Test that RAGSystem initializes correctly with valid config"""
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager') as MockSessionManager, \
             patch('rag_system.DocumentProcessor'):

            # Initialize
            rag_system = RAGSystem(mock_config)

            # Verify all components are initialized
            assert rag_system.config == mock_config
            assert rag_system.vector_store is not None
            assert rag_system.ai_generator is not None
            assert rag_system.session_manager is not None
            assert rag_system.tool_manager is not None

            # Verify tools are registered
            assert len(rag_system.tool_manager.tools) == 2

    def test_initialization_with_zero_max_results(self, mock_config_with_zero_max_results):
        """
        Test initialization with MAX_RESULTS=0 (documents the bug)

        After the fix, this should raise a ValueError
        """
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.DocumentProcessor'):

            # Currently this doesn't raise an error (the bug)
            rag_system = RAGSystem(mock_config_with_zero_max_results)

            # Verify VectorStore was called with max_results=0
            init_call = MockVectorStore.call_args
            assert init_call[0][2] == 0, "Bug: System accepts MAX_RESULTS=0"

    def test_tools_are_registered_on_init(self, mock_config):
        """Test that both tools are registered during initialization"""
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.DocumentProcessor'):

            # Initialize
            rag_system = RAGSystem(mock_config)

            # Verify both tools are registered
            tool_names = list(rag_system.tool_manager.tools.keys())
            assert 'search_course_content' in tool_names
            assert 'get_course_outline' in tool_names

            # Verify tools have correct instances
            assert rag_system.search_tool is not None
            assert rag_system.outline_tool is not None


class TestRAGSystemAnalytics:
    """Test RAGSystem analytics functionality"""

    def test_get_course_analytics(self, mock_config):
        """Test that course analytics are returned correctly"""
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.DocumentProcessor'):

            # Mock VectorStore methods
            mock_store = Mock()
            mock_store.get_course_count.return_value = 3
            mock_store.get_existing_course_titles.return_value = ["Course1", "Course2", "Course3"]
            MockVectorStore.return_value = mock_store

            # Initialize
            rag_system = RAGSystem(mock_config)

            # Get analytics
            analytics = rag_system.get_course_analytics()

            # Verify analytics structure
            assert 'total_courses' in analytics
            assert 'course_titles' in analytics
            assert analytics['total_courses'] == 3
            assert len(analytics['course_titles']) == 3
