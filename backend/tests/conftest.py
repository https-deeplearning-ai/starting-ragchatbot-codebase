"""
Pytest configuration and fixtures for RAG system tests
"""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add backend directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient  # noqa: E402
from models import Course, Lesson, Source  # noqa: E402
from vector_store import SearchResults  # noqa: E402


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore with common test methods"""
    store = Mock()

    # Default successful search results
    store.search.return_value = SearchResults(
        documents=["Test content from lesson 1"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0}],
        distances=[0.5],
    )

    # Default link retrieval
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    store.get_course_link.return_value = "https://example.com/course"

    # Default course outline
    store.get_course_outline.return_value = {
        "title": "Test Course",
        "instructor": "Test Instructor",
        "course_link": "https://example.com/course",
        "lesson_count": 3,
        "lessons": [
            {"lesson_number": 0, "lesson_title": "Introduction"},
            {"lesson_number": 1, "lesson_title": "Getting Started"},
            {"lesson_number": 2, "lesson_title": "Advanced Topics"},
        ],
    }

    return store


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager with tool execution"""
    manager = Mock()
    manager.execute_tool.return_value = "[Test Course - Lesson 1]\nTest content"
    manager.get_last_sources.return_value = [
        {"text": "Test Course - Lesson 1", "link": "https://example.com/lesson/1", "type": "lesson"}
    ]
    manager.reset_sources.return_value = None
    return manager


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    client = Mock()

    # Mock successful response without tool use
    response = Mock()
    response.content = [Mock(type="text", text="Test response")]
    response.stop_reason = "end_turn"
    client.messages.create.return_value = response

    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI/OpenRouter API client"""
    client = Mock()

    # Mock successful response
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = "Test response"
    response.choices[0].message.tool_calls = None
    client.chat.completions.create.return_value = response

    return client


@pytest.fixture
def sample_course():
    """Sample course object for testing"""
    return Course(
        title="Introduction to Testing",
        course_link="https://example.com/testing-course",
        instructor="Test Instructor",
        lessons=[
            Lesson(
                lesson_number=0, title="Course Overview", lesson_link="https://example.com/lesson/0"
            ),
            Lesson(
                lesson_number=1, title="Getting Started", lesson_link="https://example.com/lesson/1"
            ),
            Lesson(
                lesson_number=2, title="Advanced Topics", lesson_link="https://example.com/lesson/2"
            ),
        ],
    )


@pytest.fixture
def empty_search_results():
    """Empty search results for testing edge cases"""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def search_results_with_error():
    """Search results with error for testing error handling"""
    return SearchResults.empty("Search failed: Connection timeout")


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for API testing"""
    manager = Mock()
    manager.create_session.return_value = "test-session-123"
    manager.add_message.return_value = None
    manager.get_conversation_history.return_value = []
    return manager


@pytest.fixture
def mock_rag_system(mock_session_manager):
    """Mock RAGSystem for API testing"""
    rag = Mock()
    rag.session_manager = mock_session_manager

    # Mock query method
    rag.query.return_value = (
        "Test answer from RAG system",
        [
            Source(
                text="Test Course - Lesson 1", link="https://example.com/lesson/1", type="lesson"
            ),
            Source(
                text="Test Course - Lesson 2", link="https://example.com/lesson/2", type="lesson"
            ),
        ],
    )

    # Mock get_course_analytics method
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Introduction to Testing", "Advanced Testing Techniques"],
    }

    # Mock add_course_folder method
    rag.add_course_folder.return_value = (2, 50)

    return rag


@pytest.fixture
def test_app(mock_rag_system):
    """Create test FastAPI app without static file mounting"""
    from typing import List, Optional

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    # Import models
    from models import Source
    from pydantic import BaseModel

    # Create test app
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Source]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # API Endpoints (same as app.py but without static files)
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"], course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def client(test_app):
    """Create TestClient for API testing"""
    return TestClient(test_app)


@pytest.fixture
def sample_query_request():
    """Sample query request data"""
    return {"query": "What is test-driven development?", "session_id": None}


@pytest.fixture
def sample_sources():
    """Sample source list for testing"""
    return [
        Source(text="Test Course - Lesson 1", link="https://example.com/lesson/1", type="lesson"),
        Source(text="Test Course - Lesson 2", link="https://example.com/lesson/2", type="lesson"),
    ]
