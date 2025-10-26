"""
Test configuration and shared fixtures for RAG system tests
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Dict, Any
from fastapi.testclient import TestClient
import json

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models import Course, Lesson, CourseChunk
from vector_store import SearchResults


@dataclass
class TestConfig:
    """Test configuration that mirrors the real config but with safe defaults"""
    ANTHROPIC_API_KEY: str = "test-api-key"
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-202410224"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = "./test_chroma_db"


@pytest.fixture
def test_config():
    """Provide test configuration"""
    return TestConfig()


@pytest.fixture
def temp_chroma_db():
    """Create a temporary directory for test ChromaDB"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    lessons = [
        Lesson(
            lesson_number=1,
            title="Introduction to Machine Learning",
            lesson_link="https://example.com/lesson1"
        ),
        Lesson(
            lesson_number=2,
            title="Linear Regression Basics",
            lesson_link="https://example.com/lesson2"
        ),
        Lesson(
            lesson_number=3,
            title="Advanced Neural Networks",
            lesson_link="https://example.com/lesson3"
        )
    ]

    return Course(
        title="Machine Learning Fundamentals",
        instructor="Dr. Test Instructor",
        course_link="https://example.com/ml-course",
        lessons=lessons
    )


@pytest.fixture
def sample_course_chunks():
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            course_title="Machine Learning Fundamentals",
            lesson_number=1,
            chunk_index=0,
            content="Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data."
        ),
        CourseChunk(
            course_title="Machine Learning Fundamentals",
            lesson_number=1,
            chunk_index=1,
            content="Supervised learning uses labeled training data to learn mapping functions from input to output."
        ),
        CourseChunk(
            course_title="Machine Learning Fundamentals",
            lesson_number=2,
            chunk_index=0,
            content="Linear regression is a fundamental statistical technique for modeling the relationship between variables."
        ),
        CourseChunk(
            course_title="Machine Learning Fundamentals",
            lesson_number=3,
            chunk_index=0,
            content="Neural networks are computing systems inspired by biological neural networks in animal brains."
        )
    ]


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store for testing"""
    mock_store = Mock()

    # Configure mock search results
    successful_results = SearchResults(
        documents=["Test content about machine learning"],
        metadata=[{
            "course_title": "Machine Learning Fundamentals",
            "lesson_number": 1,
            "chunk_index": 0
        }],
        distances=[0.1]
    )

    empty_results = SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )

    error_results = SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error="Search failed: Database connection error"
    )

    # Configure mock methods
    mock_store.search.return_value = successful_results
    mock_store._resolve_course_name.return_value = "Machine Learning Fundamentals"
    mock_store.get_course_count.return_value = 1
    mock_store.get_existing_course_titles.return_value = ["Machine Learning Fundamentals"]

    return mock_store


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client for testing"""
    mock_client = Mock()

    # Mock successful response
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a test response about machine learning.")]
    mock_response.stop_reason = "stop_sequence"

    # Mock tool use response
    mock_tool_response = Mock()
    mock_tool_response.stop_reason = "tool_use"
    mock_tool_response.content = [
        Mock(
            type="tool_use",
            id="tool_123",
            name="search_course_content",
            input={"query": "machine learning basics"}
        )
    ]

    # Mock final response after tool execution
    mock_final_response = Mock()
    mock_final_response.content = [Mock(text="Based on the course materials, machine learning is...")]

    # Configure the client
    mock_client.messages.create.return_value = mock_response

    return {
        'client': mock_client,
        'response': mock_response,
        'tool_response': mock_tool_response,
        'final_response': mock_final_response
    }


@pytest.fixture
def mock_search_tools():
    """Create mock search tools for testing"""
    mock_search_tool = Mock()
    mock_search_tool.get_tool_definition.return_value = {
        "name": "search_course_content",
        "description": "Search course materials",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "course_name": {"type": "string"},
                "lesson_number": {"type": "integer"}
            }
        }
    }
    mock_search_tool.execute.return_value = "Found relevant content about machine learning"
    mock_search_tool.last_sources = ["Machine Learning Fundamentals - Lesson 1"]

    mock_outline_tool = Mock()
    mock_outline_tool.get_tool_definition.return_value = {
        "name": "get_course_outline",
        "description": "Get course outline",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_title": {"type": "string"}
            }
        }
    }
    mock_outline_tool.execute.return_value = "Course: Machine Learning Fundamentals\nLessons:\n1. Introduction\n2. Linear Regression"
    mock_outline_tool.last_sources = ["Machine Learning Fundamentals"]

    return {
        'search_tool': mock_search_tool,
        'outline_tool': mock_outline_tool
    }


@pytest.fixture
def sample_queries():
    """Sample queries for testing"""
    return {
        "valid_content_query": "What is machine learning?",
        "course_specific_query": "Tell me about linear regression in Machine Learning Fundamentals",
        "lesson_specific_query": "What are neural networks in lesson 3?",
        "invalid_course_query": "Tell me about quantum computing in Advanced Physics",
        "general_knowledge_query": "What is the capital of France?",
        "empty_query": "",
        "malformed_query": "!!@@##$$"
    }


@pytest.fixture
def expected_tool_definitions():
    """Expected tool definitions for validation"""
    return [
        {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in the course content"},
                    "course_name": {"type": "string", "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"},
                    "lesson_number": {"type": "integer", "description": "Specific lesson number to search within (e.g. 1, 2, 3)"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_course_outline",
            "description": "Get complete course outline including title, link, and full lesson list",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_title": {"type": "string", "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"}
                },
                "required": ["course_title"]
            }
        }
    ]


# Test data for different scenarios
@pytest.fixture
def search_test_cases():
    """Various test cases for search functionality"""
    return [
        {
            "name": "successful_search",
            "query": "machine learning",
            "course_name": None,
            "lesson_number": None,
            "expected_results": "found content",
            "should_succeed": True
        },
        {
            "name": "course_specific_search",
            "query": "linear regression",
            "course_name": "Machine Learning Fundamentals",
            "lesson_number": None,
            "expected_results": "found specific content",
            "should_succeed": True
        },
        {
            "name": "lesson_specific_search",
            "query": "neural networks",
            "course_name": "Machine Learning Fundamentals",
            "lesson_number": 3,
            "expected_results": "found lesson content",
            "should_succeed": True
        },
        {
            "name": "invalid_course_search",
            "query": "anything",
            "course_name": "Nonexistent Course",
            "lesson_number": None,
            "expected_results": "No course found matching",
            "should_succeed": False
        },
        {
            "name": "empty_results_search",
            "query": "nonexistent topic",
            "course_name": None,
            "lesson_number": None,
            "expected_results": "No relevant content found",
            "should_succeed": True
        }
    ]


# Patch environment variables for testing
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for all tests"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")


# Disable actual network calls during tests
@pytest.fixture(autouse=True)
def disable_network_calls(monkeypatch):
    """Prevent actual network calls during testing"""
    def mock_no_op(*args, **kwargs):
        pass

    # Mock any potential network calls
    monkeypatch.setattr("requests.get", Mock(side_effect=Exception("Network calls disabled in tests")))
    monkeypatch.setattr("requests.post", Mock(side_effect=Exception("Network calls disabled in tests")))


# API Testing Fixtures

@pytest.fixture
def test_app():
    """Create a test FastAPI app without static file mounting to avoid import issues"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    # Create test app (minimal version without static files)
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Add middleware for consistency with main app
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Pydantic models (same as main app)
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

    # Mock RAG system
    mock_rag = Mock()

    # Configure mock responses
    mock_rag.query.return_value = (
        "This is a test response about machine learning fundamentals.",
        ["Machine Learning Fundamentals - Lesson 1"]
    )
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 1,
        "course_titles": ["Machine Learning Fundamentals"]
    }
    mock_rag.session_manager = Mock()
    mock_rag.session_manager.create_session.return_value = "test-session-123"

    # Store the mock for tests to access
    app.state.mock_rag = mock_rag

    # API endpoints (same logic as main app but using mock)
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag.session_manager.create_session()

            answer, sources = mock_rag.query(request.query, session_id)

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
            analytics = mock_rag.get_course_analytics()
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


@pytest.fixture
def mock_rag_system(test_app):
    """Access the mock RAG system from the test app"""
    return test_app.state.mock_rag


@pytest.fixture
def sample_query_requests():
    """Sample query requests for API testing"""
    return {
        "valid_query": {
            "query": "What is machine learning?",
            "session_id": None
        },
        "query_with_session": {
            "query": "Tell me about linear regression",
            "session_id": "existing-session-456"
        },
        "empty_query": {
            "query": "",
            "session_id": None
        },
        "malformed_query_content": "invalid json content",
        "missing_query_field": {
            "session_id": "test-session"
        }
    }


@pytest.fixture
def sample_api_responses():
    """Expected API response structures"""
    return {
        "query_response": {
            "answer": "This is a test response about machine learning fundamentals.",
            "sources": ["Machine Learning Fundamentals - Lesson 1"],
            "session_id": "test-session-123"
        },
        "courses_response": {
            "total_courses": 1,
            "course_titles": ["Machine Learning Fundamentals"]
        },
        "root_response": {
            "message": "Course Materials RAG System API"
        }
    }


@pytest.fixture
def error_scenarios():
    """Error scenarios for API testing"""
    return {
        "rag_query_error": Exception("RAG system query failed"),
        "rag_analytics_error": Exception("Failed to get course analytics"),
        "missing_session_error": Exception("Session not found"),
        "invalid_query_error": Exception("Invalid query format")
    }