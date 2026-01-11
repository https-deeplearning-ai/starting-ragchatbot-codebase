"""Shared fixtures for RAG system API tests."""

import pytest
from unittest.mock import Mock, MagicMock
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from httpx import AsyncClient, ASGITransport

import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# --- Pydantic models (duplicated to avoid import issues with static files) ---

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# --- Mock fixtures ---

@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing."""
    manager = Mock()
    manager.create_session.return_value = "test_session_123"
    manager.get_conversation_history.return_value = None
    manager.add_exchange = Mock()
    manager.clear_session = Mock()
    return manager


@pytest.fixture
def mock_rag_system(mock_session_manager):
    """Mock RAG system with configurable responses."""
    rag = Mock()
    rag.session_manager = mock_session_manager
    rag.query.return_value = (
        "This is a test response about the course material.",
        [{"title": "Test Course", "url": "https://example.com/course"}]
    )
    rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["Course A", "Course B", "Course C"]
    }
    return rag


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app without static file mounting."""
    from fastapi import HTTPException

    app = FastAPI(title="Test Course Materials RAG System")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store mock in app state for access in endpoints
    app.state.rag_system = mock_rag_system

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            rag = app.state.rag_system
            session_id = request.session_id
            if not session_id:
                session_id = rag.session_manager.create_session()

            answer, sources = rag.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/session/new")
    async def new_session(request: Optional[dict] = None):
        rag = app.state.rag_system
        if request and request.get("session_id"):
            rag.session_manager.clear_session(request["session_id"])
        new_session_id = rag.session_manager.create_session()
        return {"session_id": new_session_id}

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            rag = app.state.rag_system
            analytics = rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"status": "ok", "message": "RAG System API"}

    return app


@pytest.fixture
async def client(test_app):
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --- Test data fixtures ---

@pytest.fixture
def sample_query_request():
    """Sample query request data."""
    return {"query": "What is machine learning?"}


@pytest.fixture
def sample_query_with_session():
    """Sample query request with session ID."""
    return {
        "query": "Tell me more about neural networks",
        "session_id": "existing_session_456"
    }


@pytest.fixture
def sample_course_titles():
    """Sample course titles for testing."""
    return [
        "Introduction to Machine Learning",
        "Deep Learning Fundamentals",
        "Natural Language Processing"
    ]
