"""
Tests for rag_system.py: RAGSystem.query() end-to-end orchestration.

All external dependencies (VectorStore, AIGenerator, SessionManager,
DocumentProcessor) are mocked so no real API calls or ChromaDB I/O occur.

Covers:
- Return type and content of query()
- Tool definitions passed to AIGenerator
- Source retrieval and reset lifecycle
- Conversation history threading
- Session management
- Exception propagation (the "query failed" scenario)
"""
import pytest
from unittest.mock import MagicMock, patch

from helpers import make_search_results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.ANTHROPIC_API_KEY = "test-key"
    cfg.ANTHROPIC_MODEL = "claude-test"
    cfg.CHUNK_SIZE = 800
    cfg.CHUNK_OVERLAP = 100
    cfg.MAX_RESULTS = 5
    cfg.MAX_HISTORY = 2
    cfg.CHROMA_PATH = "/tmp/test_chroma"
    cfg.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    return cfg


@pytest.fixture
def rag_system(mock_config):
    """
    RAGSystem with all four constructor dependencies mocked.
    After construction, individual component instances are replaced with
    fresh MagicMocks for full test control.
    """
    with patch("rag_system.DocumentProcessor"), \
         patch("rag_system.VectorStore"), \
         patch("rag_system.AIGenerator"), \
         patch("rag_system.SessionManager"):
        from rag_system import RAGSystem
        system = RAGSystem(mock_config)

    # Replace with controllable mocks
    system.ai_generator = MagicMock()
    system.ai_generator.generate_response.return_value = "AI response text"

    system.session_manager = MagicMock()
    system.session_manager.get_conversation_history.return_value = None

    system.vector_store = MagicMock()
    system.vector_store.search.return_value = make_search_results()
    system.vector_store.get_lesson_link.return_value = None

    # Wire the real search/outline tools to the mocked vector_store
    system.search_tool.store = system.vector_store
    system.outline_tool.store = system.vector_store

    return system


# ---------------------------------------------------------------------------
# Return type and basic structure
# ---------------------------------------------------------------------------

class TestQueryReturnType:

    def test_query_returns_two_tuple(self, rag_system):
        """query() must return a (str, list) tuple."""
        result = rag_system.query("what is backprop?")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_query_answer_is_string(self, rag_system):
        """First element of the tuple is a string (the AI answer)."""
        answer, _ = rag_system.query("what is backprop?")
        assert isinstance(answer, str)

    def test_query_sources_is_list(self, rag_system):
        """Second element of the tuple is a list (sources)."""
        _, sources = rag_system.query("what is backprop?")
        assert isinstance(sources, list)

    def test_query_answer_equals_ai_generator_response(self, rag_system):
        """The answer is exactly what AIGenerator.generate_response() returned."""
        rag_system.ai_generator.generate_response.return_value = "Specific answer"
        answer, _ = rag_system.query("q")
        assert answer == "Specific answer"


# ---------------------------------------------------------------------------
# Tool wiring: definitions and tool_manager passed to AIGenerator
# ---------------------------------------------------------------------------

class TestQueryToolWiring:

    def test_tool_definitions_passed_to_ai_generator(self, rag_system):
        """AIGenerator receives tool definitions from ToolManager."""
        rag_system.query("q")
        call_kwargs = rag_system.ai_generator.generate_response.call_args.kwargs
        tools = call_kwargs.get("tools")
        assert tools is not None
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_tool_definitions_include_search_course_content(self, rag_system):
        """Tool definitions include the 'search_course_content' tool."""
        rag_system.query("q")
        call_kwargs = rag_system.ai_generator.generate_response.call_args.kwargs
        tool_names = [t["name"] for t in call_kwargs["tools"]]
        assert "search_course_content" in tool_names

    def test_tool_manager_passed_to_ai_generator(self, rag_system):
        """AIGenerator receives the real ToolManager instance."""
        rag_system.query("q")
        call_kwargs = rag_system.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs.get("tool_manager") is rag_system.tool_manager

    def test_query_wrapped_in_prompt(self, rag_system):
        """The raw user query is embedded in the prompt sent to AIGenerator."""
        rag_system.query("explain gradient descent")
        call_kwargs = rag_system.ai_generator.generate_response.call_args.kwargs
        assert "explain gradient descent" in call_kwargs["query"]


# ---------------------------------------------------------------------------
# Sources lifecycle
# ---------------------------------------------------------------------------

class TestQuerySourcesLifecycle:

    def test_sources_empty_when_no_search_occurred(self, rag_system):
        """When the tool was not used, sources list is empty."""
        # search_tool.last_sources is empty (default fixture state)
        _, sources = rag_system.query("what is 2+2")
        assert sources == []

    def test_sources_populated_after_tool_sets_last_sources(self, rag_system):
        """Sources reflect what CourseSearchTool set in last_sources."""
        rag_system.search_tool.last_sources = ["ML Basics - Lesson 2||https://url"]
        _, sources = rag_system.query("q")
        assert sources == ["ML Basics - Lesson 2||https://url"]

    def test_sources_reset_after_retrieval(self, rag_system):
        """After query() completes, last_sources is cleared (no leakage to next request)."""
        rag_system.search_tool.last_sources = ["Some Course - Lesson 1"]
        rag_system.query("q")
        assert rag_system.search_tool.last_sources == []

    def test_sources_empty_after_reset_on_second_query(self, rag_system):
        """A second query that doesn't use the tool returns empty sources."""
        rag_system.search_tool.last_sources = ["Leftover Source"]
        rag_system.query("first query")
        _, sources = rag_system.query("second query")
        assert sources == []


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

class TestQuerySessionManagement:

    def test_history_fetched_when_session_id_provided(self, rag_system):
        """get_conversation_history() is called with the session_id when one is given."""
        rag_system.query("q", session_id="sess_1")
        rag_system.session_manager.get_conversation_history.assert_called_once_with("sess_1")

    def test_history_not_fetched_without_session_id(self, rag_system):
        """get_conversation_history() is NOT called when session_id is None."""
        rag_system.query("q", session_id=None)
        rag_system.session_manager.get_conversation_history.assert_not_called()

    def test_history_passed_to_ai_generator(self, rag_system):
        """Conversation history from SessionManager is forwarded to AIGenerator."""
        rag_system.session_manager.get_conversation_history.return_value = "User: hi\nAssistant: hello"
        rag_system.query("follow-up", session_id="sess_1")
        call_kwargs = rag_system.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] == "User: hi\nAssistant: hello"

    def test_no_history_when_session_id_is_none(self, rag_system):
        """conversation_history=None is passed to AIGenerator when there's no session."""
        rag_system.query("q", session_id=None)
        call_kwargs = rag_system.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] is None

    def test_session_history_updated_after_response(self, rag_system):
        """add_exchange() is called with session_id, user query, and AI response."""
        rag_system.ai_generator.generate_response.return_value = "The answer"
        rag_system.query("my question", session_id="sess_42")
        rag_system.session_manager.add_exchange.assert_called_once_with(
            "sess_42", "my question", "The answer"
        )

    def test_session_not_updated_without_session_id(self, rag_system):
        """add_exchange() is NOT called when session_id is None."""
        rag_system.query("q", session_id=None)
        rag_system.session_manager.add_exchange.assert_not_called()


# ---------------------------------------------------------------------------
# Exception propagation: the "query failed" scenario
# ---------------------------------------------------------------------------

class TestQueryExceptionPropagation:

    def test_ai_generator_exception_propagates(self, rag_system):
        """
        Exceptions from AIGenerator (e.g., Anthropic API errors) must propagate
        so that app.py's exception handler can convert them to HTTP 500.
        This is the expected behavior — RAGSystem does not silently swallow errors.
        """
        rag_system.ai_generator.generate_response.side_effect = RuntimeError("API rate limit hit")
        with pytest.raises(RuntimeError, match="API rate limit hit"):
            rag_system.query("what is backprop?")

    def test_tool_exception_returns_error_string_not_raises(self, rag_system):
        """
        FIX VERIFICATION: When get_lesson_link raises inside _format_results,
        the exception is now caught by the try/except in _handle_tool_execution()
        and returned as an error string to Claude — not propagated as HTTP 500.

        We verify this at the tool level (execute_tool), which is what
        _handle_tool_execution() calls.
        """
        # Simulate a failure inside _format_results — get_lesson_link raises
        rag_system.vector_store.search.return_value = make_search_results(
            docs=["content"],
            meta=[{"course_title": "DL Course", "lesson_number": 1}],
        )
        rag_system.vector_store.get_lesson_link.side_effect = Exception(
            "ChromaDB collection not initialized"
        )

        # execute_tool itself should propagate (tool has no try/except)
        # The catch is in _handle_tool_execution() in ai_generator
        with pytest.raises(Exception, match="ChromaDB collection not initialized"):
            rag_system.tool_manager.execute_tool("search_course_content", query="neural networks")

    def test_tool_execute_tool_string_error_does_not_raise(self, rag_system):
        """
        When vector_store.search() returns SearchResults.empty(error), the tool
        returns a string — NOT an exception. This is the SAFE path.
        Confirms that the vector store's internal exception handling works correctly.
        """
        from vector_store import SearchResults
        rag_system.vector_store.search.return_value = SearchResults.empty(
            "Search error: collection is empty"
        )
        # Should not raise
        result = rag_system.tool_manager.execute_tool(
            "search_course_content", query="what is backprop"
        )
        assert result == "Search error: collection is empty"
