"""Pytest configuration and shared fixtures"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

# Add backend directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore"""
    mock_store = Mock()
    mock_store.search = Mock()
    mock_store.get_course_outline = Mock()
    return mock_store


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing"""
    return SearchResults(
        documents=[
            "This is lesson content about Python basics",
            "Python functions and scope explanation"
        ],
        metadata=[
            {
                "course_title": "Introduction to Python",
                "lesson_number": 1,
                "lesson_link": "https://example.com/lesson/1",
                "chunk_index": 0
            },
            {
                "course_title": "Introduction to Python",
                "lesson_number": 1,
                "lesson_link": "https://example.com/lesson/1",
                "chunk_index": 1
            }
        ],
        distances=[0.1, 0.15]
    )


@pytest.fixture
def empty_search_results():
    """Create empty search results"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )


@pytest.fixture
def error_search_results():
    """Create search results with error"""
    return SearchResults.empty("Search failed: database error")


@pytest.fixture
def sample_course():
    """Create a sample course object"""
    return Course(
        title="Introduction to Python",
        instructor="John Doe",
        course_link="https://example.com/python",
        lessons=[
            Lesson(
                lesson_number=1,
                title="Getting Started",
                lesson_link="https://example.com/lesson/1"
            ),
            Lesson(
                lesson_number=2,
                title="Variables and Data Types",
                lesson_link="https://example.com/lesson/2"
            )
        ]
    )


@pytest.fixture
def sample_course_chunks():
    """Create sample course chunks"""
    return [
        CourseChunk(
            course_title="Introduction to Python",
            lesson_number=1,
            lesson_link="https://example.com/lesson/1",
            content="Python is a high-level programming language...",
            chunk_index=0
        ),
        CourseChunk(
            course_title="Introduction to Python",
            lesson_number=1,
            lesson_link="https://example.com/lesson/1",
            content="Variables are used to store data values...",
            chunk_index=1
        )
    ]


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client"""
    mock_client = Mock()
    mock_messages = Mock()

    # Create a mock response
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [Mock(text="This is a direct answer")]

    mock_messages.create = Mock(return_value=mock_response)
    mock_client.messages = mock_messages

    return mock_client


@pytest.fixture
def mock_anthropic_client_with_tool_use():
    """Create a mock Anthropic client that returns tool_use response"""
    mock_client = Mock()
    mock_messages = Mock()

    # First response: tool use
    tool_use_content = Mock()
    tool_use_content.type = "tool_use"
    tool_use_content.name = "search_course_content"
    tool_use_content.id = "tool_123"
    tool_use_content.input = {"query": "python basics"}

    first_response = Mock()
    first_response.stop_reason = "tool_use"
    first_response.content = [tool_use_content]

    # Second response: final answer
    second_response = Mock()
    second_response.stop_reason = "end_turn"
    second_response.content = [Mock(text="Here's the answer with search results")]

    # Configure messages.create to return different responses on consecutive calls
    mock_messages.create = Mock(side_effect=[first_response, second_response])
    mock_client.messages = mock_messages

    return mock_client


@pytest.fixture
def mock_anthropic_client_two_tool_rounds():
    """Create a mock Anthropic client that simulates two sequential tool-use rounds"""
    mock_client = Mock()
    mock_messages = Mock()

    # First response: tool use (search_course_content)
    tool_use_1 = Mock()
    tool_use_1.type = "tool_use"
    tool_use_1.name = "search_course_content"
    tool_use_1.id = "tool_001"
    tool_use_1.input = {"query": "python basics"}

    first_response = Mock()
    first_response.stop_reason = "tool_use"
    first_response.content = [tool_use_1]

    # Second response: tool use (get_course_outline)
    tool_use_2 = Mock()
    tool_use_2.type = "tool_use"
    tool_use_2.name = "get_course_outline"
    tool_use_2.id = "tool_002"
    tool_use_2.input = {"course_title": "Python Course"}

    second_response = Mock()
    second_response.stop_reason = "tool_use"
    second_response.content = [tool_use_2]

    # Third response: final answer
    third_response = Mock()
    third_response.stop_reason = "end_turn"
    third_response.content = [Mock(text="Final answer using both results")]

    mock_messages.create = Mock(side_effect=[first_response, second_response, third_response])
    mock_client.messages = mock_messages

    return mock_client


@pytest.fixture
def mock_anthropic_client_round_cap():
    """Create a mock Anthropic client that tests round cap enforcement"""
    mock_client = Mock()
    mock_messages = Mock()

    # First response: tool use
    tool_use_1 = Mock()
    tool_use_1.type = "tool_use"
    tool_use_1.name = "search_course_content"
    tool_use_1.id = "tool_001"
    tool_use_1.input = {"query": "python basics"}

    first_response = Mock()
    first_response.stop_reason = "tool_use"
    first_response.content = [tool_use_1]

    # Second response: still tool use (would want a third call, but cap is hit)
    tool_use_2 = Mock()
    tool_use_2.type = "tool_use"
    tool_use_2.name = "search_course_content"
    tool_use_2.id = "tool_002"
    tool_use_2.input = {"query": "more python"}

    second_response = Mock()
    second_response.stop_reason = "tool_use"
    second_response.content = [tool_use_2]

    # Third response: forced final call without tools
    third_response = Mock()
    third_response.stop_reason = "end_turn"
    third_response.content = [Mock(text="Answer after round cap enforced")]

    mock_messages.create = Mock(side_effect=[first_response, second_response, third_response])
    mock_client.messages = mock_messages

    return mock_client


@pytest.fixture
def config_mock():
    """Create a mock config object"""
    config = Mock()
    config.ANTHROPIC_API_KEY = "test-key-123"
    config.ANTHROPIC_MODEL = "claude-haiku-4-5"
    config.CHUNK_SIZE = 1000
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.CHROMA_PATH = "./test_chroma_db"
    return config
