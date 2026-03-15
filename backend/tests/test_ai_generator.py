"""
Tests for ai_generator.py: AIGenerator.generate_response() and _handle_tool_execution().

Covers:
- Direct response (no tool use)
- Tool calling: two-pass API flow
- Exception propagation from tool execution (the critical bug test)
- System prompt and conversation history composition
- API parameter correctness
"""
import pytest
from unittest.mock import MagicMock, patch, call

from helpers import make_text_response, make_tool_use_response, make_mixed_response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def generator(mock_client):
    """AIGenerator with Anthropic client mocked out (no real API calls)."""
    with patch("ai_generator.anthropic.Anthropic", return_value=mock_client):
        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")
    return gen


@pytest.fixture
def simple_tool_defs():
    return [{"name": "search_course_content", "description": "Search", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}]


@pytest.fixture
def mock_tool_manager():
    tm = MagicMock()
    tm.execute_tool.return_value = "search results text"
    return tm


# ---------------------------------------------------------------------------
# Direct response (stop_reason == "end_turn")
# ---------------------------------------------------------------------------

class TestGenerateResponseDirect:

    def test_end_turn_returns_text(self, generator, mock_client):
        """When Claude returns end_turn, the text content is returned directly."""
        mock_client.messages.create.return_value = make_text_response("Direct answer")
        result = generator.generate_response(query="what is 2+2")
        assert result == "Direct answer"

    def test_api_called_once_for_direct_response(self, generator, mock_client):
        """Only one API call is made when no tool use occurs."""
        mock_client.messages.create.return_value = make_text_response("hello")
        generator.generate_response(query="hi")
        assert mock_client.messages.create.call_count == 1

    def test_correct_model_used(self, generator, mock_client):
        """The model specified at construction time is passed to the API."""
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response(query="test")
        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-test"

    def test_temperature_and_max_tokens(self, generator, mock_client):
        """temperature=0 and max_tokens=800 are always sent."""
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response(query="test")
        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["temperature"] == 0
        assert kwargs["max_tokens"] == 800

    def test_query_in_messages(self, generator, mock_client):
        """The user query appears as the first message."""
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response(query="explain backprop")
        kwargs = mock_client.messages.create.call_args.kwargs
        messages = kwargs["messages"]
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "explain backprop"


# ---------------------------------------------------------------------------
# System prompt and conversation history
# ---------------------------------------------------------------------------

class TestSystemPrompt:

    def test_system_prompt_present(self, generator, mock_client):
        """The SYSTEM_PROMPT is always included in the 'system' parameter."""
        from ai_generator import AIGenerator
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response(query="test")
        kwargs = mock_client.messages.create.call_args.kwargs
        assert AIGenerator.SYSTEM_PROMPT in kwargs["system"]

    def test_conversation_history_appended_to_system(self, generator, mock_client):
        """When conversation_history is provided, it appears after the system prompt."""
        mock_client.messages.create.return_value = make_text_response("ok")
        history = "User: hello\nAssistant: hi"
        generator.generate_response(query="test", conversation_history=history)
        kwargs = mock_client.messages.create.call_args.kwargs
        assert "Previous conversation:" in kwargs["system"]
        assert history in kwargs["system"]

    def test_no_history_marker_when_history_is_none(self, generator, mock_client):
        """Without conversation history, 'Previous conversation:' is absent."""
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response(query="test", conversation_history=None)
        kwargs = mock_client.messages.create.call_args.kwargs
        assert "Previous conversation:" not in kwargs["system"]


# ---------------------------------------------------------------------------
# Tool parameters
# ---------------------------------------------------------------------------

class TestToolParameters:

    def test_tools_present_in_api_params_when_provided(self, generator, mock_client, simple_tool_defs):
        """When tools are passed, 'tools' and 'tool_choice' appear in the API call."""
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response(query="test", tools=simple_tool_defs)
        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["tools"] == simple_tool_defs
        assert kwargs["tool_choice"] == {"type": "auto"}

    def test_no_tools_key_when_tools_is_none(self, generator, mock_client):
        """When tools=None, neither 'tools' nor 'tool_choice' are added to the API call."""
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response(query="test", tools=None)
        kwargs = mock_client.messages.create.call_args.kwargs
        assert "tools" not in kwargs
        assert "tool_choice" not in kwargs


# ---------------------------------------------------------------------------
# Two-pass tool execution flow
# ---------------------------------------------------------------------------

class TestToolExecutionFlow:

    def test_tool_use_triggers_two_api_calls(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """stop_reason='tool_use' results in a second API call."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "neural networks"}),
            make_text_response("Final answer about neural networks"),
        ]
        result = generator.generate_response(
            query="explain neural networks",
            tools=simple_tool_defs,
            tool_manager=mock_tool_manager,
        )
        assert mock_client.messages.create.call_count == 2
        assert result == "Final answer about neural networks"

    def test_tool_manager_called_with_correct_args(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """tool_manager.execute_tool() is called with the tool name and input kwargs."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "backprop", "course_name": "DL101"}),
            make_text_response("answer"),
        ]
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="backprop", course_name="DL101"
        )

    def test_tool_result_in_second_call_messages(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """The second API call receives the tool result as a user message with correct structure."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_42", {"query": "backprop"}),
            make_text_response("answer"),
        ]
        mock_tool_manager.execute_tool.return_value = "result text"
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)

        second_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs
        messages = second_call_kwargs["messages"]
        # Last message is the tool result from user
        last_msg = messages[-1]
        assert last_msg["role"] == "user"
        assert isinstance(last_msg["content"], list)
        tool_result = last_msg["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "tu_42"
        assert tool_result["content"] == "result text"

    def test_second_call_has_no_tools_parameter(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """The final synthesis call must NOT include 'tools' to prevent looping."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "test"}),
            make_tool_use_response("search_course_content", "tu_2", {"query": "test2"}),
            make_text_response("done"),
        ]
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        final_call_kwargs = mock_client.messages.create.call_args_list[2].kwargs
        assert "tools" not in final_call_kwargs

    def test_assistant_tool_use_response_appended_to_messages(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """The initial assistant tool_use response is included in the message history for the second call."""
        first_response = make_tool_use_response("search_course_content", "tu_1", {"query": "test"})
        mock_client.messages.create.side_effect = [
            first_response,
            make_text_response("done"),
        ]
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        second_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs
        messages = second_call_kwargs["messages"]
        # Should have: user message, assistant message (tool_use), user message (tool_result)
        assert len(messages) == 3
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == first_response.content

    def test_mixed_content_only_tool_use_blocks_executed(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """Only tool_use blocks are executed; text blocks in the response are ignored."""
        mock_client.messages.create.side_effect = [
            make_mixed_response("search_course_content", "tu_1", {"query": "test"}),
            make_text_response("done"),
        ]
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        # Tool should be called exactly once (for the tool_use block)
        assert mock_tool_manager.execute_tool.call_count == 1

    def test_tool_use_without_tool_manager_falls_through_to_text(self, generator, mock_client, simple_tool_defs):
        """When tool_manager is None, tool_use response falls through to return content[0].text."""
        tool_response = make_tool_use_response("search_course_content", "tu_1", {"query": "test"})
        mock_client.messages.create.return_value = tool_response
        # With no tool_manager, the condition `if response.stop_reason == "tool_use" and tool_manager:`
        # is False, so it returns response.content[0].text (which is a MagicMock for the tool block)
        result = generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=None)
        # Should not raise, and should return the content[0].text attribute
        assert result == tool_response.content[0].text


# ---------------------------------------------------------------------------
# CRITICAL BUG TEST: unhandled exception from tool execution
# ---------------------------------------------------------------------------

class TestToolExecutionExceptionBug:

    def test_exception_from_execute_tool_is_caught_and_returned_as_string(
        self, generator, mock_client, simple_tool_defs, mock_tool_manager
    ):
        """
        FIX VERIFICATION: _handle_tool_execution() now wraps execute_tool() in
        try/except. Exceptions from tools are converted to error strings passed
        back to Claude instead of crashing the entire request.
        """
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "backprop"}),
            make_text_response("I encountered an error searching for that content."),
        ]
        mock_tool_manager.execute_tool.side_effect = ValueError("ChromaDB filter error")

        # After the fix: does NOT raise, returns a response
        result = generator.generate_response(
            query="explain backprop",
            tools=simple_tool_defs,
            tool_manager=mock_tool_manager,
        )
        assert isinstance(result, str)

        # The error message was passed to the second API call as tool_result content
        second_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs
        tool_result_content = second_call_kwargs["messages"][-1]["content"][0]["content"]
        assert "ChromaDB filter error" in tool_result_content


# ---------------------------------------------------------------------------
# Sequential tool calling (up to 2 rounds)
# ---------------------------------------------------------------------------

class TestSequentialToolCalling:

    def test_two_sequential_tools_triggers_three_api_calls(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """Two sequential tool uses result in 3 API calls: initial + mid-loop + final synthesis."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "first"}),
            make_tool_use_response("search_course_content", "tu_2", {"query": "second"}),
            make_text_response("text_final"),
        ]
        result = generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        assert mock_client.messages.create.call_count == 3
        assert result == "text_final"

    def test_two_sequential_tools_both_executed(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """Both tools are executed when there are two sequential tool calls."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "first"}),
            make_tool_use_response("search_course_content", "tu_2", {"query": "second"}),
            make_text_response("text_final"),
        ]
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        assert mock_tool_manager.execute_tool.call_count == 2

    def test_final_synthesis_call_has_no_tools_in_two_round_flow(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """The final synthesis call in a two-round flow has no 'tools' key."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "first"}),
            make_tool_use_response("search_course_content", "tu_2", {"query": "second"}),
            make_text_response("text_final"),
        ]
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        assert "tools" not in mock_client.messages.create.call_args_list[2].kwargs

    def test_two_round_message_history_complete(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """Final call messages has 5 entries: user, assistant_1, tool_result_1, assistant_2, tool_result_2."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "first"}),
            make_tool_use_response("search_course_content", "tu_2", {"query": "second"}),
            make_text_response("text_final"),
        ]
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        final_messages = mock_client.messages.create.call_args_list[2].kwargs["messages"]
        assert len(final_messages) == 5

    def test_mid_loop_call_has_tools_available(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """The mid-loop (second) call includes tools so Claude can make a second tool call."""
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "first"}),
            make_text_response("done"),
        ]
        generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        assert "tools" in mock_client.messages.create.call_args_list[1].kwargs

    def test_first_round_error_skips_mid_loop_call(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """A tool error in round 0 skips the mid-loop call and goes straight to final synthesis."""
        mock_tool_manager.execute_tool.side_effect = ValueError("search failed")
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "first"}),
            make_text_response("error answer"),
        ]
        result = generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        assert mock_client.messages.create.call_count == 2
        error_content = mock_client.messages.create.call_args_list[1].kwargs["messages"][-1]["content"][0]["content"]
        assert "search failed" in error_content

    def test_second_round_error_triggers_final_synthesis(self, generator, mock_client, simple_tool_defs, mock_tool_manager):
        """A tool error in round 1 still proceeds to the final synthesis call (3 total calls)."""
        mock_tool_manager.execute_tool.side_effect = [
            "ok result",
            ValueError("second search failed"),
        ]
        mock_client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "tu_1", {"query": "first"}),
            make_tool_use_response("search_course_content", "tu_2", {"query": "second"}),
            make_text_response("final answer"),
        ]
        result = generator.generate_response(query="q", tools=simple_tool_defs, tool_manager=mock_tool_manager)
        assert mock_client.messages.create.call_count == 3
        assert isinstance(result, str)
        final_messages = mock_client.messages.create.call_args_list[2].kwargs["messages"]
        tool_result_contents = [
            item["content"]
            for msg in final_messages
            if isinstance(msg.get("content"), list)
            for item in msg["content"]
            if item.get("type") == "tool_result"
        ]
        assert any("second search failed" in c for c in tool_result_contents)
