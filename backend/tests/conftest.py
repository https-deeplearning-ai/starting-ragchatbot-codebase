"""
Shared pytest fixtures for RAG chatbot tests.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vector_store import SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager


# ============== API Testing Fixtures ==============

@pytest.fixture
def mock_rag_system():
    """Create a fully mocked RAGSystem for API testing"""
    mock_rag = MagicMock()

    # Configure session manager
    mock_rag.session_manager.create_session.return_value = "test-session-123"
    mock_rag.session_manager.get_conversation_history.return_value = []

    # Configure query method to return proper format
    mock_rag.query.return_value = (
        "This is a test response about course materials.",
        ["Test Course - Lesson 1", "Test Course - Lesson 2"]
    )

    # Configure course analytics
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["Introduction to Python", "Advanced ML", "Web Development"]
    }

    return mock_rag


@pytest.fixture
def test_app(mock_rag_system):
    """
    Create a test FastAPI app without static file mounting.

    This avoids the issue where the main app.py mounts static files from
    ../frontend which doesn't exist in the test environment.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    # Create a fresh app for testing
    app = FastAPI(title="Course Materials RAG System - Test")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pydantic models (same as app.py)
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

    # Inject the mock RAG system
    app.state.rag_system = mock_rag_system

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            rag_system = app.state.rag_system
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)

            # Convert string sources to SourceItem objects
            source_items = [SourceItem(text=source) for source in sources]

            return QueryResponse(
                answer=answer,
                sources=source_items,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/sessions/{session_id}")
    async def delete_session(session_id: str):
        rag_system = app.state.rag_system
        rag_system.session_manager.delete_session(session_id)
        return {"status": "ok"}

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            rag_system = app.state.rag_system
            analytics = rag_system.get_course_analytics()
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
def test_client(test_app):
    """Create a TestClient for the test app"""
    from fastapi.testclient import TestClient
    return TestClient(test_app)


@pytest.fixture
def mock_rag_system_error():
    """RAG system mock that raises exceptions"""
    mock_rag = MagicMock()
    mock_rag.session_manager.create_session.return_value = "test-session-123"
    mock_rag.query.side_effect = Exception("Database connection failed")
    mock_rag.get_course_analytics.side_effect = Exception("Analytics unavailable")
    return mock_rag


@pytest.fixture
def test_client_with_errors(mock_rag_system_error):
    """Test client with a RAG system that raises errors"""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI()

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

    app.state.rag_system = mock_rag_system_error

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            rag_system = app.state.rag_system
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)
            source_items = [SourceItem(text=source) for source in sources]

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
            rag_system = app.state.rag_system
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    from fastapi.testclient import TestClient
    return TestClient(app)


# ============== SearchResults Fixtures ==============

@pytest.fixture
def empty_search_results():
    """SearchResults with no documents (simulates MAX_RESULTS=0 bug)"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )


@pytest.fixture
def valid_search_results():
    """SearchResults with actual content"""
    return SearchResults(
        documents=[
            "MCP (Model Context Protocol) is a protocol for AI tool integration.",
            "The protocol defines how AI models can interact with external tools."
        ],
        metadata=[
            {"course_title": "Introduction to MCP", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Introduction to MCP", "lesson_number": 2, "chunk_index": 0}
        ],
        distances=[0.25, 0.35]
    )


@pytest.fixture
def error_search_results():
    """SearchResults with an error message"""
    return SearchResults.empty("Search error: Database connection failed")


# ============== Mock VectorStore Fixtures ==============

@pytest.fixture
def mock_vector_store_empty():
    """VectorStore mock that returns empty results (simulates MAX_RESULTS=0)"""
    mock_store = Mock()
    mock_store.search.return_value = SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )
    mock_store.max_results = 0  # The bug!
    return mock_store


@pytest.fixture
def mock_vector_store_with_results():
    """VectorStore mock that returns valid results"""
    mock_store = Mock()
    mock_store.search.return_value = SearchResults(
        documents=[
            "MCP enables AI models to use external tools.",
            "Tool definitions follow a specific schema."
        ],
        metadata=[
            {"course_title": "MCP Course", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "MCP Course", "lesson_number": 2, "chunk_index": 1}
        ],
        distances=[0.2, 0.4]
    )
    mock_store.max_results = 5
    return mock_store


@pytest.fixture
def mock_vector_store_with_error():
    """VectorStore mock that returns error results"""
    mock_store = Mock()
    mock_store.search.return_value = SearchResults.empty("No course found matching 'nonexistent'")
    return mock_store


@pytest.fixture
def mock_vector_store_course_not_found():
    """VectorStore mock for course resolution failure"""
    mock_store = Mock()
    mock_store.search.return_value = SearchResults.empty("No course found matching 'Unknown Course'")
    return mock_store


# ============== Anthropic Client Mock Fixtures ==============

@pytest.fixture
def mock_anthropic_text_response():
    """Mock Anthropic response with direct text (no tool use)"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_content = Mock()
    mock_content.type = "text"
    mock_content.text = "Here is your answer about the course content."
    mock_response.content = [mock_content]
    return mock_response


@pytest.fixture
def mock_anthropic_tool_use_response():
    """Mock Anthropic response requesting tool use"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    # Tool use content block
    mock_tool_use = Mock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.id = "tool_123"
    mock_tool_use.name = "search_course_content"
    mock_tool_use.input = {"query": "MCP protocol", "course_name": "MCP Course"}

    mock_response.content = [mock_tool_use]
    return mock_response


@pytest.fixture
def mock_anthropic_final_response():
    """Mock Anthropic final response after tool execution"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_content = Mock()
    mock_content.type = "text"
    mock_content.text = "Based on the course materials, MCP is a protocol for AI integration."
    mock_response.content = [mock_content]
    return mock_response


@pytest.fixture
def mock_anthropic_client(mock_anthropic_text_response):
    """Mock Anthropic client that returns direct text response"""
    mock_client = Mock()
    mock_client.messages.create.return_value = mock_anthropic_text_response
    return mock_client


# ============== Config Fixtures ==============

@pytest.fixture
def config_with_bug():
    """Config object with MAX_RESULTS=0 bug"""
    @dataclass
    class BuggyConfig:
        ANTHROPIC_API_KEY: str = "test-key"
        ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
        EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
        CHUNK_SIZE: int = 800
        CHUNK_OVERLAP: int = 100
        MAX_RESULTS: int = 0  # THE BUG
        MAX_HISTORY: int = 2
        CHROMA_PATH: str = "./test_chroma_db"
    return BuggyConfig()


@pytest.fixture
def config_fixed():
    """Config object with proper MAX_RESULTS value"""
    @dataclass
    class FixedConfig:
        ANTHROPIC_API_KEY: str = "test-key"
        ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
        EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
        CHUNK_SIZE: int = 800
        CHUNK_OVERLAP: int = 100
        MAX_RESULTS: int = 5  # Fixed value
        MAX_HISTORY: int = 2
        CHROMA_PATH: str = "./test_chroma_db"
    return FixedConfig()


# ============== ToolManager Fixtures ==============

@pytest.fixture
def tool_manager_with_search_tool(mock_vector_store_with_results):
    """ToolManager with registered CourseSearchTool"""
    manager = ToolManager()
    search_tool = CourseSearchTool(mock_vector_store_with_results)
    manager.register_tool(search_tool)
    return manager


@pytest.fixture
def tool_manager_with_empty_results(mock_vector_store_empty):
    """ToolManager with search tool that returns empty results"""
    manager = ToolManager()
    search_tool = CourseSearchTool(mock_vector_store_empty)
    manager.register_tool(search_tool)
    return manager


# ============== Sequential Tool Calling Fixtures ==============

@pytest.fixture
def mock_anthropic_second_tool_use_response():
    """Mock Anthropic response requesting a second tool call (for round 2)"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    mock_tool_use = Mock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.id = "tool_456"
    mock_tool_use.name = "search_course_content"
    mock_tool_use.input = {"query": "MCP tools integration", "lesson_number": 4}

    mock_response.content = [mock_tool_use]
    return mock_response


def create_tool_use_response(tool_name: str, tool_input: dict, tool_id: str = "tool_123"):
    """Helper function to create mock tool use responses"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    mock_tool_use = Mock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.id = tool_id
    mock_tool_use.name = tool_name
    mock_tool_use.input = tool_input

    mock_response.content = [mock_tool_use]
    return mock_response


def create_text_response(text: str):
    """Helper function to create mock text responses"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    mock_content = Mock()
    mock_content.type = "text"
    mock_content.text = text

    mock_response.content = [mock_content]
    return mock_response
