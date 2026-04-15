"""
Tests that AIGenerator correctly invokes tools via the sequential tool-calling loop.

Covers:
- Direct text answers when Claude doesn't call a tool
- Tool manager is called when Claude returns stop_reason="tool_use"
- Correct tool name and inputs are forwarded to the tool manager
- A second API call is made after tool execution, carrying the tool result
- The final forced call does NOT include the tools parameter
- tools + tool_choice are set on the first call when tools are provided
- Edge case: stop_reason="tool_use" but no tool_manager provided
- Sequential tool calling: 2 chained rounds, forced stop, error string, exception handling
"""
import pytest
from unittest.mock import MagicMock, patch, call
from ai_generator import AIGenerator
from tests.conftest import make_text_response, make_tool_use_response


# ---------------------------------------------------------------------------
# Fixture: AIGenerator with a mocked Anthropic client
# ---------------------------------------------------------------------------

@pytest.fixture
def generator_and_client():
    """
    Returns (AIGenerator, mock_client) where mock_client is the mock
    anthropic.Anthropic() instance injected into the generator.
    """
    with patch("ai_generator.anthropic.Anthropic") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        gen = AIGenerator(api_key="test-key", model="claude-test")
    return gen, mock_client


# ---------------------------------------------------------------------------
# Direct (no-tool) responses
# ---------------------------------------------------------------------------

class TestDirectResponse:
    def test_returns_text_when_no_tool_use(self, generator_and_client):
        gen, client = generator_and_client
        client.messages.create.return_value = make_text_response("Paris is the capital of France.")

        result = gen.generate_response(query="What is the capital of France?")

        assert result == "Paris is the capital of France."

    def test_single_api_call_when_no_tool_use(self, generator_and_client):
        gen, client = generator_and_client
        client.messages.create.return_value = make_text_response()

        gen.generate_response(query="Hello")

        assert client.messages.create.call_count == 1

    def test_tools_not_in_api_call_when_none_provided(self, generator_and_client):
        gen, client = generator_and_client
        client.messages.create.return_value = make_text_response()

        gen.generate_response(query="Hello", tools=None)

        api_call_kwargs = client.messages.create.call_args[1]
        assert "tools" not in api_call_kwargs
        assert "tool_choice" not in api_call_kwargs

    def test_conversation_history_added_to_system_prompt(self, generator_and_client):
        gen, client = generator_and_client
        client.messages.create.return_value = make_text_response()

        gen.generate_response(query="Follow-up", conversation_history="User: Hi\nAssistant: Hello")

        system_content = client.messages.create.call_args[1]["system"]
        assert "User: Hi" in system_content
        assert "Assistant: Hello" in system_content


# ---------------------------------------------------------------------------
# Tool use: first call triggers tool, second call produces answer
# ---------------------------------------------------------------------------

class TestToolUseFlow:
    def _setup_two_call_sequence(self, client, tool_input=None):
        """Configure client to return tool_use on first call, text on second."""
        tool_response = make_tool_use_response(
            tool_name="search_course_content",
            tool_id="toolu_123",
            tool_input=tool_input or {"query": "what is RAG?"},
        )
        final_response = make_text_response("RAG combines retrieval with generation.")
        client.messages.create.side_effect = [tool_response, final_response]

    def test_two_api_calls_made_on_tool_use(self, generator_and_client):
        gen, client = generator_and_client
        self._setup_two_call_sequence(client)
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Relevant chunk content."

        gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert client.messages.create.call_count == 2

    def test_tool_manager_called_with_correct_tool_name(self, generator_and_client):
        gen, client = generator_and_client
        self._setup_two_call_sequence(client, tool_input={"query": "what is RAG?"})
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "some content"

        gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="what is RAG?"
        )

    def test_final_response_text_returned(self, generator_and_client):
        gen, client = generator_and_client
        self._setup_two_call_sequence(client)
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Chunk text."

        result = gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert result == "RAG combines retrieval with generation."

    def test_tool_result_injected_into_second_call_messages(self, generator_and_client):
        gen, client = generator_and_client
        self._setup_two_call_sequence(client)
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Retrieved content here."

        gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        second_call_kwargs = client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]
        # Find the tool_result message specifically (role=user, content is a list of tool_result dicts)
        tool_result_message = next(
            m for m in messages
            if isinstance(m.get("content"), list)
            and m["content"]
            and isinstance(m["content"][0], dict)
            and m["content"][0].get("type") == "tool_result"
        )
        assert tool_result_message["role"] == "user"
        result_block = tool_result_message["content"][0]
        assert result_block["type"] == "tool_result"
        assert result_block["content"] == "Retrieved content here."
        assert result_block["tool_use_id"] == "toolu_123"

    def test_second_call_includes_tools_for_possible_chaining(self, generator_and_client):
        """
        With the sequential loop, the second API call is an intermediate call that
        still includes tools — Claude can decide to chain a second tool call or
        answer directly. If Claude answers directly, the loop exits early (no forced
        final call). The forced-final-call-without-tools case is covered by
        TestSequentialToolUse.test_forced_final_call_excludes_tools.
        """
        gen, client = generator_and_client
        self._setup_two_call_sequence(client)
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "content"

        gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        second_call_kwargs = client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs
        assert "tool_choice" in second_call_kwargs


# ---------------------------------------------------------------------------
# First-call API parameter validation
# ---------------------------------------------------------------------------

class TestFirstCallParameters:
    def test_tools_included_in_first_call_when_provided(self, generator_and_client):
        gen, client = generator_and_client
        client.messages.create.return_value = make_text_response()
        tools = [{"name": "search_course_content", "description": "search"}]

        gen.generate_response(query="test", tools=tools)

        first_call_kwargs = client.messages.create.call_args[1]
        assert first_call_kwargs["tools"] == tools

    def test_tool_choice_auto_set_when_tools_provided(self, generator_and_client):
        gen, client = generator_and_client
        client.messages.create.return_value = make_text_response()

        gen.generate_response(query="test", tools=[{"name": "some_tool"}])

        first_call_kwargs = client.messages.create.call_args[1]
        assert first_call_kwargs["tool_choice"] == {"type": "auto"}

    def test_user_query_in_messages(self, generator_and_client):
        gen, client = generator_and_client
        client.messages.create.return_value = make_text_response()

        gen.generate_response(query="What is attention?")

        first_call_kwargs = client.messages.create.call_args[1]
        assert first_call_kwargs["messages"][0]["role"] == "user"
        assert first_call_kwargs["messages"][0]["content"] == "What is attention?"


# ---------------------------------------------------------------------------
# Edge case: tool_use response but no tool_manager
# ---------------------------------------------------------------------------

class TestMissingToolManager:
    def test_returns_graceful_message_when_tool_manager_missing(self, generator_and_client):
        """
        If Claude returns stop_reason='tool_use' but no tool_manager is provided,
        the generator must return a safe error message rather than crashing.

        Previously the code used a single `and` condition, causing it to fall
        through to response.content[0].text on a tool_use block (no .text attribute)
        — an AttributeError in production. The fix splits into nested ifs so the
        missing-tool_manager case is handled explicitly.
        """
        gen, client = generator_and_client
        client.messages.create.return_value = make_tool_use_response()

        result = gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=None,
        )

        assert "tool execution is not available" in result


# ---------------------------------------------------------------------------
# Sequential tool calling (up to MAX_ROUNDS = 2)
# ---------------------------------------------------------------------------

class TestSequentialToolUse:
    """
    These tests treat the generator as a black box and assert on observable
    outcomes: number of API calls, number of tool executions, return value,
    and which calls include/exclude the tools parameter.
    """

    TOOLS = [{"name": "search_course_content"}, {"name": "get_course_outline"}]

    def test_two_tool_calls_three_api_calls(self, generator_and_client):
        """Scenario C: Claude chains 2 tool calls then answers — 3 API calls total."""
        gen, client = generator_and_client
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["outline result", "search result"]

        client.messages.create.side_effect = [
            make_tool_use_response("get_course_outline",   "id1", {"course_name": "Python 101"}),
            make_tool_use_response("search_course_content","id2", {"query": "decorators"}),
            make_text_response("Here is the comparison."),
        ]

        result = gen.generate_response(query="Compare topics", tools=self.TOOLS, tool_manager=tool_manager)

        assert client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2
        assert result == "Here is the comparison."

    def test_intermediate_call_includes_tools(self, generator_and_client):
        """The second API call (between round 1 and round 2) must include tools."""
        gen, client = generator_and_client
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["result1", "result2"]

        client.messages.create.side_effect = [
            make_tool_use_response("get_course_outline",   "id1", {"course_name": "X"}),
            make_tool_use_response("search_course_content","id2", {"query": "topic"}),
            make_text_response("Final answer."),
        ]

        gen.generate_response(query="test", tools=self.TOOLS, tool_manager=tool_manager)

        second_call_kwargs = client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs
        assert "tool_choice" in second_call_kwargs

    def test_forced_final_call_excludes_tools(self, generator_and_client):
        """The third (forced) API call must NOT include tools regardless of how the loop exited."""
        gen, client = generator_and_client
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["result1", "result2"]

        client.messages.create.side_effect = [
            make_tool_use_response("get_course_outline",   "id1", {"course_name": "X"}),
            make_tool_use_response("search_course_content","id2", {"query": "topic"}),
            make_text_response("Forced final answer."),
        ]

        gen.generate_response(query="test", tools=self.TOOLS, tool_manager=tool_manager)

        third_call_kwargs = client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    def test_early_exit_when_claude_answers_mid_loop(self, generator_and_client):
        """
        Scenario: Claude calls a tool in round 1, then returns text in the intermediate
        call (round 2 start). The loop should return immediately — no forced final call.
        Total: 2 API calls, 1 tool execution.
        """
        gen, client = generator_and_client
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "outline content"

        client.messages.create.side_effect = [
            make_tool_use_response("get_course_outline", "id1", {"course_name": "X"}),
            make_text_response("I have enough info to answer now."),
        ]

        result = gen.generate_response(query="test", tools=self.TOOLS, tool_manager=tool_manager)

        assert client.messages.create.call_count == 2
        assert tool_manager.execute_tool.call_count == 1
        assert result == "I have enough info to answer now."

    def test_tool_error_string_passed_to_claude_loop_continues(self, generator_and_client):
        """
        Scenario E: Tool returns an error string (not an exception).
        The error string is valid tool result content — loop continues and Claude
        gets to reason about the failure.
        """
        gen, client = generator_and_client
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Error: course not found"

        client.messages.create.side_effect = [
            make_tool_use_response("get_course_outline", "id1", {"course_name": "X"}),
            make_text_response("I could not find the course."),
        ]

        result = gen.generate_response(query="test", tools=self.TOOLS, tool_manager=tool_manager)

        assert client.messages.create.call_count == 2
        assert tool_manager.execute_tool.call_count == 1
        # Error string is present in the messages sent to the final call
        final_call_messages = client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = next(
            m for m in final_call_messages
            if isinstance(m.get("content"), list)
            and m["content"]
            and isinstance(m["content"][0], dict)
            and m["content"][0].get("type") == "tool_result"
        )
        assert tool_result_msg["content"][0]["content"] == "Error: course not found"
        assert result == "I could not find the course."

    def test_tool_exception_exits_loop_gracefully(self, generator_and_client):
        """
        Scenario F: Tool raises an exception. Loop must exit cleanly to a forced
        final call. No exception propagates to the caller.
        """
        gen, client = generator_and_client
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = RuntimeError("DB connection failed")

        client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", "id1", {"query": "X"}),
            make_text_response("I encountered an error searching for that."),
        ]

        result = gen.generate_response(query="test", tools=self.TOOLS, tool_manager=tool_manager)

        assert client.messages.create.call_count == 2
        assert tool_manager.execute_tool.call_count == 1
        # Exception is caught and turned into a tool_result message
        final_call_messages = client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = next(
            m for m in final_call_messages
            if isinstance(m.get("content"), list)
            and m["content"]
            and isinstance(m["content"][0], dict)
            and m["content"][0].get("type") == "tool_result"
        )
        assert "Tool execution failed" in tool_result_msg["content"][0]["content"]
        assert result == "I encountered an error searching for that."
