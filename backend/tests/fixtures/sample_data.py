"""Sample data for testing the RAG system"""
import json
from vector_store import SearchResults

# Sample course metadata
SAMPLE_COURSE_METADATA = {
    "title": "MCP: Build Rich-Context AI Apps with Anthropic",
    "instructor": "Test Instructor",
    "course_link": "https://example.com/course/mcp",
    "lessons_json": json.dumps([
        {
            "lesson_number": 1,
            "lesson_title": "Introduction to MCP",
            "lesson_link": "https://example.com/course/mcp/lesson1"
        },
        {
            "lesson_number": 2,
            "lesson_title": "Core Concepts",
            "lesson_link": "https://example.com/course/mcp/lesson2"
        },
        {
            "lesson_number": 3,
            "lesson_title": "Building Applications",
            "lesson_link": "https://example.com/course/mcp/lesson3"
        }
    ]),
    "lesson_count": 3
}

SAMPLE_COURSE_METADATA_2 = {
    "title": "Advanced Retrieval for AI with Chroma",
    "instructor": "Another Instructor",
    "course_link": "https://example.com/course/chroma",
    "lessons_json": json.dumps([
        {
            "lesson_number": 1,
            "lesson_title": "Vector Databases",
            "lesson_link": "https://example.com/course/chroma/lesson1"
        }
    ]),
    "lesson_count": 1
}

# Sample course content chunks
SAMPLE_COURSE_CHUNKS = [
    {
        "content": "MCP stands for Model Context Protocol. It is a framework for building rich-context AI applications.",
        "metadata": {
            "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "lesson_number": 1,
            "chunk_index": 0
        }
    },
    {
        "content": "The Model Context Protocol enables AI models to access external data sources and tools seamlessly.",
        "metadata": {
            "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "lesson_number": 1,
            "chunk_index": 1
        }
    },
    {
        "content": "MCP servers provide contextual information to LLMs through a standardized protocol.",
        "metadata": {
            "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "lesson_number": 2,
            "chunk_index": 2
        }
    }
]

# Sample SearchResults objects
SAMPLE_SEARCH_RESULTS_EMPTY = SearchResults(
    documents=[],
    metadata=[],
    distances=[],
    error=None
)

SAMPLE_SEARCH_RESULTS_WITH_ERROR = SearchResults(
    documents=[],
    metadata=[],
    distances=[],
    error="No course found matching 'NonExistent'"
)

SAMPLE_SEARCH_RESULTS_SUCCESS = SearchResults(
    documents=[
        "MCP stands for Model Context Protocol. It is a framework for building rich-context AI applications.",
        "The Model Context Protocol enables AI models to access external data sources and tools seamlessly."
    ],
    metadata=[
        {
            "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "lesson_number": 1,
            "chunk_index": 0
        },
        {
            "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "lesson_number": 1,
            "chunk_index": 1
        }
    ],
    distances=[0.15, 0.23],
    error=None
)

# Sample Anthropic API responses
class MockTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text

class MockToolUseBlock:
    def __init__(self, tool_id, name, input_data):
        self.type = "tool_use"
        self.id = tool_id
        self.name = name
        self.input = input_data

class MockAnthropicResponse:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason
        self.id = "msg_test123"
        self.model = "claude-sonnet-4-20250514"
        self.role = "assistant"

# Sample tool use response
SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE = MockAnthropicResponse(
    content=[
        MockToolUseBlock(
            tool_id="tool_test123",
            name="search_course_content",
            input_data={"query": "What is MCP?"}
        )
    ],
    stop_reason="tool_use"
)

# Sample final text response
SAMPLE_ANTHROPIC_TEXT_RESPONSE = MockAnthropicResponse(
    content=[
        MockTextBlock("MCP stands for Model Context Protocol, a framework for building rich-context AI applications.")
    ],
    stop_reason="end_turn"
)

# Sample final response after tool use
SAMPLE_ANTHROPIC_FINAL_RESPONSE = MockAnthropicResponse(
    content=[
        MockTextBlock("MCP stands for Model Context Protocol. It enables AI models to access external data sources through a standardized protocol.")
    ],
    stop_reason="end_turn"
)

# Sample second tool use response (for round 2 in sequential calling)
SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE_2 = MockAnthropicResponse(
    content=[
        MockToolUseBlock(
            tool_id="tool_test456",
            name="get_course_outline",
            input_data={"course_name": "MCP"}
        )
    ],
    stop_reason="tool_use"
)

# Sample response for third round (after 2 tool uses)
SAMPLE_ANTHROPIC_FINAL_RESPONSE_AFTER_TWO_ROUNDS = MockAnthropicResponse(
    content=[
        MockTextBlock("Based on the course outline and content search, lesson 4 covers building applications with MCP.")
    ],
    stop_reason="end_turn"
)

def create_mock_always_tool_use():
    """Returns tool_use response indefinitely for testing round limits"""
    return MockAnthropicResponse(
        content=[
            MockToolUseBlock("tool_infinite", "search_course_content", {"query": "test"})
        ],
        stop_reason="tool_use"
    )
