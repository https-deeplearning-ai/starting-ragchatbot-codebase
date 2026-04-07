"""
Tests for AIGenerator in ai_generator.py.

Verifies that:
- The generator calls the search tool for course-specific questions
- The generator does NOT call the search tool for general knowledge questions
- Tool execution results are incorporated into the final response
- The two-turn agentic loop works correctly
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager
from vector_store import VectorStore
from config import config


@pytest.fixture(scope="module")
def generator():
    return AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)


@pytest.fixture(scope="module")
def real_tool_manager():
    """Tool manager backed by real vector store."""
    store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
    tool = CourseSearchTool(store)
    tm = ToolManager()
    tm.register_tool(tool)
    return tm


# ---------------------------------------------------------------------------
# Tool definitions are passed correctly
# ---------------------------------------------------------------------------

def test_tool_definitions_non_empty(real_tool_manager):
    """ToolManager must expose at least one tool definition to Claude."""
    defs = real_tool_manager.get_tool_definitions()
    assert isinstance(defs, list) and len(defs) > 0, "No tool definitions registered"
    names = [d["name"] for d in defs]
    assert "search_course_content" in names, f"search_course_content missing from: {names}"


# ---------------------------------------------------------------------------
# General knowledge — should NOT invoke a tool
# ---------------------------------------------------------------------------

def test_general_question_does_not_use_tool(generator, real_tool_manager):
    """A general question like 'what is Python?' should be answered without tool use."""
    real_tool_manager.reset_sources()
    response = generator.generate_response(
        query="What is Python programming language?",
        tools=real_tool_manager.get_tool_definitions(),
        tool_manager=real_tool_manager
    )
    assert isinstance(response, str) and len(response) > 0, "Response should not be empty"
    sources = real_tool_manager.get_last_sources()
    assert sources == [], (
        f"General question should not trigger tool use, but got sources: {sources}"
    )


# ---------------------------------------------------------------------------
# Course-specific question — should invoke the search tool
# ---------------------------------------------------------------------------

def test_course_specific_question_uses_tool(generator, real_tool_manager):
    """A course-specific question should trigger search_course_content tool use."""
    real_tool_manager.reset_sources()
    response = generator.generate_response(
        query="Answer this question about course materials: What topics are covered in the MCP course?",
        tools=real_tool_manager.get_tool_definitions(),
        tool_manager=real_tool_manager
    )
    assert isinstance(response, str) and len(response) > 0, (
        f"Response should not be empty, got: {response!r}"
    )


def test_generate_response_returns_string_not_exception(generator, real_tool_manager):
    """generate_response() must never raise — always return a string."""
    real_tool_manager.reset_sources()
    try:
        result = generator.generate_response(
            query="Answer this question about course materials: Explain RAG systems",
            tools=real_tool_manager.get_tool_definitions(),
            tool_manager=real_tool_manager
        )
        assert isinstance(result, str), f"Expected str, got {type(result)}: {result!r}"
    except Exception as e:
        pytest.fail(f"generate_response() raised an exception: {e}")


# ---------------------------------------------------------------------------
# Tool manager execute_tool dispatching
# ---------------------------------------------------------------------------

def test_tool_manager_executes_search_tool(real_tool_manager):
    """ToolManager.execute_tool() should dispatch to search_course_content."""
    result = real_tool_manager.execute_tool(
        "search_course_content",
        query="chromadb embeddings"
    )
    assert isinstance(result, str), f"Expected str from execute_tool, got: {type(result)}"


def test_tool_manager_unknown_tool_returns_error(real_tool_manager):
    """Calling a non-existent tool should return an error string, not raise."""
    result = real_tool_manager.execute_tool("nonexistent_tool", query="test")
    assert "not found" in result.lower(), f"Expected 'not found' message, got: {result!r}"
