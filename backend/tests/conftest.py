"""
Pytest configuration and shared fixtures for RAG system tests.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import List, Dict, Any
from datetime import datetime


# =============================================================================
# Mock Data Fixtures
# =============================================================================

@pytest.fixture
def sample_course_data() -> Dict[str, Any]:
    """Sample course data for testing."""
    return {
        "course_id": "course-001",
        "title": "Introduction to Python",
        "description": "Learn Python programming basics",
        "lessons": [
            {
                "lesson_id": "lesson-001",
                "title": "Getting Started",
                "content": "Welcome to Python programming.",
                "lesson_number": 1
            },
            {
                "lesson_id": "lesson-002",
                "title": "Variables and Types",
                "content": "Learn about variables and data types in Python.",
                "lesson_number": 2
            }
        ]
    }


@pytest.fixture
def sample_course_chunks() -> List[Dict[str, Any]]:
    """Sample course chunks for testing vector store operations."""
    return [
        {
            "chunk_id": "chunk-001",
            "course_id": "course-001",
            "course_title": "Introduction to Python",
            "lesson_number": 1,
            "content": "Welcome to Python programming.",
            "content_hash": "abc123"
        },
        {
            "chunk_id": "chunk-002",
            "course_id": "course-001",
            "course_title": "Introduction to Python",
            "lesson_number": 2,
            "content": "Learn about variables and data types in Python.",
            "content_hash": "def456"
        }
    ]


@pytest.fixture
def sample_search_results() -> Dict[str, Any]:
    """Sample search results from vector store."""
    return {
        "documents": [
            "Welcome to Python programming.",
            "Learn about variables and data types in Python."
        ],
        "metadatas": [
            {
                "course_id": "course-001",
                "course_title": "Introduction to Python",
                "lesson_number": 1,
                "chunk_id": "chunk-001"
            },
            {
                "course_id": "course-001",
                "course_title": "Introduction to Python",
                "lesson_number": 2,
                "chunk_id": "chunk-002"
            }
        ],
        "ids": [["chunk-001"], ["chunk-002"]],
        "distances": [[0.1], [0.2]]
    }


@pytest.fixture
def sample_query_request() -> Dict[str, Any]:
    """Sample query request payload."""
    return {
        "query": "What is Python?",
        "session_id": "test-session-001"
    }


@pytest.fixture
def sample_query_response() -> Dict[str, Any]:
    """Sample query response payload."""
    return {
        "answer": "Python is a high-level programming language.",
        "sources": ["Introduction to Python|Lesson 1"],
        "session_id": "test-session-001"
    }


@pytest.fixture
def sample_course_stats() -> Dict[str, Any]:
    """Sample course statistics response."""
    return {
        "total_courses": 2,
        "course_titles": ["Introduction to Python", "Advanced Python"]
    }


# =============================================================================
# Mock Component Fixtures
# =============================================================================

@pytest.fixture
def mock_config():
    """Mock configuration object."""
    config = MagicMock()
    config.CHUNK_SIZE = 1000
    config.CHUNK_OVERLAP = 200
    config.CHROMA_PATH = "./chroma_db"
    config.EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    config.MAX_RESULTS = 5
    config.MINMAX_API_KEY = "test-api-key"
    config.MINMAX_BASE_URL = "https://api.minimax.chat/v1"
    config.MINMAX_MODEL = "abab6.5s-chat"
    config.MAX_HISTORY = 10
    return config


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock = MagicMock()
    mock.search = MagicMock(return_value=MagicMock(
        documents=["Sample content"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        is_empty=False
    ))
    mock.get_course_count = MagicMock(return_value=5)
    mock.get_existing_course_titles = MagicMock(return_value=["Test Course"])
    mock.add_course_metadata = MagicMock()
    mock.add_course_content = MagicMock()
    mock.get_course_link = MagicMock(return_value="https://example.com/course")
    mock.get_lesson_link = MagicMock(return_value="https://example.com/lesson")
    return mock


@pytest.fixture
def mock_ai_generator():
    """Mock AI generator for testing."""
    mock = MagicMock()
    mock.generate_response = MagicMock(return_value="This is a test response.")
    return mock


@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing."""
    mock = MagicMock()
    mock.create_session = MagicMock(return_value="test-session-001")
    mock.get_conversation_history = MagicMock(return_value=[])
    mock.add_exchange = MagicMock()
    mock.clear_session = MagicMock()
    return mock


@pytest.fixture
def mock_document_processor():
    """Mock document processor for testing."""
    mock = MagicMock()
    mock.process_course_document = MagicMock(return_value=(
        MagicMock(
            course_id="test-course",
            title="Test Course",
            description="Test description"
        ),
        [MagicMock(chunk_id="chunk-1"), MagicMock(chunk_id="chunk-2")]
    ))
    return mock


# =============================================================================
# FastAPI Test Client Fixtures
# =============================================================================

@pytest.fixture
def mock_rag_system(mock_config, mock_vector_store, mock_ai_generator, mock_session_manager):
    """Create a mock RAG system with all components mocked."""
    with patch('app.RAGSystem') as MockRAG:
        mock_rag = MagicMock()
        mock_rag.query = MagicMock(return_value=(
            "Test answer",
            ["Source 1"]
        ))
        mock_rag.get_course_analytics = MagicMock(return_value={
            "total_courses": 1,
            "course_titles": ["Test Course"]
        })
        mock_rag.session_manager = mock_session_manager
        MockRAG.return_value = mock_rag
        yield mock_rag


# =============================================================================
# Async Fixtures
# =============================================================================

@pytest.fixture
def mock_async_search_results():
    """Mock async search results."""
    async def mock_search(query: str, limit: int = 5):
        return MagicMock(
            documents=["Async result"],
            metadata=[{"course_title": "Async Course"}],
            is_empty=False
        )
    return mock_search


# =============================================================================
# Test Helpers
# =============================================================================

def create_mock_search_results(documents: List[str], metadatas: List[Dict]) -> MagicMock:
    """Helper to create mock search results with customizable data."""
    result = MagicMock()
    result.documents = documents
    result.metadata = metadatas
    result.is_empty = len(documents) == 0
    return result


def create_mock_config(**kwargs) -> MagicMock:
    """Helper to create mock config with custom values."""
    config = MagicMock()
    config.CHUNK_SIZE = kwargs.get("chunk_size", 1000)
    config.CHUNK_OVERLAP = kwargs.get("chunk_overlap", 200)
    config.CHROMA_PATH = kwargs.get("chroma_path", "./chroma_db")
    config.EMBEDDING_MODEL = kwargs.get("embedding_model", "test-model")
    config.MAX_RESULTS = kwargs.get("max_results", 5)
    config.MINMAX_API_KEY = kwargs.get("minmax_api_key", "test-key")
    config.MINMAX_BASE_URL = kwargs.get("minmax_base_url", "https://api.test.com")
    config.MINMAX_MODEL = kwargs.get("minmax_model", "test-model")
    config.MAX_HISTORY = kwargs.get("max_history", 10)
    return config