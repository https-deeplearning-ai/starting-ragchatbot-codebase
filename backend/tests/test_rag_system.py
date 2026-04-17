"""
Integration tests for RAGSystem.query().

Patches VectorStore, DocumentProcessor, and the Anthropic client so no real
ChromaDB or API calls occur. Lets the real RAGSystem, ToolManager,
CourseSearchTool, and AIGenerator code run.

Diagnostic focus: Does the full pipeline assemble correctly?
Do sources flow back from tool to response? Does session history update?
"""
import pytest
from unittest.mock import MagicMock, patch
from rag_system import RAGSystem
from vector_store import SearchResults
from tests.conftest import make_text_response, make_tool_use_response


@pytest.fixture
def mock_config():
    """Minimal config that prevents real ChromaDB and Anthropic initialization."""
    cfg = MagicMock()
    cfg.ANTHROPIC_API_KEY = "sk-test-fake"
    cfg.ANTHROPIC_MODEL = "claude-3-haiku-20240307"
    cfg.CHROMA_PATH = ":memory:"
    cfg.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    cfg.MAX_RESULTS = 5
    cfg.MAX_HISTORY = 2
    cfg.CHUNK_SIZE = 800
    cfg.CHUNK_OVERLAP = 100
    return cfg


@pytest.fixture
def rag_system_with_mocks(mock_config, sample_search_results):
    """
    RAGSystem with VectorStore and Anthropic client both mocked.
    Yields (system, mock_vs_instance, mock_anthropic_client).
    """
    with patch("rag_system.VectorStore") as MockVS, \
         patch("rag_system.DocumentProcessor"), \
         patch("ai_generator.anthropic.Anthropic") as MockAnthropic:

        mock_vs_instance = MagicMock()
        mock_vs_instance.search.return_value = sample_search_results
        mock_vs_instance.get_lesson_link.return_value = "https://example.com/lesson/1"
        MockVS.return_value = mock_vs_instance

        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client

        system = RAGSystem(mock_config)
        yield system, mock_vs_instance, mock_client


class TestRAGSystemQueryHappyPath:

    def test_query_returns_tuple_of_answer_and_sources(self, rag_system_with_mocks):
        """
        WHAT: RAGSystem.query() returns a 2-tuple (str, list).
        ASSERT: result[0] is str, result[1] is list.
        FAILURE MEANS: API contract broken — app.py crashes unpacking (answer, sources).
        """
        system, _, mock_client = rag_system_with_mocks
        mock_client.messages.create.return_value = make_text_response("General answer.")
        answer, sources = system.query("What is Python?")
        assert isinstance(answer, str)
        assert isinstance(sources, list)

    def test_query_prompt_wraps_user_question(self, rag_system_with_mocks):
        """
        WHAT: RAGSystem.query() prepends the 'Answer this question about course materials:'
              prefix to the user query before calling generate_response.
        ASSERT: The message content sent to Claude starts with that prefix.
        FAILURE MEANS: Prompt framing confirmed — this framing may suppress tool use (Bug 5).
        """
        system, _, mock_client = rag_system_with_mocks
        mock_client.messages.create.return_value = make_text_response("ok")
        system.query("What are variables?")
        call_kwargs = mock_client.messages.create.call_args[1]
        user_message_content = call_kwargs["messages"][0]["content"]
        assert "Answer this question about course materials:" in user_message_content

    def test_query_with_tool_use_returns_sources(self, rag_system_with_mocks):
        """
        WHAT: When Claude uses the search tool and results are found, sources list is non-empty.
        ASSERT: sources has at least one entry with 'label' key.
        FAILURE MEANS: Frontend never displays source links even on successful searches.
        """
        system, _, mock_client = rag_system_with_mocks
        tool_response = make_tool_use_response("search_course_content", {"query": "python"})
        final_response = make_text_response("Python is a programming language.")
        mock_client.messages.create.side_effect = [tool_response, final_response]

        answer, sources = system.query("What is Python?")
        assert answer == "Python is a programming language."
        assert len(sources) > 0
        assert "label" in sources[0]

    def test_query_resets_sources_after_retrieval(self, rag_system_with_mocks):
        """
        WHAT: After query() retrieves sources, reset_sources() is called so the next
              query doesn't inherit stale sources.
        ASSERT: Second query's sources list is empty (direct response, no tool use).
        FAILURE MEANS: Sources from query N bleed into query N+1 in the frontend.
        """
        system, _, mock_client = rag_system_with_mocks
        tool_response = make_tool_use_response("search_course_content", {"query": "python"})
        direct_response = make_text_response("General knowledge answer.")

        # First query: tool use
        mock_client.messages.create.side_effect = [tool_response, make_text_response("Python answer.")]
        system.query("What is Python?")

        # Second query: direct response (no tool use)
        mock_client.messages.create.side_effect = [direct_response]
        _, sources2 = system.query("What is 2 + 2?")
        assert sources2 == []


class TestRAGSystemSessionHandling:

    def test_query_without_session_id_returns_answer(self, rag_system_with_mocks):
        """
        WHAT: query() called without session_id does not crash.
        ASSERT: answer is a non-empty string.
        FAILURE MEANS: Session handling broken for anonymous (stateless) queries.
        """
        system, _, mock_client = rag_system_with_mocks
        mock_client.messages.create.return_value = make_text_response("Answer.")
        answer, _ = system.query("test", session_id=None)
        assert len(answer) > 0

    def test_query_with_new_session_id_does_not_crash(self, rag_system_with_mocks):
        """
        WHAT: query() with a fresh session_id (not yet in sessions dict) works correctly.
        ASSERT: No exception; answer returned as str.
        FAILURE MEANS: get_conversation_history() crashes on unknown session_id.
        """
        system, _, mock_client = rag_system_with_mocks
        mock_client.messages.create.return_value = make_text_response("Answer.")
        answer, _ = system.query("test", session_id="brand-new-session-99")
        assert isinstance(answer, str)

    def test_query_updates_session_history_after_response(self, rag_system_with_mocks):
        """
        WHAT: After a successful query, the exchange is stored in session history.
        ASSERT: get_conversation_history() returns a string containing the user query.
        FAILURE MEANS: Conversation context never accumulates; multi-turn dialogue is broken.
        """
        system, _, mock_client = rag_system_with_mocks
        mock_client.messages.create.return_value = make_text_response("Answer to hello.")
        session_id = system.session_manager.create_session()
        system.query("hello", session_id=session_id)
        history = system.session_manager.get_conversation_history(session_id)
        assert "hello" in history


class TestRAGSystemErrorPropagation:

    def test_query_when_vector_store_errors_claude_receives_error_string(self, rag_system_with_mocks):
        """
        WHAT: When VectorStore.search returns error SearchResults, the error string
              reaches Claude as a tool result. Claude's final answer is its text,
              not a Python exception.
        ASSERT: answer is a string (no exception propagated).
        FAILURE MEANS: Unhandled exception → FastAPI 500. If this passes but user sees
                       'query failed', the bug is Claude saying so verbally, not an HTTP error.
        """
        system, mock_vs, mock_client = rag_system_with_mocks
        mock_vs.search.return_value = SearchResults.empty(
            "Search error: Number of requested results 5 is greater than number of elements in index 0"
        )
        tool_response = make_tool_use_response("search_course_content", {"query": "python"})
        final_response = make_text_response("I was unable to find information about that topic.")
        mock_client.messages.create.side_effect = [tool_response, final_response]

        answer, sources = system.query("What is Python?")
        assert isinstance(answer, str)
        assert len(answer) > 0
        assert sources == []

    def test_query_anthropic_api_exception_propagates_to_caller(self, rag_system_with_mocks):
        """
        WHAT: If the Anthropic API call raises, the exception propagates out of query()
              so FastAPI catches it as a 500.
        ASSERT: query() raises an exception (any type).
        FAILURE MEANS: Exception silently swallowed → query returns wrong value, no 500 sent.
        """
        system, _, mock_client = rag_system_with_mocks
        mock_client.messages.create.side_effect = ConnectionError("API unreachable")
        with pytest.raises(Exception):
            system.query("What is Python?")

    def test_query_with_empty_database_returns_answer_string(self, rag_system_with_mocks):
        """
        WHAT: If the vector DB is empty, search returns is_empty()=True.
              The tool returns 'No relevant content found.' Claude answers accordingly.
        ASSERT: answer is a non-empty string; no exception raised.
        FAILURE MEANS: Empty database crashes the system → HTTP 500 instead of a graceful reply.
        """
        system, mock_vs, mock_client = rag_system_with_mocks
        mock_vs.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool_response = make_tool_use_response("search_course_content", {"query": "python"})
        final_response = make_text_response("There is no course content about that topic.")
        mock_client.messages.create.side_effect = [tool_response, final_response]

        answer, _ = system.query("What is Python?")
        assert isinstance(answer, str)
        assert len(answer) > 0
