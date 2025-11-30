"""
Shared pytest fixtures for RAG System tests
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from models import Course, CourseChunk, Lesson
from vector_store import SearchResults


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore"""
    return Mock()


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    return Course(
        title="Python Basics",
        course_link="https://example.com/python-basics",
        instructor="Jane Doe",
        lessons=[
            Lesson(
                lesson_number=1,
                title="Introduction to Python",
                lesson_link="https://example.com/python-basics/lesson1",
            ),
            Lesson(
                lesson_number=2,
                title="Variables and Data Types",
                lesson_link="https://example.com/python-basics/lesson2",
            ),
            Lesson(
                lesson_number=3,
                title="Control Flow",
                lesson_link="https://example.com/python-basics/lesson3",
            ),
        ],
    )


@pytest.fixture
def sample_course_chunks(sample_course):
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            content="Lesson 1 content: Python is a high-level programming language.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="Python supports multiple programming paradigms.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Lesson 2 content: Variables store data values in Python.",
            course_title=sample_course.title,
            lesson_number=2,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def sample_search_results():
    """Create sample SearchResults for testing"""
    return SearchResults(
        documents=[
            "Python is a high-level programming language.",
            "Variables store data values in Python.",
        ],
        metadata=[
            {"course_title": "Python Basics", "lesson_number": 1},
            {"course_title": "Python Basics", "lesson_number": 2},
        ],
        distances=[0.1, 0.15],
        links=[
            "https://example.com/python-basics/lesson1",
            "https://example.com/python-basics/lesson2",
        ],
        error=None,
    )


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client"""
    mock_client = Mock()
    mock_client.messages = Mock()
    return mock_client


@pytest.fixture
def mock_anthropic_response_no_tool():
    """Mock Anthropic API response without tool use"""
    response = Mock()
    response.stop_reason = "end_turn"
    response.content = [Mock(text="This is a direct response without using tools.")]
    return response


@pytest.fixture
def mock_anthropic_response_with_tool():
    """Mock Anthropic API response with tool use"""
    # First response - requests tool use
    tool_response = Mock()
    tool_response.stop_reason = "tool_use"

    # Create mock tool use block
    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.name = "search_course_content"
    tool_block.id = "tool_123"
    tool_block.input = {"query": "What is Python?"}

    tool_response.content = [tool_block]

    return tool_response


@pytest.fixture
def mock_anthropic_final_response():
    """Mock final Anthropic API response after tool execution"""
    response = Mock()
    response.stop_reason = "end_turn"
    response.content = [
        Mock(
            text="Python is a high-level programming language used for general-purpose programming."
        )
    ]
    return response


@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for API testing"""
    mock_rag = Mock()
    mock_rag.query.return_value = (
        "Python is a high-level programming language.",
        [
            {"text": "Python supports multiple paradigms.", "link": "https://example.com/lesson1"},
            {"text": "Python has dynamic typing.", "link": "https://example.com/lesson2"}
        ]
    )
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Basics", "Advanced Python"]
    }
    mock_rag.session_manager = Mock()
    mock_rag.session_manager.create_session.return_value = "test_session_123"
    return mock_rag


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app without static file mounting"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    # Create test app
    app = FastAPI(title="Course Materials RAG System Test")

    # Add CORS
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

    class SourceItem(BaseModel):
        text: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # API endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            source_items = []
            for source in sources:
                if isinstance(source, dict):
                    source_items.append(SourceItem(text=source.get("text", ""), link=source.get("link")))
                else:
                    source_items.append(SourceItem(text=str(source), link=None))

            return QueryResponse(
                answer=answer,
                sources=source_items,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
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
        return {"message": "Course Materials RAG System API"}

    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the FastAPI app"""
    return TestClient(test_app)
