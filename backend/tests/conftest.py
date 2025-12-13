"""Shared pytest fixtures for testing the RAG system"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from tests.fixtures.sample_data import (
    SAMPLE_COURSE_METADATA,
    SAMPLE_COURSE_METADATA_2,
    SAMPLE_SEARCH_RESULTS_SUCCESS,
    SAMPLE_SEARCH_RESULTS_EMPTY,
    SAMPLE_SEARCH_RESULTS_WITH_ERROR,
    SAMPLE_ANTHROPIC_TEXT_RESPONSE,
    SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE,
    SAMPLE_ANTHROPIC_FINAL_RESPONSE
)


@pytest.fixture
def sample_course_metadata():
    """Sample course catalog metadata"""
    return SAMPLE_COURSE_METADATA.copy()


@pytest.fixture
def sample_course_metadata_2():
    """Second sample course metadata"""
    return SAMPLE_COURSE_METADATA_2.copy()


@pytest.fixture
def sample_search_results_success():
    """Sample successful SearchResults"""
    return SAMPLE_SEARCH_RESULTS_SUCCESS


@pytest.fixture
def sample_search_results_empty():
    """Sample empty SearchResults"""
    return SAMPLE_SEARCH_RESULTS_EMPTY


@pytest.fixture
def sample_search_results_with_error():
    """Sample SearchResults with error"""
    return SAMPLE_SEARCH_RESULTS_WITH_ERROR


@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection with controllable behavior"""
    mock_collection = Mock()

    # Default behavior: return empty results
    mock_collection.query.return_value = {
        'documents': [[]],
        'metadatas': [[]],
        'distances': [[]]
    }

    mock_collection.get.return_value = {
        'ids': [],
        'documents': [],
        'metadatas': []
    }

    return mock_collection


@pytest.fixture
def mock_vector_store(mock_chroma_collection):
    """Mock VectorStore with controllable search results"""
    from vector_store import VectorStore

    with patch('vector_store.chromadb.PersistentClient'):
        # Create VectorStore with default max_results=5
        store = VectorStore(
            chroma_path="./test_chroma",
            embedding_model="all-MiniLM-L6-v2",
            max_results=5
        )

        # Replace collections with mocks
        store.course_catalog = mock_chroma_collection
        store.course_content = mock_chroma_collection

        return store


@pytest.fixture
def mock_vector_store_with_zero_max_results(mock_chroma_collection):
    """Mock VectorStore with max_results=0 to test the bug"""
    from vector_store import VectorStore

    with patch('vector_store.chromadb.PersistentClient'):
        # Create VectorStore with max_results=0 (the bug)
        store = VectorStore(
            chroma_path="./test_chroma",
            embedding_model="all-MiniLM-L6-v2",
            max_results=0
        )

        # Replace collections with mocks
        store.course_catalog = mock_chroma_collection
        store.course_content = mock_chroma_collection

        return store


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    mock_client = Mock()
    mock_messages = Mock()
    mock_client.messages = mock_messages

    # Default: return simple text response
    mock_messages.create.return_value = SAMPLE_ANTHROPIC_TEXT_RESPONSE

    return mock_client


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager"""
    from search_tools import ToolManager

    manager = ToolManager()

    # Mock execute_tool to return canned responses
    original_execute = manager.execute_tool

    def mock_execute(tool_name, **kwargs):
        if tool_name == "search_course_content":
            return "[MCP: Build Rich-Context AI Apps with Anthropic - Lesson 1]\nMCP stands for Model Context Protocol."
        elif tool_name == "get_course_outline":
            return "Course: MCP\nLink: https://example.com/mcp\n\nLessons:\nLesson 1: Introduction"
        return original_execute(tool_name, **kwargs)

    manager.execute_tool = mock_execute

    return manager


@pytest.fixture(params=[0, 1, 5])
def max_results_parametrized(request):
    """Parametrized fixture for testing different max_results values"""
    return request.param


@pytest.fixture
def mock_config():
    """Mock Config object"""
    from dataclasses import dataclass

    @dataclass
    class TestConfig:
        ANTHROPIC_API_KEY: str = "test-api-key"
        ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
        EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
        CHUNK_SIZE: int = 800
        CHUNK_OVERLAP: int = 100
        MAX_RESULTS: int = 5
        MAX_HISTORY: int = 2
        CHROMA_PATH: str = "./test_chroma_db"

    return TestConfig()


@pytest.fixture
def mock_config_with_zero_max_results():
    """Mock Config with MAX_RESULTS=0 (the bug)"""
    from dataclasses import dataclass

    @dataclass
    class TestConfig:
        ANTHROPIC_API_KEY: str = "test-api-key"
        ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
        EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
        CHUNK_SIZE: int = 800
        CHUNK_OVERLAP: int = 100
        MAX_RESULTS: int = 0  # The bug!
        MAX_HISTORY: int = 2
        CHROMA_PATH: str = "./test_chroma_db"

    return TestConfig()


# ============================================================================
# API Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for API tests"""
    mock_manager = Mock()
    mock_manager.create_session.return_value = "test-session-123"
    mock_manager.get_conversation_history.return_value = []
    mock_manager.add_exchange.return_value = None
    return mock_manager


@pytest.fixture
def mock_rag_system(mock_session_manager):
    """Mock RAGSystem for API endpoint tests"""
    mock_rag = Mock()

    # Mock session_manager
    mock_rag.session_manager = mock_session_manager

    # Mock query method to return (answer, sources)
    mock_rag.query.return_value = (
        "MCP stands for Model Context Protocol.",
        [
            {"text": "MCP: Build Rich-Context AI Apps - Lesson 1", "url": "https://example.com/mcp/lesson1"},
            {"text": "Advanced MCP Topics - Lesson 2", "url": "https://example.com/mcp/lesson2"}
        ]
    )

    # Mock get_course_analytics
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": [
            "MCP: Build Rich-Context AI Apps with Anthropic",
            "Advanced Retrieval for AI with Chroma"
        ]
    }

    return mock_rag


@pytest.fixture
def test_app(mock_rag_system):
    """FastAPI test app with API endpoints only (no static file mounting)"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    # Define Pydantic models inline
    class QueryRequest(BaseModel):
        """Request model for course queries"""
        query: str
        session_id: Optional[str] = None

    class Source(BaseModel):
        """Single source citation with optional link"""
        text: str
        url: Optional[str] = None

    class QueryResponse(BaseModel):
        """Response model for course queries"""
        answer: str
        sources: List[Source]
        session_id: str

    class CourseStats(BaseModel):
        """Response model for course statistics"""
        total_courses: int
        course_titles: List[str]

    # Create test app
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Define API endpoints using mock_rag_system
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            # Create session if not provided
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            # Process query using RAG system
            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def test_client(test_app):
    """FastAPI TestClient for making API requests"""
    from fastapi.testclient import TestClient
    return TestClient(test_app)
