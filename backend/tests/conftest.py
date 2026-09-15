"""Shared fixtures for the backend diagnostic test suite."""

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ai_generator import AIGenerator
from rag_system import RAGSystem
from search_tools import Source, ToolManager
from vector_store import SearchResults, VectorStore

# ---------------------------------------------------------------------------
# Objective 1 helpers: CourseSearchTool / ToolManager unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vector_store():
    """A fully mocked VectorStore -- no real Chroma, no network, no disk I/O."""
    return MagicMock(spec=VectorStore)


@pytest.fixture
def make_results():
    """Factory for building SearchResults without boilerplate."""

    def _make(documents=None, metadata=None, distances=None, error=None):
        return SearchResults(
            documents=documents or [],
            metadata=metadata or [],
            distances=distances or [],
            error=error,
        )

    return _make


# ---------------------------------------------------------------------------
# Objective 2 helpers: AIGenerator unit tests (Anthropic client mocked)
# ---------------------------------------------------------------------------


@pytest.fixture
def ai_generator():
    """A real AIGenerator with its Anthropic client's create() call mocked out."""
    generator = AIGenerator(api_key="test-key-not-used", model="claude-sonnet-5")
    generator.client.messages.create = MagicMock()
    return generator


@pytest.fixture
def mock_tool_manager():
    return MagicMock(spec=ToolManager)


@pytest.fixture
def text_response():
    """Build a fake Anthropic response whose content is a single text block."""

    def _make(text, stop_reason="end_turn"):
        return SimpleNamespace(
            stop_reason=stop_reason,
            content=[SimpleNamespace(type="text", text=text)],
        )

    return _make


@pytest.fixture
def tool_use_response():
    """
    Build a fake Anthropic response containing one or more tool_use blocks.
    tool_calls: list of {"name": str, "input": dict, "id": optional str}
    """

    def _make(tool_calls, stop_reason="tool_use"):
        blocks = [
            SimpleNamespace(
                type="tool_use",
                name=call["name"],
                input=call["input"],
                id=call.get("id", f"toolu_{i}"),
            )
            for i, call in enumerate(tool_calls)
        ]
        return SimpleNamespace(stop_reason=stop_reason, content=blocks)

    return _make


# ---------------------------------------------------------------------------
# Objective 3 helpers: real VectorStore + real ToolManager, scripted Anthropic
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent.parent
REAL_CHROMA_PATH = str(BACKEND_DIR / "chroma_db")


@dataclass
class _TestConfig:
    """
    Mirrors config.Config but with an absolute CHROMA_PATH, so this works
    regardless of the cwd pytest is invoked from (config.Config's default
    './chroma_db' is relative and assumes cwd == backend/, which is NOT
    true when pytest runs from the repo root per testpaths=['backend/tests']).
    """

    ANTHROPIC_API_KEY: str = "test-key-not-used"
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = REAL_CHROMA_PATH


@pytest.fixture(scope="session")
def rag_system():
    """
    A RAGSystem wired to the REAL, already-populated backend/chroma_db,
    with real VectorStore/ToolManager/CourseSearchTool/CourseOutlineTool.
    Session-scoped because constructing VectorStore loads the sentence-
    transformer embedding model, which is slow. Never make a live Anthropic
    call from this fixture -- see _isolate_rag_system below.
    """
    return RAGSystem(_TestConfig())


@pytest.fixture(autouse=True)
def _isolate_rag_system(request):
    """
    Give every test that uses `rag_system` a clean slate: no leftover
    session history, no leftover tool sources, and a fresh mock in place
    of the real Anthropic client so no live network call ever happens.
    """
    if "rag_system" in request.fixturenames:
        rag = request.getfixturevalue("rag_system")
        rag.session_manager.sessions.clear()
        rag.tool_manager.reset_sources()
        rag.ai_generator.client.messages.create = MagicMock()
    yield


# ---------------------------------------------------------------------------
# Objective 4 helpers: FastAPI endpoint tests
#
# backend/app.py cannot be imported under test: at import time it constructs a
# real RAGSystem (loading the embedding model and Chroma) and mounts
# StaticFiles(directory="../frontend"), a cwd-relative path that does not
# resolve when pytest runs from the repo root. So the endpoints are re-declared
# here, inline, against an injected (mocked) RAG system. Keep create_test_app
# in sync with backend/app.py when routes or response shapes change.
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None


class SourceItem(BaseModel):
    """A single source reference with optional link"""
    text: str
    link: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[SourceItem]
    session_id: str


class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]


class _NoCacheStaticFiles(StaticFiles):
    """Mirror of app.DevStaticFiles -- stamps no-cache headers on file responses."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


def create_test_app(rag_system, static_dir=None) -> FastAPI:
    """
    Build a FastAPI app with the same routes/contracts as backend/app.py.

    Args:
        rag_system: anything quacking like RAGSystem (normally a MagicMock).
        static_dir: directory to serve at "/". When None the static mount is
            skipped entirely, so API-only tests need no frontend on disk.
    """
    app = FastAPI(title="Course Materials RAG System (test)", root_path="")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=[SourceItem(text=s.text, link=s.link) for s in sources],
                session_id=session_id,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        """End a conversation session and free its stored history"""
        try:
            rag_system.session_manager.delete_session(session_id)
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    if static_dir is not None:
        app.mount(
            "/",
            _NoCacheStaticFiles(directory=str(static_dir), html=True),
            name="static",
        )

    return app


@pytest.fixture
def sample_sources():
    """Two Source records: one with a lesson link, one without."""
    return [
        Source(text="MCP: Build Rich-Context AI Apps - Lesson 1", link="https://example.com/l1"),
        Source(text="Advanced Retrieval for AI - Lesson 3", link=None),
    ]


@pytest.fixture
def sample_analytics():
    """Course analytics payload in the shape RAGSystem.get_course_analytics returns."""
    return {
        "total_courses": 2,
        "course_titles": [
            "Advanced Retrieval for AI",
            "MCP: Build Rich-Context AI Apps",
        ],
    }


@pytest.fixture
def mock_rag(sample_sources, sample_analytics):
    """
    A stand-in RAGSystem for endpoint tests: no Chroma, no embedding model, no
    Anthropic calls. Not spec'd against RAGSystem because session_manager is an
    instance attribute and would not survive spec introspection.
    """
    rag = MagicMock()
    rag.query.return_value = ("Claude answers here.", sample_sources)
    rag.get_course_analytics.return_value = sample_analytics
    rag.session_manager.create_session.return_value = "session_1"
    rag.session_manager.delete_session.return_value = None
    return rag


@pytest.fixture
def static_dir(tmp_path):
    """A throwaway stand-in for frontend/, so "/" can be exercised in isolation."""
    root = tmp_path / "frontend"
    root.mkdir()
    (root / "index.html").write_text(
        "<!doctype html><title>Course Materials Assistant</title>", encoding="utf-8"
    )
    (root / "style.css").write_text("body { margin: 0; }", encoding="utf-8")
    (root / "script.js").write_text("// frontend entrypoint\n", encoding="utf-8")
    return root


@pytest.fixture
def api_client(mock_rag):
    """TestClient for the API routes only -- no static mount."""
    with TestClient(create_test_app(mock_rag)) as client:
        yield client


@pytest.fixture
def full_client(mock_rag, static_dir):
    """TestClient for the whole app, including the static frontend mount at "/"."""
    with TestClient(create_test_app(mock_rag, static_dir=static_dir)) as client:
        yield client
