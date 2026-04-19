"""
Tests for AIGenerator.

anthropic.Anthropic is mocked at import time — no real API calls made.
All tests verify external behavior: API call count, arguments passed, text returned.
"""
import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_use_block(name, tool_id, input_dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.id = tool_id
    block.input = input_dict
    return block


def _response(stop_reason, content):
    r = MagicMock()
    r.stop_reason = stop_reason
    r.content = content
    return r


def _tool_use_response(name="search_course_content", tool_id="tu_001", query="test query"):
    block = _tool_use_block(name, tool_id, {"query": query})
    return _response(stop_reason="tool_use", content=[block])


def _end_turn_response(text="final answer"):
    return _response(stop_reason="end_turn", content=[_text_block(text)])


@pytest.fixture
def generator():
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        gen = AIGenerator(api_key="test-key", model="claude-test-model")
        gen._mock_client = mock_client  # expose for assertions
        yield gen


@pytest.fixture
def tool_manager():
    tm = MagicMock()
    tm.execute_tool.return_value = "search results text"
    return tm


# ---------------------------------------------------------------------------
# 0 tool rounds — direct response
# ---------------------------------------------------------------------------

class TestDirectResponse:
    def test_returns_text_on_end_turn(self, generator):
        generator._mock_client.messages.create.return_value = _end_turn_response("Hello!")
        assert generator.generate_response(query="Say hi") == "Hello!"

    def test_makes_exactly_one_api_call(self, generator):
        generator._mock_client.messages.create.return_value = _end_turn_response()
        generator.generate_response(query="test")
        assert generator._mock_client.messages.create.call_count == 1

    def test_passes_tools_and_tool_choice_to_api(self, generator):
        generator._mock_client.messages.create.return_value = _end_turn_response()
        tools = [{"name": "search", "description": "..."}]
        generator.generate_response(query="test", tools=tools)
        kwargs = generator._mock_client.messages.create.call_args.kwargs
        assert kwargs["tools"] == tools
        assert kwargs["tool_choice"] == {"type": "auto"}

    def test_does_not_pass_tools_when_none_provided(self, generator):
        generator._mock_client.messages.create.return_value = _end_turn_response()
        generator.generate_response(query="test")
        kwargs = generator._mock_client.messages.create.call_args.kwargs
        assert "tools" not in kwargs
        assert "tool_choice" not in kwargs

    def test_conversation_history_appears_in_system_prompt(self, generator):
        generator._mock_client.messages.create.return_value = _end_turn_response()
        generator.generate_response(query="test", conversation_history="User: hi\nAssistant: hello")
        kwargs = generator._mock_client.messages.create.call_args.kwargs
        assert "User: hi" in kwargs["system"]
        assert "Assistant: hello" in kwargs["system"]

    def test_tool_manager_not_called_on_end_turn(self, generator, tool_manager):
        generator._mock_client.messages.create.return_value = _end_turn_response()
        generator.generate_response(query="test", tool_manager=tool_manager)
        tool_manager.execute_tool.assert_not_called()


# ---------------------------------------------------------------------------
# 1 tool round — Claude calls a tool then answers
# ---------------------------------------------------------------------------

class TestOneToolRound:
    def _setup(self, generator, tool_manager, final_text="final answer"):
        generator._mock_client.messages.create.side_effect = [
            _tool_use_response(query="functions"),
            _end_turn_response(final_text),
        ]
        return [{"name": "search_course_content"}]

    def test_makes_two_api_calls(self, generator, tool_manager):
        tools = self._setup(generator, tool_manager)
        generator.generate_response(query="what are functions", tools=tools, tool_manager=tool_manager)
        assert generator._mock_client.messages.create.call_count == 2

    def test_tool_manager_called_once_with_correct_args(self, generator, tool_manager):
        tools = self._setup(generator, tool_manager)
        generator.generate_response(query="what are functions", tools=tools, tool_manager=tool_manager)
        tool_manager.execute_tool.assert_called_once_with("search_course_content", query="functions")

    def test_second_call_includes_tool_result_as_user_message(self, generator, tool_manager):
        """The second API call must carry the tool result in a user message."""
        tools = self._setup(generator, tool_manager)
        generator.generate_response(query="what are functions", tools=tools, tool_manager=tool_manager)
        second_kwargs = generator._mock_client.messages.create.call_args_list[1].kwargs
        user_msgs = [m for m in second_kwargs["messages"] if m["role"] == "user"]
        last_user = user_msgs[-1]
        assert isinstance(last_user["content"], list)
        assert last_user["content"][0]["type"] == "tool_result"

    def test_second_call_keeps_tools_available(self, generator, tool_manager):
        """Tools remain in the second call so Claude could make a second tool call."""
        tools = self._setup(generator, tool_manager)
        generator.generate_response(query="what are functions", tools=tools, tool_manager=tool_manager)
        second_kwargs = generator._mock_client.messages.create.call_args_list[1].kwargs
        assert "tools" in second_kwargs

    def test_returns_text_from_final_response(self, generator, tool_manager):
        tools = self._setup(generator, tool_manager, final_text="The answer is 42")
        result = generator.generate_response(query="what's the answer", tools=tools, tool_manager=tool_manager)
        assert result == "The answer is 42"


# ---------------------------------------------------------------------------
# 2 tool rounds — cap reached, forced final call without tools
# ---------------------------------------------------------------------------

class TestTwoToolRounds:
    def _setup(self, generator, tool_manager, final_text="synthesized answer"):
        generator._mock_client.messages.create.side_effect = [
            _tool_use_response(tool_id="tu_001", query="outline query"),
            _tool_use_response(tool_id="tu_002", query="content query"),
            _end_turn_response(final_text),
        ]
        return [{"name": "search_course_content"}]

    def test_makes_three_api_calls(self, generator, tool_manager):
        tools = self._setup(generator, tool_manager)
        generator.generate_response(query="complex query", tools=tools, tool_manager=tool_manager)
        assert generator._mock_client.messages.create.call_count == 3

    def test_tool_manager_called_twice(self, generator, tool_manager):
        tools = self._setup(generator, tool_manager)
        generator.generate_response(query="complex query", tools=tools, tool_manager=tool_manager)
        assert tool_manager.execute_tool.call_count == 2

    def test_third_call_has_no_tools(self, generator, tool_manager):
        """After the cap, the forced final call must NOT include tools."""
        tools = self._setup(generator, tool_manager)
        generator.generate_response(query="complex query", tools=tools, tool_manager=tool_manager)
        third_kwargs = generator._mock_client.messages.create.call_args_list[2].kwargs
        assert "tools" not in third_kwargs
        assert "tool_choice" not in third_kwargs

    def test_messages_accumulate_across_rounds(self, generator, tool_manager):
        """The third call must carry the full conversation: user + 2×(assistant+tool_result)."""
        tools = self._setup(generator, tool_manager)
        generator.generate_response(query="complex query", tools=tools, tool_manager=tool_manager)
        third_kwargs = generator._mock_client.messages.create.call_args_list[2].kwargs
        msgs = third_kwargs["messages"]
        roles = [m["role"] for m in msgs]
        # Expected: user, assistant, user(tool_result), assistant, user(tool_result) = 5 messages
        assert roles == ["user", "assistant", "user", "assistant", "user"]

    def test_returns_text_from_third_response(self, generator, tool_manager):
        tools = self._setup(generator, tool_manager, final_text="complete answer")
        result = generator.generate_response(query="complex query", tools=tools, tool_manager=tool_manager)
        assert result == "complete answer"


# ---------------------------------------------------------------------------
# Tool execution errors
# ---------------------------------------------------------------------------

class TestToolExecutionError:
    def _setup_with_error(self, generator, tool_manager, final_text="sorry, error"):
        tool_manager.execute_tool.side_effect = RuntimeError("DB exploded")
        generator._mock_client.messages.create.side_effect = [
            _tool_use_response(query="failing query"),
            _end_turn_response(final_text),
        ]
        return [{"name": "search_course_content"}]

    def test_error_does_not_propagate(self, generator, tool_manager):
        tools = self._setup_with_error(generator, tool_manager)
        # Should not raise
        result = generator.generate_response(query="test", tools=tools, tool_manager=tool_manager)
        assert isinstance(result, str)

    def test_error_triggers_final_api_call(self, generator, tool_manager):
        """Even on tool error a final API call is made so Claude can respond."""
        tools = self._setup_with_error(generator, tool_manager)
        generator.generate_response(query="test", tools=tools, tool_manager=tool_manager)
        assert generator._mock_client.messages.create.call_count == 2

    def test_error_final_call_has_no_tools(self, generator, tool_manager):
        tools = self._setup_with_error(generator, tool_manager)
        generator.generate_response(query="test", tools=tools, tool_manager=tool_manager)
        second_kwargs = generator._mock_client.messages.create.call_args_list[1].kwargs
        assert "tools" not in second_kwargs

    def test_error_string_appears_as_tool_result(self, generator, tool_manager):
        """Claude must receive the error as a tool_result so it can acknowledge it."""
        tools = self._setup_with_error(generator, tool_manager)
        generator.generate_response(query="test", tools=tools, tool_manager=tool_manager)
        second_kwargs = generator._mock_client.messages.create.call_args_list[1].kwargs
        user_msgs = [m for m in second_kwargs["messages"] if m["role"] == "user"]
        last_user = user_msgs[-1]
        tool_result_content = last_user["content"][0]["content"]
        assert "Error" in tool_result_content

    def test_error_returns_text_from_final_response(self, generator, tool_manager):
        tools = self._setup_with_error(generator, tool_manager, final_text="could not retrieve")
        result = generator.generate_response(query="test", tools=tools, tool_manager=tool_manager)
        assert result == "could not retrieve"


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

class TestSystemPrompt:
    def test_prompt_mentions_two_sequential_tool_calls(self):
        assert "2" in AIGenerator.SYSTEM_PROMPT
        assert "sequential" in AIGenerator.SYSTEM_PROMPT.lower()

    def test_max_tool_rounds_constant_is_two(self):
        assert AIGenerator.MAX_TOOL_ROUNDS == 2
