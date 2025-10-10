"""Pytest configuration and shared fixtures for RAG system tests"""

import os
import shutil
import sys
import tempfile
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_generator import AIGenerator
from config import Config
from document_processor import DocumentProcessor
from models import Course, CourseChunk, Lesson
from rag_system import RAGSystem
from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager
from session_manager import SessionManager
from vector_store import SearchResults, VectorStore


@pytest.fixture
def temp_chroma_path():
    """Create a temporary ChromaDB directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_config(temp_chroma_path):
    """Create a test configuration"""
    config = Config()
    config.CHROMA_PATH = temp_chroma_path
    config.MAX_RESULTS = 5
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_HISTORY = 2
    return config


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    return Course(
        title="Introduction to Machine Learning",
        course_link="https://example.com/ml-course",
        instructor="Dr. Jane Smith",
        lessons=[
            Lesson(
                lesson_number=0,
                title="Course Overview",
                lesson_link="https://example.com/ml-course/lesson0",
            ),
            Lesson(
                lesson_number=1,
                title="Supervised Learning Basics",
                lesson_link="https://example.com/ml-course/lesson1",
            ),
            Lesson(
                lesson_number=2,
                title="Neural Networks",
                lesson_link="https://example.com/ml-course/lesson2",
            ),
        ],
    )


@pytest.fixture
def sample_course_2():
    """Create a second sample course for testing"""
    return Course(
        title="Building Towards Computer Use with Anthropic",
        course_link="https://www.deeplearning.ai/short-courses/building-toward-computer-use-with-anthropic/",
        instructor="Colt Steele",
        lessons=[
            Lesson(
                lesson_number=0,
                title="Introduction",
                lesson_link="https://learn.deeplearning.ai/courses/building-toward-computer-use-with-anthropic/lesson/a6k0z/introduction",
            ),
            Lesson(
                lesson_number=1,
                title="API Basics",
                lesson_link="https://learn.deeplearning.ai/courses/building-toward-computer-use-with-anthropic/lesson/xyz/api-basics",
            ),
        ],
    )


@pytest.fixture
def sample_chunks():
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            content="Machine learning is a subset of artificial intelligence that enables systems to learn from data. It involves training algorithms to recognize patterns and make predictions.",
            course_title="Introduction to Machine Learning",
            lesson_number=0,
            chunk_index=0,
        ),
        CourseChunk(
            content="Supervised learning uses labeled training data to learn the relationship between inputs and outputs. Common algorithms include linear regression, decision trees, and neural networks.",
            course_title="Introduction to Machine Learning",
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes that process and transform input data to produce outputs.",
            course_title="Introduction to Machine Learning",
            lesson_number=2,
            chunk_index=2,
        ),
        CourseChunk(
            content="Anthropic's Claude is a large language model designed with safety and reliability in mind. It uses constitutional AI principles to ensure helpful, harmless, and honest behavior.",
            course_title="Building Towards Computer Use with Anthropic",
            lesson_number=0,
            chunk_index=3,
        ),
        CourseChunk(
            content="The Anthropic API allows developers to integrate Claude into their applications. You can make requests using HTTP POST with JSON payloads containing your prompts and parameters.",
            course_title="Building Towards Computer Use with Anthropic",
            lesson_number=1,
            chunk_index=4,
        ),
    ]


@pytest.fixture
def vector_store(test_config, sample_course, sample_course_2, sample_chunks):
    """Create a populated vector store for testing"""
    store = VectorStore(
        chroma_path=test_config.CHROMA_PATH,
        embedding_model=test_config.EMBEDDING_MODEL,
        max_results=test_config.MAX_RESULTS,
    )

    # Add course metadata
    store.add_course_metadata(sample_course)
    store.add_course_metadata(sample_course_2)

    # Add course content chunks
    store.add_course_content(sample_chunks)

    return store


@pytest.fixture
def course_search_tool(vector_store):
    """Create a CourseSearchTool instance"""
    return CourseSearchTool(vector_store)


@pytest.fixture
def course_outline_tool(vector_store):
    """Create a CourseOutlineTool instance"""
    return CourseOutlineTool(vector_store)


@pytest.fixture
def tool_manager(course_search_tool, course_outline_tool):
    """Create a ToolManager with registered tools"""
    manager = ToolManager()
    manager.register_tool(course_search_tool)
    manager.register_tool(course_outline_tool)
    return manager


@pytest.fixture
def mock_api_key():
    """Return a mock API key for testing"""
    return "test-api-key-12345"


@pytest.fixture
def document_processor(test_config):
    """Create a DocumentProcessor instance"""
    return DocumentProcessor(
        chunk_size=test_config.CHUNK_SIZE, chunk_overlap=test_config.CHUNK_OVERLAP
    )


@pytest.fixture
def session_manager(test_config):
    """Create a SessionManager instance"""
    return SessionManager(max_history=test_config.MAX_HISTORY)


@pytest.fixture
def sample_course_document():
    """Create a sample course document content"""
    return """Course Title: Introduction to Machine Learning
Course Link: https://example.com/ml-course
Course Instructor: Dr. Jane Smith

Lesson 0: Course Overview
Lesson Link: https://example.com/ml-course/lesson0
Machine learning is a subset of artificial intelligence that enables systems to learn from data. It involves training algorithms to recognize patterns and make predictions. This course will cover the fundamentals of machine learning including supervised learning, unsupervised learning, and neural networks.

Lesson 1: Supervised Learning Basics
Lesson Link: https://example.com/ml-course/lesson1
Supervised learning uses labeled training data to learn the relationship between inputs and outputs. Common algorithms include linear regression, decision trees, and neural networks. The goal is to create a model that can make accurate predictions on new, unseen data.

Lesson 2: Neural Networks
Lesson Link: https://example.com/ml-course/lesson2
Neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes that process and transform input data to produce outputs. Deep learning uses neural networks with multiple hidden layers to learn complex patterns.
"""


@pytest.fixture
def temp_course_file(sample_course_document):
    """Create a temporary course file for testing document processing"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(sample_course_document)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


# ============================================================================
# API Testing Fixtures
# ============================================================================


@pytest.fixture
def mock_rag_system(test_config):
    """Create a mock RAG system for API testing"""
    mock_rag = Mock(spec=RAGSystem)
    mock_rag.session_manager = Mock(spec=SessionManager)
    mock_rag.session_manager.create_session.return_value = "test-session-123"

    # Default query response
    mock_rag.query.return_value = (
        "This is a test response about machine learning.",
        [
            {
                "course_title": "Introduction to Machine Learning",
                "lesson_number": 1,
                "content": "Machine learning basics...",
                "lesson_link": "https://example.com/ml-course/lesson1",
            }
        ],
    )

    # Default analytics response
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": [
            "Introduction to Machine Learning",
            "Building Towards Computer Use with Anthropic",
        ],
    }

    return mock_rag


@pytest.fixture
def test_client(mock_rag_system):
    """
    Create a FastAPI test client with mocked dependencies.
    This avoids issues with static file mounting by creating a clean test app.
    """
    from typing import Any, Dict, List, Optional

    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from pydantic import BaseModel

    # Create test app (without static file mounting)
    test_app = FastAPI(title="Course Materials RAG System - Test")

    # Use the mocked RAG system
    test_app.state.rag_system = mock_rag_system

    # Define request/response models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Any]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Define test endpoints
    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            rag_system = test_app.state.rag_system
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)

            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            rag_system = test_app.state.rag_system
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/")
    async def root():
        """Root endpoint for health check"""
        return {"status": "ok", "message": "RAG System API"}

    return TestClient(test_app)


@pytest.fixture
def sample_query_request():
    """Sample query request payload"""
    return {"query": "What is machine learning?", "session_id": None}


@pytest.fixture
def sample_query_request_with_session():
    """Sample query request with existing session"""
    return {
        "query": "Tell me more about neural networks",
        "session_id": "test-session-123",
    }
