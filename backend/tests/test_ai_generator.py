from unittest.mock import MagicMock, patch
import pytest

from ai_generator import AIGenerator


def _tool_use_response(tool_id="t1", tool_name="search_course_content", tool_input=None):
    if tool_input is None:
        tool_input = {"query": "test"}
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = tool_name
    block.input = tool_input
    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = [block]
    return resp


def _text_response(text="Answer."):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [block]
    return resp


def _make_generator():
    with patch("ai_generator.AnthropicVertex"):
        return AIGenerator("proj", "us-east1", "model")


@patch("ai_generator.AnthropicVertex")
class TestGenerateResponse:

    def test_no_tool_use_returns_direct_text(self, mock_vertex_class):
        mock_client = MagicMock()
        mock_vertex_class.return_value = mock_client
        mock_client.messages.create.return_value = _text_response("Direct answer.")

        gen = AIGenerator("proj", "region", "model")
        result = gen.generate_response("What is Python?")

        assert result == "Direct answer."
        assert mock_client.messages.create.call_count == 1

    def test_no_tools_provided_skips_loop(self, mock_vertex_class):
        mock_client = MagicMock()
        mock_vertex_class.return_value = mock_client
        mock_client.messages.create.return_value = _text_response("No tools needed.")

        gen = AIGenerator("proj", "region", "model")
        result = gen.generate_response("General question")

        assert result == "No tools needed."
        assert mock_client.messages.create.call_count == 1
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "tools" not in call_kwargs

    def test_one_tool_call_then_natural_stop(self, mock_vertex_class):
        mock_client = MagicMock()
        mock_vertex_class.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _tool_use_response(tool_id="t1", tool_input={"query": "python basics"}),
            _text_response("Answer after one search."),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Search results here"

        gen = AIGenerator("proj", "region", "model")
        result = gen.generate_response(
            "Explain Python", tools=[{"name": "search_course_content"}], tool_manager=tool_manager
        )

        assert result == "Answer after one search."
        assert mock_client.messages.create.call_count == 2
        tool_manager.execute_tool.assert_called_once_with("search_course_content", query="python basics")

    def test_two_tool_calls_uses_closing_call(self, mock_vertex_class):
        mock_client = MagicMock()
        mock_vertex_class.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _tool_use_response(tool_id="t1", tool_input={"query": "lesson 4 title"}),
            _tool_use_response(tool_id="t2", tool_input={"query": "topic X"}),
            _text_response("Complete answer."),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["Lesson 4: Topic X", "Course Y covers Topic X"]

        gen = AIGenerator("proj", "region", "model")
        result = gen.generate_response(
            "Find a course on the same topic as lesson 4",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert result == "Complete answer."
        assert mock_client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2

        # Both tool results must be in the messages sent to the closing call
        closing_messages = mock_client.messages.create.call_args_list[2].kwargs["messages"]
        tool_result_messages = [
            m for m in closing_messages
            if isinstance(m["content"], list)
            and any(
                isinstance(r, dict) and r.get("type") == "tool_result"
                for r in m["content"]
            )
        ]
        assert len(tool_result_messages) == 2

    def test_round_limit_closing_call_has_no_tools(self, mock_vertex_class):
        mock_client = MagicMock()
        mock_vertex_class.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _tool_use_response(tool_id="t1"),
            _tool_use_response(tool_id="t2"),
            _text_response("Forced final."),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        gen = AIGenerator("proj", "region", "model")
        gen.generate_response(
            "query", tools=[{"name": "search_course_content"}], tool_manager=tool_manager
        )

        assert mock_client.messages.create.call_count == 3
        closing_kwargs = mock_client.messages.create.call_args_list[2].kwargs
        assert "tools" not in closing_kwargs

    def test_tool_failure_triggers_graceful_closing_call(self, mock_vertex_class):
        mock_client = MagicMock()
        mock_vertex_class.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _tool_use_response(tool_id="t1"),
            _text_response("I could not retrieve that information."),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = RuntimeError("Connection failed")

        gen = AIGenerator("proj", "region", "model")
        result = gen.generate_response(
            "query", tools=[{"name": "search_course_content"}], tool_manager=tool_manager
        )

        assert result == "I could not retrieve that information."
        assert mock_client.messages.create.call_count == 2

        # The error string must be present in the closing call's messages
        closing_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
        closing_messages_str = str(closing_messages)
        assert "Connection failed" in closing_messages_str

    def test_conversation_history_included_in_system_prompt(self, mock_vertex_class):
        mock_client = MagicMock()
        mock_vertex_class.return_value = mock_client
        mock_client.messages.create.return_value = _text_response("Response.")

        gen = AIGenerator("proj", "region", "model")
        gen.generate_response(
            "Follow-up question",
            conversation_history="User: Hi\nAssistant: Hello",
        )

        system_arg = mock_client.messages.create.call_args.kwargs["system"]
        assert "User: Hi" in system_arg
        assert "Assistant: Hello" in system_arg
