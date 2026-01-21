"""
Shared pytest fixtures for RAG chatbot tests.
"""
import pytest
from unittest.mock import Mock
from dataclasses import dataclass
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vector_store import SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager


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
