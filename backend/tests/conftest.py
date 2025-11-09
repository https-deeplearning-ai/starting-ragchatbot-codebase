"""Pytest fixtures for RAG system tests"""
import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, ToolManager
from ai_generator import AIGenerator
from models import Course, Lesson, CourseChunk


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore for testing"""
    store = Mock(spec=VectorStore)
    store.max_results = 5
    return store


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing"""
    return SearchResults(
        documents=[
            "This is content from lesson 1 about Python basics.",
            "This is content from lesson 2 about advanced topics."
        ],
        metadata=[
            {"course_title": "Python Course", "lesson_number": 1},
            {"course_title": "Python Course", "lesson_number": 2}
        ],
        distances=[0.1, 0.2]
    )


@pytest.fixture
def empty_search_results():
    """Create empty search results for testing"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )


@pytest.fixture
def error_search_results():
    """Create error search results for testing"""
    return SearchResults.empty("Search error: Database connection failed")


@pytest.fixture
def course_search_tool(mock_vector_store):
    """Create a CourseSearchTool with mocked vector store"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def tool_manager():
    """Create a ToolManager for testing"""
    return ToolManager()


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client for testing"""
    client = Mock()
    return client


@pytest.fixture
def ai_generator(mock_anthropic_client):
    """Create an AIGenerator with mocked client"""
    generator = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
    generator.client = mock_anthropic_client
    return generator


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    lessons = [
        Lesson(
            lesson_number=1,
            title="Introduction to Python",
            lesson_link="https://example.com/lesson1",
            content="Python basics content"
        ),
        Lesson(
            lesson_number=2,
            title="Advanced Python",
            lesson_link="https://example.com/lesson2",
            content="Advanced Python content"
        )
    ]
    return Course(
        title="Python Course",
        instructor="John Doe",
        course_link="https://example.com/course",
        lessons=lessons
    )


@pytest.fixture
def sample_chunks():
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            course_title="Python Course",
            lesson_number=1,
            content="This is content from lesson 1 about Python basics.",
            chunk_index=0
        ),
        CourseChunk(
            course_title="Python Course",
            lesson_number=2,
            content="This is content from lesson 2 about advanced topics.",
            chunk_index=1
        )
    ]


# ==================== FastAPI Testing Fixtures ====================

@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for API testing"""
    rag_system = Mock()

    # Mock session manager
    rag_system.session_manager = Mock()
    rag_system.session_manager.create_session.return_value = "test_session_id"

    # Mock query method - returns (answer, sources, source_links)
    rag_system.query.return_value = (
        "This is a test answer about Python basics.",
        ["Python Course - Lesson 1", "Python Course - Lesson 2"],
        ["https://example.com/lesson1", "https://example.com/lesson2"]
    )

    # Mock get_course_analytics method
    rag_system.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Course", "JavaScript Course"]
    }

    # Mock add_course_folder method
    rag_system.add_course_folder.return_value = (2, 150)

    return rag_system


@pytest.fixture
def test_app(mock_rag_system):
    """
    Create a test FastAPI app without static file mounting.

    This avoids the issue where the app tries to mount ../frontend
    which doesn't exist in the test environment.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    # Create test app
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Add middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        source_links: List[Optional[str]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Define endpoints inline
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources, source_links = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                source_links=source_links,
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

    @app.get("/")
    async def root():
        """Root endpoint for health check"""
        return {"status": "ok", "message": "RAG API is running"}

    return app


@pytest.fixture
async def async_client(test_app):
    """Create an async HTTP client for testing FastAPI endpoints"""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as client:
        yield client
