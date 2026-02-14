"""Tests for AIGenerator in ai_generator.py.

These tests verify that the AI generator:
- Correctly formats messages with search context for the LLM
- Includes the system prompt in every call
- Handles conversation history
- Propagates connection/HTTP errors (which cause 'query failed' in the frontend)
- Handles unexpected response shapes gracefully
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import httpx

from ai_generator import AIGenerator


@pytest.fixture
def generator():
    """AIGenerator pointed at a fake Ollama URL."""
    return AIGenerator(base_url="http://localhost:11434", model="test-model")


@pytest.fixture
def mock_ollama_success(monkeypatch):
    """Patch httpx.Client.post to return a successful Ollama response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "RAG combines retrieval with generation."}
    }
    mock_response.raise_for_status = MagicMock()

    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr(httpx.Client, "post", mock_post)
    return mock_post


# ---------------------------------------------------------------------------
# Message formatting tests
# ---------------------------------------------------------------------------

class TestGenerateResponseFormatting:
    """Verify the messages sent to Ollama are correctly structured."""

    def test_context_is_included_in_user_message(self, generator, mock_ollama_success):
        """When context is provided, it should appear in the user message."""
        generator.generate_response(
            query="What is RAG?",
            context="[Building RAG Chatbots - Lesson 1]\nRAG stands for Retrieval-Augmented Generation.",
        )

        # Inspect the payload sent to Ollama
        call_args = mock_ollama_success.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        messages = payload["messages"]

        user_msg = next(m for m in messages if m["role"] == "user")
        assert "Course context:" in user_msg["content"]
        assert "RAG stands for Retrieval-Augmented Generation" in user_msg["content"]
        assert "What is RAG?" in user_msg["content"]

    def test_no_context_sends_query_only(self, generator, mock_ollama_success):
        """Without context, the user message should be just the query."""
        generator.generate_response(query="Hello")

        call_args = mock_ollama_success.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        messages = payload["messages"]

        user_msg = next(m for m in messages if m["role"] == "user")
        assert user_msg["content"] == "Hello"
        assert "Course context:" not in user_msg["content"]

    def test_system_prompt_always_present(self, generator, mock_ollama_success):
        """The system prompt should always be the first message."""
        generator.generate_response(query="test")

        call_args = mock_ollama_success.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        messages = payload["messages"]

        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert "AI assistant" in system_msg["content"]

    def test_conversation_history_appended_to_system(self, generator, mock_ollama_success):
        """Conversation history should be appended to the system prompt."""
        history = "User: What is RAG?\nAssistant: RAG is retrieval-augmented generation."

        generator.generate_response(query="Tell me more", conversation_history=history)

        call_args = mock_ollama_success.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        messages = payload["messages"]

        system_msg = messages[0]
        assert "Previous conversation:" in system_msg["content"]
        assert "What is RAG?" in system_msg["content"]

    def test_empty_context_treated_as_no_context(self, generator, mock_ollama_success):
        """An empty string context should NOT add 'Course context:' prefix."""
        generator.generate_response(query="Hello", context="")

        call_args = mock_ollama_success.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        messages = payload["messages"]

        user_msg = next(m for m in messages if m["role"] == "user")
        assert user_msg["content"] == "Hello"


# ---------------------------------------------------------------------------
# Response extraction tests
# ---------------------------------------------------------------------------

class TestGenerateResponseOutput:
    """Verify the response is correctly extracted from the Ollama reply."""

    def test_returns_content_string(self, generator, mock_ollama_success):
        """generate_response should return the content string from Ollama."""
        result = generator.generate_response(query="What is RAG?", context="some context")

        assert result == "RAG combines retrieval with generation."

    def test_handles_missing_message_key(self, generator, monkeypatch):
        """If Ollama returns unexpected JSON, should return empty string (not crash)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"unexpected": "format"}
        mock_response.raise_for_status = MagicMock()
        monkeypatch.setattr(httpx.Client, "post", MagicMock(return_value=mock_response))

        result = generator.generate_response(query="test")

        assert result == ""

    def test_handles_missing_content_key(self, generator, monkeypatch):
        """If 'message' exists but has no 'content', should return empty string."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"role": "assistant"}}
        mock_response.raise_for_status = MagicMock()
        monkeypatch.setattr(httpx.Client, "post", MagicMock(return_value=mock_response))

        result = generator.generate_response(query="test")

        assert result == ""


# ---------------------------------------------------------------------------
# Error handling tests — these expose the root cause of "query failed"
# ---------------------------------------------------------------------------

class TestGenerateResponseErrors:
    """Test error scenarios that cause the 'query failed' frontend error."""

    def test_connection_error_propagates(self, generator, monkeypatch):
        """If Ollama is not running, a ConnectError should propagate.

        This is the most likely cause of 'query failed' — the ai_generator
        does NOT catch connection errors, so they bubble up through
        rag_system.query() → app.py → HTTP 500 → frontend 'Query failed'.
        """
        def raise_connect_error(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.Client, "post", raise_connect_error)

        with pytest.raises(httpx.ConnectError):
            generator.generate_response(query="What is RAG?", context="some context")

    def test_http_error_propagates(self, generator, monkeypatch):
        """If Ollama returns a 4xx/5xx, the error should propagate.

        For example, if the model name is wrong, Ollama returns 404.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        monkeypatch.setattr(httpx.Client, "post", MagicMock(return_value=mock_response))

        with pytest.raises(httpx.HTTPStatusError):
            generator.generate_response(query="test", context="ctx")

    def test_timeout_error_propagates(self, generator, monkeypatch):
        """If Ollama takes too long, a timeout error should propagate."""
        def raise_timeout(*args, **kwargs):
            raise httpx.ReadTimeout("Read timed out")

        monkeypatch.setattr(httpx.Client, "post", raise_timeout)

        with pytest.raises(httpx.ReadTimeout):
            generator.generate_response(query="test", context="ctx")

    def test_generator_does_not_filter_context(self, generator, mock_ollama_success):
        """AIGenerator passes context as-is — filtering is rag_system's job.

        The generator is a thin wrapper around Ollama. If it receives an error
        string as context, it will include it. The fix for this lives in
        rag_system.query(), which now filters error strings before they
        reach the generator.
        """
        error_as_context = "Search error: collection is empty"

        generator.generate_response(query="What is RAG?", context=error_as_context)

        call_args = mock_ollama_success.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        user_msg = next(m for m in payload["messages"] if m["role"] == "user")

        # Generator doesn't filter — it passes whatever it receives
        assert "Search error:" in user_msg["content"]


# ---------------------------------------------------------------------------
# Request structure tests
# ---------------------------------------------------------------------------

class TestOllamaRequestFormat:
    """Verify the HTTP request to Ollama is well-formed."""

    def test_request_uses_correct_endpoint(self, generator, mock_ollama_success):
        """Should POST to /api/chat."""
        generator.generate_response(query="test")

        call_args = mock_ollama_success.call_args
        url = call_args.args[0] if call_args.args else call_args[0][0]
        assert url == "http://localhost:11434/api/chat"

    def test_request_includes_model(self, generator, mock_ollama_success):
        """Payload should include the configured model name."""
        generator.generate_response(query="test")

        call_args = mock_ollama_success.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["model"] == "test-model"

    def test_request_disables_streaming(self, generator, mock_ollama_success):
        """stream should be False (we expect a single JSON response)."""
        generator.generate_response(query="test")

        call_args = mock_ollama_success.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["stream"] is False


# ---------------------------------------------------------------------------
# Helper factories for tool-calling tests
# ---------------------------------------------------------------------------

def _make_response(message_body: dict):
    """Create a mock httpx response returning the given message dict."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"message": message_body}
    resp.raise_for_status = MagicMock()
    return resp


def make_tool_call_response(tool_name: str, arguments: dict):
    """Mock Ollama response that requests a tool call."""
    return _make_response({
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": tool_name, "arguments": arguments}}
        ],
    })


def make_text_response(content: str):
    """Mock Ollama response that returns plain text (no tool calls)."""
    return _make_response({
        "role": "assistant",
        "content": content,
    })


SAMPLE_TOOLS = [{"type": "function", "function": {"name": "search", "parameters": {}}}]


# ---------------------------------------------------------------------------
# Sequential tool-calling tests
# ---------------------------------------------------------------------------

class TestSequentialToolCalling:
    """Verify the recursive tool-calling loop in generate_response."""

    def test_single_tool_call_then_text(self, generator, monkeypatch):
        """One tool call followed by a text response → 2 API calls, 1 execution."""
        mock_post = MagicMock(side_effect=[
            make_tool_call_response("search", {"query": "RAG"}),
            make_text_response("Here is the answer."),
        ])
        monkeypatch.setattr(httpx.Client, "post", mock_post)
        executor = MagicMock(return_value="search results")

        result = generator.generate_response(
            query="What is RAG?", tools=SAMPLE_TOOLS, tool_executor=executor,
        )

        assert result == "Here is the answer."
        assert mock_post.call_count == 2
        executor.assert_called_once_with("search", query="RAG")

    def test_two_sequential_tool_calls(self, generator, monkeypatch):
        """Two sequential tool calls then text → 3 API calls, 2 executions."""
        mock_post = MagicMock(side_effect=[
            make_tool_call_response("search", {"query": "course X"}),
            make_tool_call_response("search", {"query": "lesson 4"}),
            make_text_response("Final answer."),
        ])
        monkeypatch.setattr(httpx.Client, "post", mock_post)
        executor = MagicMock(return_value="result")

        result = generator.generate_response(
            query="complex query", tools=SAMPLE_TOOLS, tool_executor=executor,
        )

        assert result == "Final answer."
        assert mock_post.call_count == 3
        assert executor.call_count == 2

    def test_no_tool_calls_returns_immediately(self, generator, monkeypatch):
        """If the LLM returns text right away, no tool execution happens."""
        mock_post = MagicMock(side_effect=[
            make_text_response("Immediate answer."),
        ])
        monkeypatch.setattr(httpx.Client, "post", mock_post)
        executor = MagicMock()

        result = generator.generate_response(
            query="hi", tools=SAMPLE_TOOLS, tool_executor=executor,
        )

        assert result == "Immediate answer."
        assert mock_post.call_count == 1
        executor.assert_not_called()

    def test_max_rounds_forces_final_call_without_tools(self, generator, monkeypatch):
        """After MAX_TOOL_ROUNDS tool calls, the next call omits tools to force text."""
        # MAX_TOOL_ROUNDS is 3, so we need 3 tool-call rounds + 1 forced text
        mock_post = MagicMock(side_effect=[
            make_tool_call_response("search", {"query": "a"}),
            make_tool_call_response("search", {"query": "b"}),
            make_tool_call_response("search", {"query": "c"}),
            make_text_response("Forced text."),
        ])
        monkeypatch.setattr(httpx.Client, "post", mock_post)
        executor = MagicMock(return_value="r")

        result = generator.generate_response(
            query="q", tools=SAMPLE_TOOLS, tool_executor=executor,
        )

        assert result == "Forced text."
        # Fourth call should NOT have tools in its payload
        fourth_call_payload = mock_post.call_args_list[3].kwargs.get("json") or mock_post.call_args_list[3][1].get("json")
        assert "tools" not in fourth_call_payload

    def test_tool_error_passed_as_result(self, generator, monkeypatch):
        """If tool_executor raises, the error string is sent as the tool result."""
        mock_post = MagicMock(side_effect=[
            make_tool_call_response("bad_tool", {}),
            make_text_response("Recovered."),
        ])
        monkeypatch.setattr(httpx.Client, "post", mock_post)
        executor = MagicMock(side_effect=ValueError("something broke"))

        result = generator.generate_response(
            query="q", tools=SAMPLE_TOOLS, tool_executor=executor,
        )

        assert result == "Recovered."
        # Verify the error was passed as a tool message
        second_call_payload = mock_post.call_args_list[1].kwargs.get("json") or mock_post.call_args_list[1][1].get("json")
        tool_msgs = [m for m in second_call_payload["messages"] if m["role"] == "tool"]
        assert len(tool_msgs) == 1
        assert "Tool error:" in tool_msgs[0]["content"]
        assert "something broke" in tool_msgs[0]["content"]

    def test_messages_accumulate_across_rounds(self, generator, monkeypatch):
        """After 2 rounds, the final API call should contain the full conversation."""
        mock_post = MagicMock(side_effect=[
            make_tool_call_response("search", {"query": "first"}),
            make_tool_call_response("search", {"query": "second"}),
            make_text_response("Done."),
        ])
        monkeypatch.setattr(httpx.Client, "post", mock_post)
        executor = MagicMock(return_value="data")

        generator.generate_response(
            query="q", tools=SAMPLE_TOOLS, tool_executor=executor,
        )

        final_payload = mock_post.call_args_list[2].kwargs.get("json") or mock_post.call_args_list[2][1].get("json")
        msgs = final_payload["messages"]
        roles = [m["role"] for m in msgs]
        # system, user, assistant(tool_call), tool, assistant(tool_call), tool
        assert roles == ["system", "user", "assistant", "tool", "assistant", "tool"]

    def test_tools_in_payload_when_provided(self, generator, monkeypatch):
        """When tools are provided, the first API call payload should include them."""
        mock_post = MagicMock(side_effect=[
            make_text_response("answer"),
        ])
        monkeypatch.setattr(httpx.Client, "post", mock_post)

        generator.generate_response(
            query="q", tools=SAMPLE_TOOLS, tool_executor=MagicMock(),
        )

        first_payload = mock_post.call_args_list[0].kwargs.get("json") or mock_post.call_args_list[0][1].get("json")
        assert "tools" in first_payload
        assert first_payload["tools"] == SAMPLE_TOOLS

    def test_no_tools_backward_compatible(self, generator, mock_ollama_success):
        """Without tools/tool_executor, behavior is unchanged — no tools in payload."""
        generator.generate_response(query="test")

        payload = mock_ollama_success.call_args.kwargs.get("json") or mock_ollama_success.call_args[1].get("json")
        assert "tools" not in payload
        assert mock_ollama_success.call_count == 1
