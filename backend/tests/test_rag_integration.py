"""Integration tests for RAG system in rag_system.py"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from rag_system import RAGSystem
from config import Config
from vector_store import SearchResults


class MockConfig:
    """Mock configuration for testing"""
    ANTHROPIC_API_KEY = "test_key"
    ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    CHROMA_PATH = "./test_chroma_db"
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100
    MAX_RESULTS = 5
    MAX_HISTORY = 2


@pytest.fixture
def mock_config():
    """Create mock configuration"""
    return MockConfig()


@pytest.fixture
def rag_system(mock_config):
    """Create RAG system with mocked dependencies"""
    with patch('rag_system.DocumentProcessor'), \
         patch('rag_system.VectorStore') as MockVectorStore, \
         patch('rag_system.AIGenerator') as MockAIGenerator, \
         patch('rag_system.SessionManager') as MockSessionManager:

        # Create RAG system
        system = RAGSystem(mock_config)

        # Store mocks for access in tests
        system.mock_vector_store = system.vector_store
        system.mock_ai_generator = system.ai_generator
        system.mock_session_manager = system.session_manager

        return system


class TestRAGSystemInitialization:
    """Test RAG system initialization"""

    def test_components_initialized(self, rag_system):
        """Test that all components are initialized"""
        assert rag_system.vector_store is not None
        assert rag_system.ai_generator is not None
        assert rag_system.session_manager is not None
        assert rag_system.tool_manager is not None
        assert rag_system.search_tool is not None

    def test_tools_registered(self, rag_system):
        """Test that search tools are registered with tool manager"""
        tool_defs = rag_system.tool_manager.get_tool_definitions()
        assert len(tool_defs) > 0
        tool_names = [tool["name"] for tool in tool_defs]
        assert "search_course_content" in tool_names


class TestRAGSystemQuery:
    """Test RAG system query method"""

    def test_query_without_session(self, rag_system):
        """Test query without session creates new session"""
        # Setup
        rag_system.mock_ai_generator.generate_response.return_value = "Test answer"
        rag_system.mock_session_manager.get_conversation_history.return_value = None
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        rag_system.tool_manager.get_last_source_links = Mock(return_value=[])
        rag_system.tool_manager.reset_sources = Mock()

        # Execute
        answer, sources, links = rag_system.query("What is Python?", session_id=None)

        # Verify
        assert answer == "Test answer"
        rag_system.mock_session_manager.get_conversation_history.assert_called_once_with(None)

    def test_query_with_session(self, rag_system):
        """Test query with existing session uses history"""
        # Setup
        rag_system.mock_ai_generator.generate_response.return_value = "Follow-up answer"
        rag_system.mock_session_manager.get_conversation_history.return_value = "Previous chat history"
        rag_system.tool_manager.get_last_sources = Mock(return_value=["Source 1"])
        rag_system.tool_manager.get_last_source_links = Mock(return_value=["http://link1"])
        rag_system.tool_manager.reset_sources = Mock()

        # Execute
        answer, sources, links = rag_system.query("Tell me more", session_id="session_123")

        # Verify
        rag_system.mock_session_manager.get_conversation_history.assert_called_once_with("session_123")
        rag_system.mock_ai_generator.generate_response.assert_called_once()
        call_args = rag_system.mock_ai_generator.generate_response.call_args
        assert call_args.kwargs["conversation_history"] == "Previous chat history"

    def test_query_passes_tools_to_ai(self, rag_system):
        """Test that query passes tool definitions to AI generator"""
        # Setup
        rag_system.mock_ai_generator.generate_response.return_value = "Answer"
        rag_system.mock_session_manager.get_conversation_history.return_value = None
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        rag_system.tool_manager.get_last_source_links = Mock(return_value=[])
        rag_system.tool_manager.reset_sources = Mock()

        # Execute
        rag_system.query("Test query")

        # Verify tools were passed
        call_args = rag_system.mock_ai_generator.generate_response.call_args
        assert "tools" in call_args.kwargs
        assert "tool_manager" in call_args.kwargs
        assert call_args.kwargs["tool_manager"] == rag_system.tool_manager

    def test_query_returns_sources(self, rag_system):
        """Test that query returns sources from tool manager"""
        # Setup
        rag_system.mock_ai_generator.generate_response.return_value = "Answer"
        rag_system.mock_session_manager.get_conversation_history.return_value = None
        rag_system.tool_manager.get_last_sources = Mock(return_value=["Python Course - Lesson 1"])
        rag_system.tool_manager.get_last_source_links = Mock(return_value=["http://example.com"])
        rag_system.tool_manager.reset_sources = Mock()

        # Execute
        answer, sources, links = rag_system.query("What is Python?")

        # Verify
        assert sources == ["Python Course - Lesson 1"]
        assert links == ["http://example.com"]
        rag_system.tool_manager.get_last_sources.assert_called_once()
        rag_system.tool_manager.get_last_source_links.assert_called_once()

    def test_query_resets_sources(self, rag_system):
        """Test that sources are reset after query"""
        # Setup
        rag_system.mock_ai_generator.generate_response.return_value = "Answer"
        rag_system.mock_session_manager.get_conversation_history.return_value = None
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        rag_system.tool_manager.get_last_source_links = Mock(return_value=[])
        rag_system.tool_manager.reset_sources = Mock()

        # Execute
        rag_system.query("Test")

        # Verify
        rag_system.tool_manager.reset_sources.assert_called_once()

    def test_query_updates_conversation_history(self, rag_system):
        """Test that query updates conversation history"""
        # Setup
        rag_system.mock_ai_generator.generate_response.return_value = "Answer"
        rag_system.mock_session_manager.get_conversation_history.return_value = None
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        rag_system.tool_manager.get_last_source_links = Mock(return_value=[])
        rag_system.tool_manager.reset_sources = Mock()

        # Execute
        answer, sources, links = rag_system.query("What is Python?", session_id="session_123")

        # Verify
        rag_system.mock_session_manager.add_exchange.assert_called_once_with(
            "session_123",
            "What is Python?",
            "Answer"
        )


class TestRAGSystemWithRealToolManager:
    """Test RAG system with real tool manager (not mocked)"""

    def test_tool_manager_executes_search(self, mock_config):
        """Test that tool manager can execute search tool"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager'):

            # Create RAG system (tool manager is real)
            system = RAGSystem(mock_config)

            # Setup mocks
            mock_vector_store_instance = MockVectorStore.return_value
            mock_vector_store_instance.search.return_value = SearchResults(
                documents=["Python content"],
                metadata=[{"course_title": "Python Course", "lesson_number": 1}],
                distances=[0.1]
            )
            mock_vector_store_instance.get_lesson_link.return_value = "http://lesson1"

            # Execute tool directly
            result = system.tool_manager.execute_tool(
                "search_course_content",
                query="What is Python?"
            )

            # Verify
            assert "Python content" in result
            assert "[Python Course - Lesson 1]" in result

    def test_sources_tracked_across_search(self, mock_config):
        """Test that sources are tracked when search is executed"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager'):

            # Create RAG system
            system = RAGSystem(mock_config)

            # Setup mocks
            mock_vector_store_instance = MockVectorStore.return_value
            mock_vector_store_instance.search.return_value = SearchResults(
                documents=["Python content"],
                metadata=[{"course_title": "Python Course", "lesson_number": 1}],
                distances=[0.1]
            )
            mock_vector_store_instance.get_lesson_link.return_value = "http://lesson1"

            # Execute search
            system.tool_manager.execute_tool(
                "search_course_content",
                query="What is Python?"
            )

            # Check sources
            sources = system.tool_manager.get_last_sources()
            assert len(sources) > 0
            assert "Python Course - Lesson 1" in sources


class TestRAGSystemErrorHandling:
    """Test error handling in RAG system"""

    def test_query_handles_ai_generator_exception(self, rag_system):
        """Test that exceptions from AI generator are propagated"""
        # Setup
        rag_system.mock_ai_generator.generate_response.side_effect = Exception("API Error")
        rag_system.mock_session_manager.get_conversation_history.return_value = None

        # Execute and verify exception is raised
        with pytest.raises(Exception) as exc_info:
            rag_system.query("Test query")

        assert "API Error" in str(exc_info.value)

    def test_query_handles_empty_sources(self, rag_system):
        """Test that query handles empty sources gracefully"""
        # Setup
        rag_system.mock_ai_generator.generate_response.return_value = "Answer"
        rag_system.mock_session_manager.get_conversation_history.return_value = None
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        rag_system.tool_manager.get_last_source_links = Mock(return_value=[])
        rag_system.tool_manager.reset_sources = Mock()

        # Execute
        answer, sources, links = rag_system.query("What is Python?")

        # Verify
        assert answer == "Answer"
        assert sources == []
        assert links == []
