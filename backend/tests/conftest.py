"""Shared pytest fixtures for testing the RAG system"""

from unittest.mock import Mock, patch

import pytest

from tests.fixtures.sample_data import (
    SAMPLE_ANTHROPIC_TEXT_RESPONSE,
    SAMPLE_COURSE_METADATA,
    SAMPLE_COURSE_METADATA_2,
    SAMPLE_SEARCH_RESULTS_EMPTY,
    SAMPLE_SEARCH_RESULTS_SUCCESS,
    SAMPLE_SEARCH_RESULTS_WITH_ERROR,
)


@pytest.fixture
def sample_course_metadata():
    """Sample course catalog metadata"""
    return SAMPLE_COURSE_METADATA.copy()


@pytest.fixture
def sample_course_metadata_2():
    """Second sample course metadata"""
    return SAMPLE_COURSE_METADATA_2.copy()


@pytest.fixture
def sample_search_results_success():
    """Sample successful SearchResults"""
    return SAMPLE_SEARCH_RESULTS_SUCCESS


@pytest.fixture
def sample_search_results_empty():
    """Sample empty SearchResults"""
    return SAMPLE_SEARCH_RESULTS_EMPTY


@pytest.fixture
def sample_search_results_with_error():
    """Sample SearchResults with error"""
    return SAMPLE_SEARCH_RESULTS_WITH_ERROR


@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection with controllable behavior"""
    mock_collection = Mock()

    # Default behavior: return empty results
    mock_collection.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

    return mock_collection


@pytest.fixture
def mock_vector_store(mock_chroma_collection):
    """Mock VectorStore with controllable search results"""
    from vector_store import VectorStore

    with patch("vector_store.chromadb.PersistentClient"):
        # Create VectorStore with default max_results=5
        store = VectorStore(
            chroma_path="./test_chroma", embedding_model="all-MiniLM-L6-v2", max_results=5
        )

        # Replace collections with mocks
        store.course_catalog = mock_chroma_collection
        store.course_content = mock_chroma_collection

        return store


@pytest.fixture
def mock_vector_store_with_zero_max_results(mock_chroma_collection):
    """Mock VectorStore with max_results=0 to test the bug"""
    from vector_store import VectorStore

    with patch("vector_store.chromadb.PersistentClient"):
        # Create VectorStore with max_results=0 (the bug)
        store = VectorStore(
            chroma_path="./test_chroma", embedding_model="all-MiniLM-L6-v2", max_results=0
        )

        # Replace collections with mocks
        store.course_catalog = mock_chroma_collection
        store.course_content = mock_chroma_collection

        return store


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    mock_client = Mock()
    mock_messages = Mock()
    mock_client.messages = mock_messages

    # Default: return simple text response
    mock_messages.create.return_value = SAMPLE_ANTHROPIC_TEXT_RESPONSE

    return mock_client


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager"""
    from search_tools import ToolManager

    manager = ToolManager()

    # Mock execute_tool to return canned responses
    original_execute = manager.execute_tool

    def mock_execute(tool_name, **kwargs):
        if tool_name == "search_course_content":
            return "[MCP: Build Rich-Context AI Apps with Anthropic - Lesson 1]\nMCP stands for Model Context Protocol."
        elif tool_name == "get_course_outline":
            return "Course: MCP\nLink: https://example.com/mcp\n\nLessons:\nLesson 1: Introduction"
        return original_execute(tool_name, **kwargs)

    manager.execute_tool = mock_execute

    return manager


@pytest.fixture(params=[0, 1, 5])
def max_results_parametrized(request):
    """Parametrized fixture for testing different max_results values"""
    return request.param


@pytest.fixture
def mock_config():
    """Mock Config object"""
    from dataclasses import dataclass

    @dataclass
    class TestConfig:
        ANTHROPIC_API_KEY: str = "test-api-key"
        ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
        EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
        CHUNK_SIZE: int = 800
        CHUNK_OVERLAP: int = 100
        MAX_RESULTS: int = 5
        MAX_HISTORY: int = 2
        CHROMA_PATH: str = "./test_chroma_db"

    return TestConfig()


@pytest.fixture
def mock_config_with_zero_max_results():
    """Mock Config with MAX_RESULTS=0 (the bug)"""
    from dataclasses import dataclass

    @dataclass
    class TestConfig:
        ANTHROPIC_API_KEY: str = "test-api-key"
        ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
        EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
        CHUNK_SIZE: int = 800
        CHUNK_OVERLAP: int = 100
        MAX_RESULTS: int = 0  # The bug!
        MAX_HISTORY: int = 2
        CHROMA_PATH: str = "./test_chroma_db"

    return TestConfig()
