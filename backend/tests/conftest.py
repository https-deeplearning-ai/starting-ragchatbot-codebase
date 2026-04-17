import pytest
from unittest.mock import MagicMock
from vector_store import SearchResults
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Shared sample data
# ---------------------------------------------------------------------------

SAMPLE_CHROMA_RESULTS = {
    "documents": [["Lesson content about Python basics.", "More content here."]],
    "metadatas": [[
        {"course_title": "Python Fundamentals", "lesson_number": 1, "chunk_index": 0},
        {"course_title": "Python Fundamentals", "lesson_number": 2, "chunk_index": 0},
    ]],
    "distances": [[0.12, 0.34]],
}


# ---------------------------------------------------------------------------
# SearchResults fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_search_results():
    """Two-document SearchResults with full metadata."""
    return SearchResults.from_chroma(SAMPLE_CHROMA_RESULTS)


@pytest.fixture
def empty_search_results():
    """Empty SearchResults with no error."""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """SearchResults carrying a ChromaDB error string."""
    return SearchResults.empty(
        "Search error: Number of requested results 5 is greater than number of elements in index 0"
    )


# ---------------------------------------------------------------------------
# VectorStore mock fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vector_store(sample_search_results):
    """
    MagicMock standing in for VectorStore.
    Defaults: .search() returns sample_search_results, .get_lesson_link() returns a URL.
    """
    store = MagicMock()
    store.search.return_value = sample_search_results
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    store.get_course_outline.return_value = None
    return store


# ---------------------------------------------------------------------------
# RAGSystem mock fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """
    MagicMock standing in for RAGSystem.
    Defaults: .query() returns a plain answer with no sources; .get_course_analytics()
    returns two courses; session_manager behaves as expected.
    """
    rag = MagicMock()
    rag.session_manager.create_session.return_value = "auto-session-id"
    rag.query.return_value = ("Test answer.", [])
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Fundamentals", "Data Science Basics"],
    }
    return rag


# ---------------------------------------------------------------------------
# Shared test-app factory (used by test_app.py)
# ---------------------------------------------------------------------------

def build_test_app(rag_system) -> FastAPI:
    """
    Return a minimal FastAPI app that mirrors the real app.py routes but
    skips the StaticFiles mount and RAGSystem startup, so tests can run
    without a frontend directory or a real ChromaDB instance.
    """
    app = FastAPI()

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

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
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
    async def delete_session(session_id: str):
        rag_system.session_manager.clear_session(session_id)
        return {"status": "cleared"}

    return app


# ---------------------------------------------------------------------------
# Anthropic response mock helpers (module-level, importable by test files)
# ---------------------------------------------------------------------------

def make_text_response(text: str):
    """Create a mock Anthropic Message with a single text block and stop_reason=end_turn."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def make_tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str = "tu_abc123"):
    """Create a mock Anthropic Message that requests a tool call."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_use_id
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response
