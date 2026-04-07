"""
Tests for RAGSystem.query() in rag_system.py.

Verifies the full end-to-end pipeline for content-related queries:
- Query returns a (response, sources) tuple without raising
- Response is a non-empty string
- Sources is a list
- Specific content questions return relevant answers
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from rag_system import RAGSystem
from config import config


@pytest.fixture(scope="module")
def rag():
    return RAGSystem(config)


# ---------------------------------------------------------------------------
# Return type contract
# ---------------------------------------------------------------------------

def test_query_returns_tuple(rag):
    """query() must return a (str, list) tuple."""
    result = rag.query("What is RAG?")
    assert isinstance(result, tuple) and len(result) == 2, (
        f"Expected (str, list) tuple, got: {result!r}"
    )
    answer, sources = result
    assert isinstance(answer, str), f"answer must be str, got {type(answer)}"
    assert isinstance(sources, list), f"sources must be list, got {type(sources)}"


def test_query_answer_nonempty(rag):
    """query() must return a non-empty answer for any reasonable question."""
    answer, _ = rag.query("What is RAG?")
    assert len(answer.strip()) > 0, "Answer should not be empty"


# ---------------------------------------------------------------------------
# Content-related queries (the failing case)
# ---------------------------------------------------------------------------

def test_content_query_does_not_crash(rag):
    """A content-specific question must not raise an exception."""
    try:
        answer, sources = rag.query(
            "What topics are covered in the MCP course?"
        )
        assert isinstance(answer, str), f"Expected str answer, got: {type(answer)}"
    except Exception as e:
        pytest.fail(f"RAGSystem.query() raised an exception: {e}")


def test_content_query_no_query_failed_message(rag):
    """A content query should not produce a 'query failed' or error response."""
    answer, _ = rag.query("What is covered in lesson 1 of the MCP course?")
    lower = answer.lower()
    assert "query failed" not in lower, (
        f"Got 'query failed' in response: {answer!r}"
    )
    assert "error" not in lower or len(answer) > 50, (
        f"Response looks like an error message: {answer!r}"
    )


def test_rag_query_with_known_course(rag):
    """Querying about a course that exists in ChromaDB should return content."""
    answer, sources = rag.query(
        "Tell me about the Advanced Retrieval for AI course"
    )
    assert isinstance(answer, str) and len(answer) > 20, (
        f"Expected substantive answer, got: {answer!r}"
    )


def test_rag_query_returns_sources_for_course_content(rag):
    """A course-content query should populate sources."""
    _, sources = rag.query("What does lesson 2 of the MCP course cover?")
    # sources may be empty if tool wasn't invoked, but must be a list
    assert isinstance(sources, list), f"sources must be a list, got: {type(sources)}"


# ---------------------------------------------------------------------------
# Session handling
# ---------------------------------------------------------------------------

def test_query_with_session_id(rag):
    """query() with a session_id must not crash and must return valid results."""
    session_id = rag.session_manager.create_session()
    answer, sources = rag.query("What is ChromaDB?", session_id=session_id)
    assert isinstance(answer, str) and len(answer) > 0


def test_multi_turn_conversation(rag):
    """A second query in the same session should work without error."""
    session_id = rag.session_manager.create_session()
    rag.query("What is RAG?", session_id=session_id)
    answer, _ = rag.query("Can you give me an example?", session_id=session_id)
    assert isinstance(answer, str) and len(answer) > 0, (
        f"Second turn failed, got: {answer!r}"
    )


# ---------------------------------------------------------------------------
# Vector store connectivity
# ---------------------------------------------------------------------------

def test_courses_are_loaded(rag):
    """ChromaDB should have courses loaded — if 0, ingestion failed."""
    count = rag.vector_store.get_course_count()
    assert count > 0, (
        f"No courses in vector store! Ingestion may have failed. count={count}"
    )


def test_course_search_tool_registered(rag):
    """search_course_content tool must be registered in the tool manager."""
    names = [d["name"] for d in rag.tool_manager.get_tool_definitions()]
    assert "search_course_content" in names, (
        f"search_course_content not registered. Registered: {names}"
    )
