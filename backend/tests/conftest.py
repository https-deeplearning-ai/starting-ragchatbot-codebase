"""
Pytest configuration and shared fixtures for RAG Chatbot tests
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_course():
    """Sample course with lessons"""
    return Course(
        title="Test Course: Introduction to RAG",
        instructor="Test Instructor",
        link="https://example.com/course",
        lessons=[
            Lesson(lesson_number=0, title="Introduction", link="https://example.com/lesson0"),
            Lesson(lesson_number=1, title="Getting Started", link="https://example.com/lesson1"),
            Lesson(lesson_number=2, title="Advanced Topics", link="https://example.com/lesson2"),
        ]
    )


@pytest.fixture
def sample_course_chunks():
    """Sample course chunks with metadata"""
    return [
        {
            "content": "RAG stands for Retrieval-Augmented Generation. It combines retrieval with generation.",
            "metadata": {
                "course_title": "Test Course: Introduction to RAG",
                "lesson_number": 0,
                "chunk_index": 0,
                "course_link": "https://example.com/course",
                "lesson_link": "https://example.com/lesson0"
            }
        },
        {
            "content": "Vector databases store embeddings for semantic search capabilities.",
            "metadata": {
                "course_title": "Test Course: Introduction to RAG",
                "lesson_number": 1,
                "chunk_index": 0,
                "course_link": "https://example.com/course",
                "lesson_link": "https://example.com/lesson1"
            }
        },
        {
            "content": "Claude can use tools to search course content and provide accurate answers.",
            "metadata": {
                "course_title": "Test Course: Introduction to RAG",
                "lesson_number": 2,
                "chunk_index": 0,
                "course_link": "https://example.com/course",
                "lesson_link": "https://example.com/lesson2"
            }
        }
    ]


@pytest.fixture
def sample_search_results(sample_course_chunks):
    """Sample successful search results"""
    documents = [chunk["content"] for chunk in sample_course_chunks]
    metadata = [chunk["metadata"] for chunk in sample_course_chunks]
    distances = [0.1, 0.2, 0.3]

    return SearchResults(
        documents=documents,
        metadata=metadata,
        distances=distances,
        error=None
    )


@pytest.fixture
def empty_search_results():
    """Empty search results (no matches)"""
    return SearchResults.empty("No results found")


@pytest.fixture
def error_search_results():
    """Search results with error"""
    return SearchResults.empty("Database connection failed")


# ============================================================================
# Mock VectorStore Fixtures
# ============================================================================

@pytest.fixture
def mock_vector_store(sample_search_results):
    """Mock VectorStore that returns sample results"""
    mock = Mock()
    mock.search.return_value = sample_search_results
    return mock


@pytest.fixture
def mock_vector_store_empty(empty_search_results):
    """Mock VectorStore that returns empty results"""
    mock = Mock()
    mock.search.return_value = empty_search_results
    return mock


@pytest.fixture
def mock_vector_store_error(error_search_results):
    """Mock VectorStore that returns error"""
    mock = Mock()
    mock.search.return_value = error_search_results
    return mock


@pytest.fixture
def mock_vector_store_exception():
    """Mock VectorStore that raises exception"""
    mock = Mock()
    mock.search.side_effect = Exception("ChromaDB connection lost")
    return mock


# ============================================================================
# Mock Anthropic Client Fixtures
# ============================================================================

@pytest.fixture
def mock_anthropic_client_direct():
    """Mock Anthropic client that returns direct text response (no tools)"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a direct answer without using tools.")]
    mock_response.stop_reason = "end_turn"
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_anthropic_client_tool_use():
    """Mock Anthropic client that returns tool_use response"""
    mock_client = Mock()

    # First response with tool_use
    first_response = Mock()
    tool_use_block = Mock()
    tool_use_block.type = "tool_use"
    tool_use_block.id = "toolu_123"
    tool_use_block.name = "search_course_content"
    tool_use_block.input = {"query": "What is RAG?"}
    first_response.content = [tool_use_block]
    first_response.stop_reason = "tool_use"

    # Second response after tool execution
    second_response = Mock()
    second_response.content = [Mock(text="RAG stands for Retrieval-Augmented Generation.")]
    second_response.stop_reason = "end_turn"

    mock_client.messages.create.side_effect = [first_response, second_response]
    return mock_client


@pytest.fixture
def mock_anthropic_client_api_error():
    """Mock Anthropic client that raises API error"""
    mock_client = Mock()
    mock_client.messages.create.side_effect = Exception("API connection timeout")
    return mock_client


@pytest.fixture
def mock_anthropic_client_second_call_fails():
    """Mock where first call succeeds but second call fails"""
    mock_client = Mock()

    # First response succeeds with tool_use
    first_response = Mock()
    tool_use_block = Mock()
    tool_use_block.type = "tool_use"
    tool_use_block.id = "toolu_123"
    tool_use_block.name = "search_course_content"
    tool_use_block.input = {"query": "What is RAG?"}
    first_response.content = [tool_use_block]
    first_response.stop_reason = "tool_use"

    # Second call raises exception
    mock_client.messages.create.side_effect = [
        first_response,
        Exception("Second API call failed")
    ]
    return mock_client


@pytest.fixture
def mock_anthropic_client_two_sequential_tool_calls():
    """Mock Anthropic client for two sequential tool calls"""
    mock_client = Mock()

    # Round 1: First tool_use
    round1_response = Mock()
    tool_use_1 = Mock()
    tool_use_1.type = "tool_use"
    tool_use_1.id = "toolu_round1"
    tool_use_1.name = "search_course_content"
    tool_use_1.input = {"query": "MCP course outline"}
    round1_response.content = [tool_use_1]
    round1_response.stop_reason = "tool_use"

    # Round 2: Second tool_use
    round2_response = Mock()
    tool_use_2 = Mock()
    tool_use_2.type = "tool_use"
    tool_use_2.id = "toolu_round2"
    tool_use_2.name = "search_course_content"
    tool_use_2.input = {"query": "context windows", "course_name": "Context"}
    round2_response.content = [tool_use_2]
    round2_response.stop_reason = "tool_use"

    # Final: Text response after seeing both tool results
    final_response = Mock()
    final_response.content = [Mock(text="Based on the searches, both courses cover context window management.")]
    final_response.stop_reason = "end_turn"

    mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]
    return mock_client


@pytest.fixture
def mock_anthropic_client_one_tool_then_text():
    """Mock Anthropic client for single tool call followed by direct text"""
    mock_client = Mock()

    # Round 1: Tool use
    round1_response = Mock()
    tool_use_1 = Mock()
    tool_use_1.type = "tool_use"
    tool_use_1.id = "toolu_single"
    tool_use_1.name = "search_course_content"
    tool_use_1.input = {"query": "What is RAG?"}
    round1_response.content = [tool_use_1]
    round1_response.stop_reason = "tool_use"

    # Round 2: Direct text (no more tools needed)
    round2_response = Mock()
    round2_response.content = [Mock(text="RAG stands for Retrieval-Augmented Generation.")]
    round2_response.stop_reason = "end_turn"

    mock_client.messages.create.side_effect = [round1_response, round2_response]
    return mock_client


# ============================================================================
# Mock ToolManager Fixtures
# ============================================================================

@pytest.fixture
def mock_tool_manager_success():
    """Mock ToolManager that executes tools successfully"""
    mock = Mock()
    mock.execute_tool.return_value = "[Test Course] RAG stands for Retrieval-Augmented Generation."
    mock.get_last_sources.return_value = [
        {"text": "Test Course - Lesson 0", "url": "https://example.com/lesson0"}
    ]
    mock.reset_sources.return_value = None
    return mock


@pytest.fixture
def mock_tool_manager_exception():
    """Mock ToolManager that raises exception during execution"""
    mock = Mock()
    mock.execute_tool.side_effect = Exception("Tool execution failed")
    mock.get_last_sources.return_value = []
    return mock


@pytest.fixture
def mock_tool_manager_two_searches():
    """Mock ToolManager that tracks multiple search executions"""
    mock = Mock()

    # Return different results for each search
    mock.execute_tool.side_effect = [
        "[MCP Course] Lesson 4: Context Window Management",  # First search
        "[Context Course - Lesson 1] Managing large context windows"  # Second search
    ]

    mock.get_last_sources.return_value = [
        {"text": "MCP Course - Lesson 4", "url": "https://example.com/mcp/lesson4"},
        {"text": "Context Course - Lesson 1", "url": "https://example.com/context/lesson1"}
    ]

    mock.reset_sources.return_value = None
    return mock


# ============================================================================
# Mock SessionManager Fixtures
# ============================================================================

@pytest.fixture
def mock_session_manager():
    """Mock SessionManager"""
    mock = Mock()
    mock.get_conversation_history.return_value = None  # No history
    mock.update_conversation.return_value = None
    return mock


@pytest.fixture
def mock_session_manager_with_history():
    """Mock SessionManager with conversation history"""
    mock = Mock()
    mock.get_conversation_history.return_value = "User: What is RAG?\nAssistant: RAG stands for Retrieval-Augmented Generation."
    mock.update_conversation.return_value = None
    return mock


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def temp_chroma_db(tmp_path):
    """Temporary ChromaDB for integration tests"""
    db_path = tmp_path / "test_chroma_db"
    db_path.mkdir()
    return str(db_path)


@pytest.fixture
def api_key_env(monkeypatch):
    """Set test API key in environment"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-123")


@pytest.fixture
def mock_config():
    """Mock Config object for RAGSystem initialization"""
    mock = Mock()
    mock.CHUNK_SIZE = 800
    mock.CHUNK_OVERLAP = 100
    mock.CHROMA_PATH = "./test_chroma_db"
    mock.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    mock.MAX_RESULTS = 5
    mock.ANTHROPIC_API_KEY = "sk-ant-test-key-123"
    mock.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    mock.MAX_HISTORY = 2
    return mock


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests that interact with external services")
