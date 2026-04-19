"""
Integration tests for RAGSystem.

VectorStore, AIGenerator, DocumentProcessor, and SessionManager are all
patched at the module level — no real I/O happens.
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def rag():
    """
    Return a RAGSystem instance with all external dependencies mocked.
    Patches applied in conftest sys.path setup allow `from rag_system import ...`.
    """
    with patch("rag_system.VectorStore") as MockVectorStore, \
         patch("rag_system.AIGenerator") as MockAIGenerator, \
         patch("rag_system.DocumentProcessor") as MockDocProcessor, \
         patch("rag_system.SessionManager") as MockSessionManager:

        # Build mock instances
        mock_vs = MagicMock()
        mock_ai = MagicMock()
        mock_dp = MagicMock()
        mock_sm = MagicMock()

        MockVectorStore.return_value = mock_vs
        MockAIGenerator.return_value = mock_ai
        MockDocProcessor.return_value = mock_dp
        MockSessionManager.return_value = mock_sm

        # Reasonable defaults
        mock_ai.generate_response.return_value = "Claude says hello"
        mock_sm.get_conversation_history.return_value = "previous: hi"

        # Config stub
        config = MagicMock()
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-test-model"
        config.CHROMA_PATH = "/tmp/chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.MAX_HISTORY = 2

        from rag_system import RAGSystem
        system = RAGSystem(config)

        # Expose mocks for assertions
        system._mock_vs = mock_vs
        system._mock_ai = mock_ai
        system._mock_sm = mock_sm

        yield system


# ---------------------------------------------------------------------------
# query() tests
# ---------------------------------------------------------------------------

class TestRagSystemQuery:
    def test_query_returns_response_and_sources(self, rag):
        """Happy path: returns the AI's text and whatever sources tool_manager has."""
        # Patch tool_manager on the instance
        rag.tool_manager = MagicMock()
        rag.tool_manager.get_tool_definitions.return_value = [{"name": "search"}]
        rag.tool_manager.get_last_sources.return_value = ["Course A - Lesson 1"]
        rag._mock_ai.generate_response.return_value = "Python uses indentation"

        response, sources = rag.query("What is Python indentation?")

        assert response == "Python uses indentation"
        assert sources == ["Course A - Lesson 1"]

    def test_query_passes_tools_to_ai_generator(self, rag):
        """generate_response must be called with tools= and tool_manager=."""
        tool_defs = [{"name": "search_course_content"}]
        rag.tool_manager = MagicMock()
        rag.tool_manager.get_tool_definitions.return_value = tool_defs
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("What is a list?")

        call_kwargs = rag._mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["tools"] == tool_defs
        assert call_kwargs["tool_manager"] is rag.tool_manager

    def test_query_passes_conversation_history_for_known_session(self, rag):
        """When session_id is provided, history is fetched and forwarded."""
        rag.tool_manager = MagicMock()
        rag.tool_manager.get_tool_definitions.return_value = []
        rag.tool_manager.get_last_sources.return_value = []
        rag._mock_sm.get_conversation_history.return_value = "User: hello\nAssistant: hi"

        rag.query("Follow-up question", session_id="sess-001")

        call_kwargs = rag._mock_ai.generate_response.call_args.kwargs
        assert "User: hello" in call_kwargs["conversation_history"]

    def test_query_with_no_session_skips_history(self, rag):
        """Without session_id, conversation_history should be None."""
        rag.tool_manager = MagicMock()
        rag.tool_manager.get_tool_definitions.return_value = []
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("What is a dict?")  # no session_id

        call_kwargs = rag._mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] is None
        rag._mock_sm.get_conversation_history.assert_not_called()

    def test_query_resets_sources_after_retrieval(self, rag):
        """reset_sources() must be called after get_last_sources()."""
        rag.tool_manager = MagicMock()
        rag.tool_manager.get_tool_definitions.return_value = []
        rag.tool_manager.get_last_sources.return_value = ["Source X"]

        rag.query("test query")

        rag.tool_manager.reset_sources.assert_called_once()

    def test_query_updates_session_after_response(self, rag):
        """add_exchange() must be called with session_id, query, and response."""
        rag.tool_manager = MagicMock()
        rag.tool_manager.get_tool_definitions.return_value = []
        rag.tool_manager.get_last_sources.return_value = []
        rag._mock_ai.generate_response.return_value = "answer text"

        rag.query("user question", session_id="sess-xyz")

        rag._mock_sm.add_exchange.assert_called_once_with(
            "sess-xyz", "user question", "answer text"
        )

    def test_query_does_not_update_session_without_session_id(self, rag):
        """Without session_id, add_exchange() should NOT be called."""
        rag.tool_manager = MagicMock()
        rag.tool_manager.get_tool_definitions.return_value = []
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("anonymous question")

        rag._mock_sm.add_exchange.assert_not_called()


# ---------------------------------------------------------------------------
# add_course_folder() tests
# ---------------------------------------------------------------------------

class TestRagSystemAddCourseFolder:
    def test_nonexistent_folder_returns_zero(self, rag):
        """If the folder does not exist, return (0, 0) without touching the store."""
        courses, chunks = rag.add_course_folder("/tmp/does_not_exist_xyzzy")
        assert courses == 0
        assert chunks == 0

    def test_skips_courses_that_already_exist(self, rag, tmp_path):
        """Courses already in the vector store must not be re-added."""
        # Create a dummy .txt file so the folder is non-empty
        course_file = tmp_path / "course.txt"
        course_file.write_text("dummy")

        # DocumentProcessor returns a course whose title is already indexed
        mock_course = MagicMock()
        mock_course.title = "Existing Course"
        rag.document_processor.process_course_document.return_value = (mock_course, [])
        rag._mock_vs.get_existing_course_titles.return_value = ["Existing Course"]

        courses, chunks = rag.add_course_folder(str(tmp_path))

        assert courses == 0
        rag._mock_vs.add_course_metadata.assert_not_called()

    def test_adds_new_course_to_vector_store(self, rag, tmp_path):
        """A course title not yet in the store should be added."""
        course_file = tmp_path / "new_course.txt"
        course_file.write_text("dummy")

        mock_course = MagicMock()
        mock_course.title = "Brand New Course"
        mock_chunks = [MagicMock(), MagicMock()]
        rag.document_processor.process_course_document.return_value = (mock_course, mock_chunks)
        rag._mock_vs.get_existing_course_titles.return_value = []

        courses, chunks = rag.add_course_folder(str(tmp_path))

        assert courses == 1
        assert chunks == 2
        rag._mock_vs.add_course_metadata.assert_called_once_with(mock_course)
        rag._mock_vs.add_course_content.assert_called_once_with(mock_chunks)

    def test_clear_existing_calls_clear_all_data(self, rag, tmp_path):
        """clear_existing=True must call clear_all_data before processing."""
        rag._mock_vs.get_existing_course_titles.return_value = []

        rag.add_course_folder(str(tmp_path), clear_existing=True)

        rag._mock_vs.clear_all_data.assert_called_once()

    def test_clear_existing_false_does_not_clear(self, rag, tmp_path):
        """clear_existing=False (default) must NOT call clear_all_data."""
        rag._mock_vs.get_existing_course_titles.return_value = []

        rag.add_course_folder(str(tmp_path), clear_existing=False)

        rag._mock_vs.clear_all_data.assert_not_called()
