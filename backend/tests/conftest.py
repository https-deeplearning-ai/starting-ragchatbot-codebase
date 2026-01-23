"""Shared fixtures and mocks for RAG chatbot tests"""

import os
import sys
from unittest.mock import Mock

import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vector_store import SearchResults


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Create a mock configuration object for testing"""
    config = Mock()
    config.MAX_RESULTS = 5
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.CHROMA_PATH = "/tmp/test_chroma"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.MAX_HISTORY = 2
    return config


# ============================================================================
# RAG System Fixtures
# ============================================================================

@pytest.fixture
def mock_rag_system():
    """Create a mock RAGSystem for API testing"""
    rag = Mock()

    # Mock query method
    rag.query.return_value = (
        "This is a test answer about the course material.",
        [{"text": "ML Fundamentals - Lesson 1", "link": "https://example.com/lesson1"}]
    )

    # Mock session manager
    rag.session_manager = Mock()
    rag.session_manager.create_session.return_value = "test-session-123"
    rag.session_manager.clear_session.return_value = None

    # Mock get_course_analytics
    rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["ML Fundamentals", "Python Basics", "Data Science 101"]
    }

    return rag


@pytest.fixture
def mock_rag_system_empty():
    """Create a mock RAGSystem with no courses"""
    rag = Mock()

    rag.query.return_value = (
        "I don't have any course materials to search.",
        []
    )

    rag.session_manager = Mock()
    rag.session_manager.create_session.return_value = "empty-session-456"

    rag.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": []
    }

    return rag


@pytest.fixture
def mock_rag_system_error():
    """Create a mock RAGSystem that raises errors"""
    rag = Mock()

    rag.query.side_effect = Exception("Database connection failed")

    rag.session_manager = Mock()
    rag.session_manager.create_session.return_value = "error-session-789"
    rag.session_manager.clear_session.side_effect = Exception("Session not found")

    rag.get_course_analytics.side_effect = Exception("Analytics unavailable")

    return rag


# ============================================================================
# Session Manager Fixtures
# ============================================================================

@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager"""
    manager = Mock()
    manager.create_session.return_value = "session-abc-123"
    manager.get_conversation_history.return_value = None
    manager.add_exchange.return_value = None
    manager.clear_session.return_value = None
    return manager


@pytest.fixture
def mock_session_manager_with_history():
    """Create a mock SessionManager with existing conversation history"""
    manager = Mock()
    manager.create_session.return_value = "session-with-history"
    manager.get_conversation_history.return_value = [
        {"role": "user", "content": "What is machine learning?"},
        {"role": "assistant", "content": "Machine learning is..."}
    ]
    manager.add_exchange.return_value = None
    return manager


@pytest.fixture
def sample_search_results():
    """Create sample successful search results"""
    return SearchResults(
        documents=["Lesson content about machine learning basics"],
        metadata=[
            {"course_title": "ML Fundamentals", "lesson_number": 1, "chunk_index": 0}
        ],
        distances=[0.15],
    )


@pytest.fixture
def empty_search_results():
    """Create empty search results"""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """Create search results with error"""
    return SearchResults.empty("No course found matching 'NonExistent'")


@pytest.fixture
def mock_vector_store(sample_search_results):
    """Create a mock VectorStore with working configuration"""
    store = Mock()
    store.max_results = 5
    store.search = Mock(return_value=sample_search_results)
    store.get_lesson_link = Mock(return_value="https://example.com/lesson1")
    return store


@pytest.fixture
def mock_vector_store_zero_results():
    """Create a mock VectorStore simulating MAX_RESULTS=0 bug"""
    store = Mock()
    store.max_results = 0
    store.search = Mock(
        return_value=SearchResults(documents=[], metadata=[], distances=[])
    )
    store.get_lesson_link = Mock(return_value=None)
    return store


@pytest.fixture
def mock_anthropic_response_with_tool_use():
    """Create mock Anthropic response that requests tool use"""
    response = Mock()
    response.stop_reason = "tool_use"

    tool_use_block = Mock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "search_course_content"
    tool_use_block.id = "tool_123"
    tool_use_block.input = {"query": "machine learning"}

    response.content = [tool_use_block]
    return response


@pytest.fixture
def mock_anthropic_response_text():
    """Create mock Anthropic response with text only"""
    response = Mock()
    response.stop_reason = "end_turn"

    text_block = Mock()
    text_block.type = "text"
    text_block.text = "Here is the answer about machine learning."

    response.content = [text_block]
    return response
