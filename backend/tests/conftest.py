"""
Shared pytest fixtures for the RAG chatbot test suite.

The FastAPI app in app.py has two side effects on import that must be suppressed
in tests:
  1. RAGSystem(config) — connects to ChromaDB and loads embeddings
  2. app.mount("/", StaticFiles(directory="../frontend")) — the frontend directory
     does not exist in the test environment

Both are patched before the module is imported so the app loads cleanly.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch


def _import_app_with_patches():
    """
    Import app.py while RAGSystem and StaticFiles are mocked out.

    The patches must be active during the import because app.py calls
    RAGSystem(config) and StaticFiles(...) at module level. Once the module
    is loaded those names are bound locally, so stopping the patches
    afterwards is safe.
    """
    mock_rag = MagicMock()
    with patch("rag_system.RAGSystem", return_value=mock_rag), \
         patch("fastapi.staticfiles.StaticFiles"):
        import app as app_module
    # Ensure the module-level rag_system variable points to our mock
    app_module.rag_system = mock_rag
    return app_module, mock_rag


_app_module, _mock_rag_instance = _import_app_with_patches()


@pytest.fixture
def mock_rag():
    """
    The mock RAGSystem instance wired into the FastAPI app.

    Call tracking and side effects are cleared between tests so that
    assertions in one test cannot bleed into the next.
    """
    _mock_rag_instance.reset_mock(side_effect=True)
    return _mock_rag_instance


@pytest.fixture
def client():
    """FastAPI TestClient backed by the patched app."""
    from fastapi.testclient import TestClient
    return TestClient(_app_module.app)


@pytest.fixture
def sample_query_payload():
    return {"query": "What is machine learning?", "session_id": "test-session-123"}


@pytest.fixture
def sample_rag_response():
    return ("Machine learning is a subset of AI.", ["Course A - Lesson 1"])
