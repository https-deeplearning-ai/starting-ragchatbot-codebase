"""Shared fixtures for backend tests."""
import sys
import os

# Ensure backend directory is on the path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from config import config
from vector_store import VectorStore
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from ai_generator import AIGenerator
from rag_system import RAGSystem


@pytest.fixture(scope="session")
def vector_store():
    return VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)


@pytest.fixture(scope="session")
def search_tool(vector_store):
    return CourseSearchTool(vector_store)


@pytest.fixture(scope="session")
def ai_generator():
    return AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)


@pytest.fixture(scope="session")
def outline_tool(vector_store):
    return CourseOutlineTool(vector_store)


@pytest.fixture(scope="session")
def tool_manager(search_tool, outline_tool):
    tm = ToolManager()
    tm.register_tool(search_tool)
    tm.register_tool(outline_tool)
    return tm


@pytest.fixture(scope="session")
def rag_system():
    return RAGSystem(config)
