import os
import sys

# Add the backend directory to the Python path so test files can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
from unittest.mock import MagicMock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional

import pytest
from models import Course, CourseChunk, Lesson
from vector_store import VectorStore


@pytest.fixture
def tmp_chroma_path():
    """Create a temporary directory for ChromaDB during tests.

    ignore_cleanup_errors=True avoids PermissionError on Windows where
    ChromaDB holds file handles open until the process exits.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield tmpdir


@pytest.fixture
def empty_vector_store(tmp_chroma_path):
    """A VectorStore backed by a fresh empty ChromaDB."""
    return VectorStore(
        chroma_path=tmp_chroma_path,
        embedding_model="all-MiniLM-L6-v2",
        max_results=5,
    )


@pytest.fixture
def sample_course():
    return Course(
        title="Introduction to RAG",
        course_link="https://example.com/rag",
        instructor="Test Instructor",
        lessons=[
            Lesson(lesson_number=1, title="What is RAG"),
            Lesson(lesson_number=2, title="Vector Databases"),
        ],
    )


@pytest.fixture
def sample_chunks():
    return [
        CourseChunk(
            content="Lesson 1 content: RAG stands for Retrieval-Augmented Generation. "
            "It combines a retrieval system with a generative language model.",
            course_title="Introduction to RAG",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="Vector databases store embeddings and enable fast similarity search "
            "over large document collections.",
            course_title="Introduction to RAG",
            lesson_number=2,
            chunk_index=1,
        ),
        CourseChunk(
            content="ChromaDB is an open-source vector database well-suited for local development.",
            course_title="Introduction to RAG",
            lesson_number=2,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def populated_vector_store(empty_vector_store, sample_course, sample_chunks):
    """A VectorStore with one test course and three content chunks loaded."""
    empty_vector_store.add_course_metadata(sample_course)
    empty_vector_store.add_course_content(sample_chunks)
    return empty_vector_store


# ---------------------------------------------------------------------------
# API endpoint test infrastructure
# ---------------------------------------------------------------------------

def _build_test_api_app(rag_system):
    """
    Minimal FastAPI app mirroring the routes in app.py with an injected
    rag_system.  Avoids the static-file mount and ChromaDB init that make
    importing app.py directly fail in test environments.
    """
    test_app = FastAPI()

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

    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        rag_system.session_manager.clear_session(session_id)
        return {"status": "cleared"}

    return test_app


@pytest.fixture
def mock_rag_system():
    """A fully-mocked RAGSystem for use in API endpoint tests."""
    rag = MagicMock()
    rag.session_manager.create_session.return_value = "session_1"
    rag.query.return_value = ("Test answer", ["Introduction to RAG - Lesson 1"])
    rag.get_course_analytics.return_value = {
        "total_courses": 1,
        "course_titles": ["Introduction to RAG"],
    }
    return rag


@pytest.fixture
def api_client(mock_rag_system):
    """Starlette TestClient wired to the minimal test API app."""
    app = _build_test_api_app(mock_rag_system)
    return TestClient(app)
