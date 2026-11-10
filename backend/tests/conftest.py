"""Shared fixtures. Tests mock ChromaDB and the Anthropic client: no network, no embeddings."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vector_store import SearchResults  # noqa: E402

MCP = "MCP: Build Rich-Context AI Apps with Anthropic"


def make_results(chunks, error=None):
    """chunks: list of (text, course_title, lesson_number, chunk_index)"""
    if error:
        return SearchResults.empty(error)
    return SearchResults(
        documents=[c[0] for c in chunks],
        metadata=[
            {"course_title": c[1], "lesson_number": c[2], "chunk_index": c[3]}
            for c in chunks
        ],
        distances=[0.1 * i for i in range(len(chunks))],
    )


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_lesson_link.side_effect = (
        lambda title, n: f"https://example.com/{title[:3].lower()}/lesson{n}"
    )
    return store


# --- Fake Anthropic responses -------------------------------------------------

def text_block(text):
    return SimpleNamespace(type="text", text=text)


def thinking_block(thinking="hmm"):
    return SimpleNamespace(type="thinking", thinking=thinking)


def tool_use_block(name, tool_input, block_id="toolu_1"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=block_id)


def response(*blocks, stop_reason="end_turn"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason)
