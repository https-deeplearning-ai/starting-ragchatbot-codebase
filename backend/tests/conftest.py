"""
Pytest configuration and shared fixtures for RAG system tests.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def mock_config():
    """Mock configuration object"""
    config = Mock()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHROMA_PATH = "./test_chroma_db"
    config.ENVIRONMENT = "test"
    config.ALLOWED_HOSTS = ["*"]
    config.ALLOWED_ORIGINS = ["*"]
    return config


@pytest.fixture
def mock_vector_store():
    """Mock vector store with common behaviors"""
    mock_store = Mock()
    mock_store.search.return_value = Mock(
        error=None,
        is_empty=lambda: False,
        documents=["Test document content"],
        metadata=[{
            "course_title": "Test Course",
            "lesson_title": "Test Lesson",
            "chunk_id": "test_chunk_1"
        }]
    )
    mock_store.get_all_courses_metadata.return_value = [
        {
            "title": "Test Course",
            "course_link": "https://example.com/course",
            "lessons": [
                {"title": "Lesson 1", "link": "https://example.com/lesson1"},
                {"title": "Lesson 2", "link": "https://example.com/lesson2"}
            ]
        }
    ]
    mock_store.get_course_count.return_value = 1
    return mock_store


@pytest.fixture
def mock_ai_generator():
    """Mock AI generator with standard response"""
    mock_gen = Mock()
    mock_gen.generate_response.return_value = "This is a test response from the AI."
    return mock_gen


@pytest.fixture
def mock_session_manager():
    """Mock session manager"""
    mock_manager = Mock()
    mock_manager.create_session.return_value = "session_test123"
    mock_manager.get_history.return_value = []
    mock_manager.add_exchange.return_value = None
    mock_manager.clear_session.return_value = None
    return mock_manager


@pytest.fixture
def mock_rag_system(mock_vector_store, mock_ai_generator, mock_session_manager):
    """Mock RAG system with all dependencies"""
    mock_system = Mock()
    mock_system.vector_store = mock_vector_store
    mock_system.ai_generator = mock_ai_generator
    mock_system.session_manager = mock_session_manager
    mock_system.query.return_value = (
        "This is a test answer",
        [{"course": "Test Course", "lesson": "Test Lesson"}]
    )
    mock_system.get_course_analytics.return_value = {
        "total_courses": 1,
        "course_titles": ["Test Course"]
    }
    mock_system.outline_tool = Mock()
    mock_system.outline_tool.execute.return_value = "Test Course Outline:\n- Lesson 1\n- Lesson 2"
    return mock_system


@pytest.fixture
def test_app(mock_rag_system, mock_config, tmp_path):
    """
    Create a test FastAPI app without static file mounting to avoid import issues.
    Returns TestClient for making requests.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field, validator
    from typing import List, Optional, Union, Dict, Any

    # Create clean test app
    app = FastAPI(title="Test RAG System")

    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pydantic models (copied from app.py)
    class QueryRequest(BaseModel):
        query: str = Field(..., min_length=1, max_length=2000)
        session_id: Optional[str] = Field(None, max_length=100)

        @validator('query')
        def query_must_not_be_empty(cls, v):
            if not v or not v.strip():
                raise ValueError('Query cannot be empty')
            return v.strip()

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Union[str, Dict[str, Any]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    class ClearSessionRequest(BaseModel):
        session_id: str = Field(..., min_length=1, max_length=100)

        @validator('session_id')
        def session_id_must_be_valid(cls, v):
            if not v.startswith('session_'):
                raise ValueError('Session ID must start with "session_"')
            return v

    class ClearSessionResponse(BaseModel):
        success: bool
        message: str

    class CourseOutlineRequest(BaseModel):
        course_title: str = Field(..., min_length=1, max_length=200)

        @validator('course_title')
        def course_title_must_not_be_empty(cls, v):
            if not v or not v.strip():
                raise ValueError('Course title cannot be empty')
            return v.strip()

    class CourseOutlineResponse(BaseModel):
        course_title: str
        course_link: Optional[str]
        lessons: List[Dict[str, Any]]
        total_lessons: int
        formatted_outline: str

    class HealthCheckResponse(BaseModel):
        status: str
        version: str
        environment: str
        timestamp: str
        components: Dict[str, Dict[str, Any]]

    # API endpoints
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check():
        from datetime import datetime
        return HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            environment="test",
            timestamp=datetime.utcnow().isoformat(),
            components={
                "vector_store": {"status": "healthy", "details": {"course_count": 1}},
                "ai_generator": {"status": "healthy", "details": {"model": "test-model"}},
                "system": {"status": "healthy", "details": {}}
            }
        )

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
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

    @app.post("/api/clear_session", response_model=ClearSessionResponse)
    async def clear_session(request: ClearSessionRequest):
        try:
            mock_rag_system.session_manager.clear_session(request.session_id)
            return ClearSessionResponse(
                success=True,
                message="Session cleared successfully"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/course_outline", response_model=CourseOutlineResponse)
    async def get_course_outline(request: CourseOutlineRequest):
        try:
            result = mock_rag_system.outline_tool.execute(request.course_title)

            if result.startswith("No course found") or result.startswith("No courses available"):
                raise HTTPException(status_code=404, detail=result)

            all_courses = mock_rag_system.vector_store.get_all_courses_metadata()
            matching_course = None
            course_title_lower = request.course_title.lower()

            for course in all_courses:
                if course.get('title', '').lower() == course_title_lower or course_title_lower in course.get('title', '').lower():
                    matching_course = course
                    break

            if not matching_course:
                raise HTTPException(status_code=404, detail=f"Course not found: {request.course_title}")

            return CourseOutlineResponse(
                course_title=matching_course.get('title', 'Unknown'),
                course_link=matching_course.get('course_link'),
                lessons=matching_course.get('lessons', []),
                total_lessons=len(matching_course.get('lessons', [])),
                formatted_outline=result
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return TestClient(app)


@pytest.fixture
def sample_query_request():
    """Sample query request data"""
    return {
        "query": "What is the main topic of the course?",
        "session_id": "session_test123"
    }


@pytest.fixture
def sample_course_data():
    """Sample course data for testing"""
    return {
        "title": "Test Course",
        "course_link": "https://example.com/course",
        "lessons": [
            {"title": "Introduction", "link": "https://example.com/lesson1"},
            {"title": "Advanced Topics", "link": "https://example.com/lesson2"}
        ]
    }


@pytest.fixture(autouse=True)
def reset_mocks():
    """Automatically reset all mocks after each test"""
    yield
    # Cleanup happens automatically with pytest's fixture scope