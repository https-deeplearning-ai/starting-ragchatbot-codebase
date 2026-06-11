import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional

from models import SourceItem


# ---------------------------------------------------------------------------
# Shared request/response models (mirrors app.py, without static-file mount)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------

def build_test_app(rag) -> FastAPI:
    """Return a minimal FastAPI app wired to *rag* — no static-file mount."""
    app = FastAPI()

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag.session_manager.create_session()
            answer, sources = rag.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag():
    """Pre-configured RAGSystem mock with sensible defaults."""
    rag = MagicMock()
    rag.session_manager.create_session.return_value = "sess-auto"
    rag.query.return_value = ("Default answer.", [])
    rag.get_course_analytics.return_value = {"total_courses": 0, "course_titles": []}
    return rag


@pytest.fixture
def client(mock_rag):
    """TestClient backed by a fresh test app for each test."""
    app = build_test_app(mock_rag)
    with TestClient(app) as c:
        yield c
