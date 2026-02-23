"""Shared test helpers and factories."""

import sys
import os
from dataclasses import dataclass
from unittest.mock import MagicMock

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vector_store import SearchResults


@dataclass
class MockConfig:
    ANTHROPIC_API_KEY: str = "test-key"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = "./test_chroma_db"


def make_search_results(documents=None, metadata=None, distances=None, error=None):
    """Factory for SearchResults objects."""
    if error:
        return SearchResults.empty(error)
    return SearchResults(
        documents=documents or [],
        metadata=metadata or [],
        distances=distances or [],
        error=None,
    )


def make_valid_search_results(n=2):
    """Create valid search results with n items."""
    docs = [f"Content about topic {i}" for i in range(n)]
    meta = [
        {"course_title": f"Course {i}", "lesson_number": i + 1, "chunk_index": i}
        for i in range(n)
    ]
    dists = [0.1 * (i + 1) for i in range(n)]
    return SearchResults(documents=docs, metadata=meta, distances=dists)


def make_anthropic_response(content_blocks, stop_reason="end_turn"):
    """Factory for mock Anthropic API responses."""
    mock_response = MagicMock()
    mock_response.stop_reason = stop_reason

    blocks = []
    for block in content_blocks:
        mock_block = MagicMock()
        mock_block.type = block["type"]
        if block["type"] == "text":
            mock_block.text = block["text"]
        elif block["type"] == "tool_use":
            mock_block.id = block["id"]
            mock_block.name = block["name"]
            mock_block.input = block["input"]
        blocks.append(mock_block)

    mock_response.content = blocks
    return mock_response
