import pytest
from unittest.mock import MagicMock, patch
from tests.helpers import make_search_results, make_text_block, make_tool_use_block, make_message


@pytest.fixture
def rag(tmp_path):
    with patch("vector_store.chromadb.PersistentClient") as mock_chroma, \
         patch("vector_store.SentenceTransformer"), \
         patch("ai_generator.anthropic.Anthropic") as mock_anthropic_cls:

        mock_collection = MagicMock()
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_create = mock_client.messages.create

        from config import Config
        cfg = Config(
            ANTHROPIC_API_KEY="test-key",
            ANTHROPIC_MODEL="claude-sonnet-4-6",
            CHROMA_PATH=str(tmp_path / "chroma"),
            EMBEDDING_MODEL="all-MiniLM-L6-v2",
            MAX_RESULTS=5,
            MAX_HISTORY=2,
            CHUNK_SIZE=800,
            CHUNK_OVERLAP=100,
        )

        from rag_system import RAGSystem
        system = RAGSystem(cfg)

        # Swap out vector_store with a clean MagicMock for full test control
        mock_store = MagicMock()
        system.vector_store = mock_store
        for tool in system.tool_manager.tools.values():
            if hasattr(tool, "store"):
                tool.store = mock_store

        yield {"system": system, "mock_create": mock_create, "mock_store": mock_store}


def _text_response(text):
    return make_message([make_text_block(text)], stop_reason="end_turn")


class TestRAGSystemQuery:

    def test_query_without_tool_use_returns_answer_and_empty_sources(self, rag):
        rag["mock_create"].return_value = _text_response("Python is a programming language.")
        response, sources = rag["system"].query("What is Python?", session_id="s1")
        assert response == "Python is a programming language."
        assert sources == []

    def test_query_with_tool_use_returns_answer_and_sources(self, rag):
        tool_input = {"query": "what is RAG"}
        rag["mock_create"].side_effect = [
            make_message(
                [make_tool_use_block("search_course_content", tool_input, "tu_1")],
                stop_reason="tool_use",
            ),
            make_message([make_text_block("RAG combines retrieval with generation.")], stop_reason="end_turn"),
        ]
        rag["mock_store"].search.return_value = make_search_results(
            documents=["RAG content block."],
            metadata=[{"course_title": "AI Course", "lesson_number": 1}],
            distances=[0.1],
        )
        rag["mock_store"].get_lesson_link.return_value = "https://example.com/l1"

        rag["system"].session_manager.sessions["s1"] = []
        response, sources = rag["system"].query("what is RAG", session_id="s1")

        assert response == "RAG combines retrieval with generation."
        assert len(sources) == 1
        assert sources[0]["text"] == "AI Course - Lesson 1"
        assert sources[0]["url"] == "https://example.com/l1"

    def test_query_history_passed_on_second_call(self, rag):
        session_id = "s_history"
        rag["system"].session_manager.sessions[session_id] = []

        rag["mock_create"].return_value = _text_response("First answer.")
        rag["system"].query("First question.", session_id=session_id)

        rag["mock_create"].return_value = _text_response("Second answer.")
        rag["system"].query("Second question.", session_id=session_id)

        second_call_kwargs = rag["mock_create"].call_args.kwargs
        system_param = second_call_kwargs["system"]
        assert "First question." in system_param
        assert "First answer." in system_param

    def test_reset_sources_called_per_query(self, rag):
        rag["mock_create"].return_value = _text_response("Answer.")
        call_count = []
        original = rag["system"].tool_manager.reset_sources

        def spy():
            call_count.append(1)
            original()

        rag["system"].tool_manager.reset_sources = spy

        rag["system"].query("Q1", session_id="s1")
        rag["system"].query("Q2", session_id="s1")
        assert len(call_count) == 2

    def test_query_creates_session_when_none_provided(self, rag):
        """
        EXPECTED FAIL on current code.
        Bug: query() wraps history lookup and history storage in `if session_id:`
        guards. When session_id=None is passed, no session is ever created and
        no history is stored. The session_manager.sessions dict remains empty.
        Fix: call create_session() at the top of query() when session_id is None,
        then remove both `if session_id:` guards (they become redundant).
        """
        rag["mock_create"].return_value = _text_response("Auto-session answer.")
        rag["system"].query("Implicit session query.")
        # At least one session must have been created
        assert len(rag["system"].session_manager.sessions) >= 1  # FAILS on current code
