"""Shared fixtures for RAG chatbot tests."""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


# ---------------------------------------------------------------------------
# API test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """A fully mocked RAGSystem for API endpoint tests."""
    rag = MagicMock()
    rag.query.return_value = (
        "RAG stands for Retrieval-Augmented Generation.",
        [{"title": "Building RAG Chatbots", "link": "https://example.com/rag"}],
    )
    rag.session_manager.create_session.return_value = "session_1"
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Building RAG Chatbots", "Intro to MCP"],
    }
    return rag


@pytest.fixture
def test_app(mock_rag_system):
    """A lightweight FastAPI app with the same endpoints as app.py,
    but without static-file mounting or startup document loading."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    api = FastAPI()

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceItem(BaseModel):
        title: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str

    class ClearSessionRequest(BaseModel):
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    rag = mock_rag_system

    @api.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag.session_manager.create_session()
            answer, sources = rag.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @api.post("/api/sessions/clear")
    async def clear_session(request: ClearSessionRequest):
        try:
            rag.session_manager.clear_session(request.session_id)
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @api.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return api


@pytest.fixture
def client(test_app):
    """HTTPX TestClient (sync) for the test FastAPI app."""
    from starlette.testclient import TestClient
    return TestClient(test_app)


@dataclass
class MockConfig:
    """Minimal config for testing without .env or real services."""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "test-model"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = "./test_chroma_db"


@pytest.fixture
def mock_config():
    return MockConfig()


@pytest.fixture
def sample_search_results():
    """Realistic search results as returned by VectorStore.search()."""
    return SearchResults(
        documents=[
            "Lesson 1 content: RAG stands for Retrieval-Augmented Generation. It combines retrieval and generation.",
            "Lesson 2 content: Vector databases store embeddings for semantic search.",
        ],
        metadata=[
            {"course_title": "Building RAG Chatbots", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Building RAG Chatbots", "lesson_number": 2, "chunk_index": 3},
        ],
        distances=[0.25, 0.42],
    )


@pytest.fixture
def empty_search_results():
    """Empty search results (no matching documents)."""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """Search results with an error."""
    return SearchResults(documents=[], metadata=[], distances=[], error="Search error: collection is empty")


@pytest.fixture
def sample_course():
    """A sample Course object for testing."""
    return Course(
        title="Building RAG Chatbots",
        course_link="https://example.com/rag-course",
        instructor="Test Instructor",
        lessons=[
            Lesson(lesson_number=1, title="Introduction to RAG", lesson_link="https://example.com/lesson1"),
            Lesson(lesson_number=2, title="Vector Databases", lesson_link="https://example.com/lesson2"),
            Lesson(lesson_number=3, title="Building the Pipeline", lesson_link="https://example.com/lesson3"),
        ],
    )


@pytest.fixture
def mock_vector_store():
    """A fully mocked VectorStore (avoids ChromaDB + embedding model)."""
    store = MagicMock()
    store.search.return_value = SearchResults(
        documents=[
            "RAG combines retrieval with generation for better answers.",
        ],
        metadata=[
            {"course_title": "Building RAG Chatbots", "lesson_number": 1, "chunk_index": 0},
        ],
        distances=[0.3],
    )
    store.get_lesson_link.return_value = "https://example.com/lesson1"
    store.get_course_link.return_value = "https://example.com/rag-course"
    store.get_course_outline.return_value = None  # default: no outline match
    return store
