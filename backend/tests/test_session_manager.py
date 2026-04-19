"""
Tests for SessionManager.

No external dependencies — SessionManager is pure in-memory state.
"""
import pytest
from session_manager import SessionManager


class TestCreateSession:
    def test_returns_a_string_id(self):
        sm = SessionManager()
        session_id = sm.create_session()
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_each_call_returns_unique_id(self):
        sm = SessionManager()
        ids = {sm.create_session() for _ in range(5)}
        assert len(ids) == 5

    def test_new_session_has_empty_history(self):
        sm = SessionManager()
        session_id = sm.create_session()
        assert sm.get_conversation_history(session_id) is None


class TestAddMessage:
    def test_message_appears_in_history(self):
        sm = SessionManager()
        session_id = sm.create_session()
        sm.add_message(session_id, "user", "hello")
        history = sm.get_conversation_history(session_id)
        assert "hello" in history

    def test_auto_creates_session_for_unknown_id(self):
        sm = SessionManager()
        sm.add_message("ghost-session", "user", "hi")
        history = sm.get_conversation_history("ghost-session")
        assert "hi" in history

    def test_history_trimmed_to_max_history_times_two(self):
        sm = SessionManager(max_history=2)  # keeps last 4 messages
        session_id = sm.create_session()
        for i in range(6):
            sm.add_message(session_id, "user", f"message {i}")
        messages = sm.sessions[session_id]
        assert len(messages) <= 4

    def test_trim_keeps_most_recent_messages(self):
        sm = SessionManager(max_history=2)
        session_id = sm.create_session()
        for i in range(6):
            sm.add_message(session_id, "user", f"msg {i}")
        history = sm.get_conversation_history(session_id)
        # Oldest messages should be gone
        assert "msg 0" not in history
        assert "msg 1" not in history
        # Most recent should remain
        assert "msg 5" in history


class TestAddExchange:
    def test_adds_both_user_and_assistant_messages(self):
        sm = SessionManager()
        session_id = sm.create_session()
        sm.add_exchange(session_id, "What is Python?", "A programming language.")
        messages = sm.sessions[session_id]
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_content_stored_correctly(self):
        sm = SessionManager()
        session_id = sm.create_session()
        sm.add_exchange(session_id, "user question", "assistant answer")
        messages = sm.sessions[session_id]
        assert messages[0].content == "user question"
        assert messages[1].content == "assistant answer"


class TestGetConversationHistory:
    def test_returns_none_for_unknown_session(self):
        sm = SessionManager()
        assert sm.get_conversation_history("does-not-exist") is None

    def test_returns_none_for_none_session_id(self):
        sm = SessionManager()
        assert sm.get_conversation_history(None) is None

    def test_returns_none_for_empty_session(self):
        sm = SessionManager()
        session_id = sm.create_session()
        assert sm.get_conversation_history(session_id) is None

    def test_formats_role_as_title_case(self):
        sm = SessionManager()
        session_id = sm.create_session()
        sm.add_message(session_id, "user", "hi")
        sm.add_message(session_id, "assistant", "hello")
        history = sm.get_conversation_history(session_id)
        assert "User:" in history
        assert "Assistant:" in history

    def test_multiple_exchanges_all_appear(self):
        sm = SessionManager()
        session_id = sm.create_session()
        sm.add_exchange(session_id, "Q1", "A1")
        sm.add_exchange(session_id, "Q2", "A2")
        history = sm.get_conversation_history(session_id)
        assert "Q1" in history
        assert "A1" in history
        assert "Q2" in history
        assert "A2" in history


class TestClearSession:
    def test_clears_all_messages(self):
        sm = SessionManager()
        session_id = sm.create_session()
        sm.add_exchange(session_id, "question", "answer")
        sm.clear_session(session_id)
        assert sm.get_conversation_history(session_id) is None

    def test_clear_nonexistent_session_does_not_raise(self):
        sm = SessionManager()
        sm.clear_session("nonexistent")  # should not raise
