"""
Shared mock factories for building fake Anthropic API responses and SearchResults.
Imported directly by test files (not via conftest auto-discovery).
"""
from unittest.mock import MagicMock
from vector_store import SearchResults


def make_text_response(text: str) -> MagicMock:
    """Simulates an Anthropic response with stop_reason='end_turn' and a text block."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def make_tool_use_response(tool_name: str, tool_id: str, tool_input: dict) -> MagicMock:
    """Simulates an Anthropic response with stop_reason='tool_use' and a tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.id = tool_id
    block.input = tool_input
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response


def make_mixed_response(tool_name: str, tool_id: str, tool_input: dict) -> MagicMock:
    """Simulates a response with both a text block and a tool_use block."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I'll search for that."

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.id = tool_id
    tool_block.input = tool_input

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [text_block, tool_block]
    return response


def make_search_results(docs=None, meta=None, distances=None) -> SearchResults:
    """Creates a populated SearchResults for use in VectorStore mocks."""
    docs = docs or ["Lesson content here."]
    meta = meta or [{"course_title": "Python Basics", "lesson_number": 1}]
    distances = distances or ([0.1] * len(docs))
    return SearchResults(documents=docs, metadata=meta, distances=distances)
