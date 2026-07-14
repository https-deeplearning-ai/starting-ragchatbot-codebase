"""Shared fixtures for RAG backend tests."""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel

# Ensure backend/ is on sys.path so imports like `from search_tools import ...` work
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from vector_store import SearchResults  # noqa: E402


# ---------------------------------------------------------------------------
# Unit-test fixtures (search tools / AI generator)
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_search_results():
    """Non-empty SearchResults with course/lesson metadata."""
    return SearchResults(
        documents=["RAG combines retrieval with generation for grounded answers."],
        metadata=[{
            "course_title": "Advanced Retrieval for AI with Chroma",
            "lesson_number": 1,
        }],
        distances=[0.12],
    )


@pytest.fixture
def empty_search_results():
    """Empty SearchResults with no error."""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """SearchResults carrying an error message."""
    return SearchResults.empty("Search error: n_results must be a positive integer")


@pytest.fixture
def mock_vector_store():
    """MagicMock stand-in for VectorStore."""
    store = MagicMock()
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    return store


@pytest.fixture
def search_course_content_tool_def():
    """Minimal Anthropic tool definition for search_course_content."""
    return {
        "name": "search_course_content",
        "description": "Search course materials",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "course_name": {"type": "string"},
                "lesson_number": {"type": "integer"},
            },
            "required": ["query"],
        },
    }


def make_text_block(text: str):
    """Create a mock Anthropic text content block."""
    return SimpleNamespace(type="text", text=text)


def make_tool_use_block(
    name: str = "search_course_content",
    tool_input: dict | None = None,
    tool_id: str = "toolu_123",
):
    """Create a mock Anthropic tool_use content block."""
    return SimpleNamespace(
        type="tool_use",
        id=tool_id,
        name=name,
        input=tool_input or {"query": "What is RAG?", "course_name": "Chroma"},
    )


def make_api_response(content, stop_reason: str = "end_turn"):
    """Create a mock Anthropic messages.create response."""
    return SimpleNamespace(content=content, stop_reason=stop_reason)


# ---------------------------------------------------------------------------
# API-test fixtures (avoid importing app.py which mounts missing static files)
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_query_request():
    """Typical POST /api/query body."""
    return {
        "query": "What is RAG?",
        "session_id": None,
    }


@pytest.fixture
def sample_query_response_data():
    """Default values returned by a mocked RAGSystem.query."""
    return {
        "answer": "RAG retrieves relevant documents then generates grounded answers.",
        "sources": ["Advanced Retrieval for AI with Chroma - Lesson 1"],
        "session_id": "session-abc-123",
    }


@pytest.fixture
def sample_course_analytics():
    """Default values returned by a mocked RAGSystem.get_course_analytics."""
    return {
        "total_courses": 2,
        "course_titles": [
            "Advanced Retrieval for AI with Chroma",
            "MCP: Build Rich-Context AI Apps with Anthropic",
        ],
    }


@pytest.fixture
def mock_rag_system(sample_query_response_data, sample_course_analytics):
    """Mocked RAGSystem used by the test FastAPI app."""
    rag = MagicMock()
    rag.query.return_value = (
        sample_query_response_data["answer"],
        sample_query_response_data["sources"],
    )
    rag.session_manager.create_session.return_value = sample_query_response_data[
        "session_id"
    ]
    rag.get_course_analytics.return_value = sample_course_analytics
    return rag


def create_test_app(rag_system) -> FastAPI:
    """
    Build a FastAPI app with the same API routes as backend/app.py,
    without mounting StaticFiles (which requires ../frontend at import time).
    """

    app = FastAPI(title="Course Materials RAG System (test)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_chat_session(session_id: str):
        rag_system.session_manager.clear_session(session_id)
        return {"status": "success"}

    @app.get("/")
    async def root():
        """Lightweight stand-in for the static frontend mount used in production."""
        return {"message": "Course Materials RAG System"}

    return app


@pytest.fixture
def test_app(mock_rag_system):
    """FastAPI application wired to a mocked RAG system (no static mount)."""
    return create_test_app(mock_rag_system)


@pytest.fixture
def client(test_app):
    """Synchronous TestClient for API endpoint tests."""
    return TestClient(test_app)
