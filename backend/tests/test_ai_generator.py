"""
Tests for AIGenerator in ai_generator.py.

All assertions are on observable external behavior:
  - how many times the Anthropic client was called
  - which tools were executed and with what arguments
  - what string generate_response() returned
  - what parameters were passed to each API call
"""

from unittest.mock import MagicMock, patch

from ai_generator import AIGenerator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_generator():
    """Return an AIGenerator whose Anthropic client is fully mocked."""
    with patch("ai_generator.anthropic.Anthropic"):
        gen = AIGenerator(api_key="fake-key", model="fake-model")
        gen.client = MagicMock()
        return gen


def _make_text_response(text="Answer text"):
    """Simulate a Claude response that produces plain text (no tool use)."""
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    resp.content = [text_block]
    return resp


def _make_tool_use_response(
    tool_name="search_course_content",
    tool_input=None,
    tool_id="tool_abc",
):
    """Simulate a Claude response that requests a tool call."""
    if tool_input is None:
        tool_input = {"query": "what is RAG"}
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = tool_id
    tool_block.name = tool_name
    tool_block.input = tool_input

    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = [tool_block]
    return resp


def _make_tool_manager(return_value="search results"):
    tm = MagicMock()
    tm.execute_tool.return_value = return_value
    return tm


TOOL_DEFINITIONS = [
    {
        "name": "search_course_content",
        "description": "Search course materials",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }
]


# ---------------------------------------------------------------------------
# Direct-response path (no tool use)
# ---------------------------------------------------------------------------


class TestGenerateResponseDirect:

    def test_returns_text_when_stop_reason_is_end_turn(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_text_response("Hello world")

        result = gen.generate_response("What is 2+2?")

        assert result == "Hello world"

    def test_api_called_once_for_direct_response(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_text_response()

        gen.generate_response("test")

        assert gen.client.messages.create.call_count == 1

    def test_api_called_with_correct_model(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_text_response()

        gen.generate_response("test")

        kwargs = gen.client.messages.create.call_args[1]
        assert kwargs["model"] == "fake-model"

    def test_system_prompt_included(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_text_response()

        gen.generate_response("test")

        kwargs = gen.client.messages.create.call_args[1]
        assert "system" in kwargs and len(kwargs["system"]) > 0

    def test_conversation_history_appended_to_system_prompt(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_text_response()

        gen.generate_response("test", conversation_history="User: hi\nAssistant: hello")

        kwargs = gen.client.messages.create.call_args[1]
        assert "Previous conversation" in kwargs["system"]
        assert "User: hi" in kwargs["system"]

    def test_tools_passed_to_first_call_when_provided(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_text_response()

        gen.generate_response("test", tools=TOOL_DEFINITIONS)

        kwargs = gen.client.messages.create.call_args[1]
        assert kwargs["tools"] == TOOL_DEFINITIONS

    def test_tool_choice_auto_set_when_tools_provided(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_text_response()

        gen.generate_response("test", tools=TOOL_DEFINITIONS)

        kwargs = gen.client.messages.create.call_args[1]
        assert kwargs.get("tool_choice") == {"type": "auto"}

    def test_no_tool_choice_when_no_tools(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_text_response()

        gen.generate_response("test")

        kwargs = gen.client.messages.create.call_args[1]
        assert "tool_choice" not in kwargs


# ---------------------------------------------------------------------------
# Single tool-use round
# ---------------------------------------------------------------------------


class TestSingleRoundToolUse:
    """Claude requests one tool call, then returns a text answer."""

    def test_returns_final_text(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(),
            _make_text_response("RAG means Retrieval-Augmented Generation"),
        ]

        result = gen.generate_response(
            "What is RAG?", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        assert result == "RAG means Retrieval-Augmented Generation"

    def test_api_called_twice(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(),
            _make_text_response(),
        ]

        gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        assert gen.client.messages.create.call_count == 2

    def test_execute_tool_called_once_with_correct_args(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(
                tool_input={"query": "vector stores", "course_name": "RAG"}
            ),
            _make_text_response(),
        ]
        tm = _make_tool_manager()

        gen.generate_response("question", tools=TOOL_DEFINITIONS, tool_manager=tm)

        tm.execute_tool.assert_called_once_with(
            "search_course_content", query="vector stores", course_name="RAG"
        )

    def test_follow_up_call_includes_tools(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(),
            _make_text_response(),
        ]

        gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs

    def test_follow_up_messages_are_user_assistant_user(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(),
            _make_text_response(),
        ]

        gen.generate_response(
            "my question", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_tool_result_carries_correct_tool_use_id(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_id="tid_xyz"),
            _make_text_response(),
        ]

        gen.generate_response(
            "q", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        tool_result_block = second_call_kwargs["messages"][2]["content"][0]
        assert tool_result_block["tool_use_id"] == "tid_xyz"

    def test_follow_up_call_does_not_set_tool_choice(self):
        """Follow-up calls omit tool_choice so Claude can freely choose to answer without tools."""
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(),
            _make_text_response(),
        ]

        gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        assert "tool_choice" not in second_call_kwargs


# ---------------------------------------------------------------------------
# Two sequential tool-use rounds
# ---------------------------------------------------------------------------


class TestTwoRoundToolUse:
    """Claude uses the search tool twice in separate rounds before answering."""

    def test_returns_final_text_after_two_rounds(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(
                tool_input={"query": "lesson 4 title"}, tool_id="t1"
            ),
            _make_tool_use_response(tool_input={"query": "found topic"}, tool_id="t2"),
            _make_text_response("Here is the course that covers the same topic."),
        ]

        result = gen.generate_response(
            "Find a course covering lesson 4 of course X",
            tools=TOOL_DEFINITIONS,
            tool_manager=_make_tool_manager(),
        )

        assert result == "Here is the course that covers the same topic."

    def test_api_called_three_times(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_id="t1"),
            _make_tool_use_response(tool_id="t2"),
            _make_text_response(),
        ]

        gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        assert gen.client.messages.create.call_count == 3

    def test_execute_tool_called_twice(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_input={"query": "first search"}, tool_id="t1"),
            _make_tool_use_response(
                tool_input={"query": "second search"}, tool_id="t2"
            ),
            _make_text_response(),
        ]
        tm = _make_tool_manager()

        gen.generate_response("question", tools=TOOL_DEFINITIONS, tool_manager=tm)

        assert tm.execute_tool.call_count == 2

    def test_both_tool_inputs_passed_to_execute_tool(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_input={"query": "first search"}, tool_id="t1"),
            _make_tool_use_response(
                tool_input={"query": "second search"}, tool_id="t2"
            ),
            _make_text_response(),
        ]
        tm = _make_tool_manager()

        gen.generate_response("question", tools=TOOL_DEFINITIONS, tool_manager=tm)

        call_queries = [c[1]["query"] for c in tm.execute_tool.call_args_list]
        assert "first search" in call_queries
        assert "second search" in call_queries

    def test_all_follow_up_calls_include_tools(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_id="t1"),
            _make_tool_use_response(tool_id="t2"),
            _make_text_response(),
        ]

        gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        for i in (1, 2):
            kwargs = gen.client.messages.create.call_args_list[i][1]
            assert "tools" in kwargs, f"Call #{i + 1} is missing 'tools'"

    def test_messages_accumulate_across_both_rounds(self):
        """Third API call must see all five prior messages."""
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_id="t1"),
            _make_tool_use_response(tool_id="t2"),
            _make_text_response(),
        ]

        gen.generate_response(
            "my query", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        third_call_kwargs = gen.client.messages.create.call_args_list[2][1]
        messages = third_call_kwargs["messages"]
        # [user_query, asst(round1), user(round1_results), asst(round2), user(round2_results)]
        assert len(messages) == 5
        roles = [m["role"] for m in messages]
        assert roles == ["user", "assistant", "user", "assistant", "user"]


# ---------------------------------------------------------------------------
# Max-rounds termination
# ---------------------------------------------------------------------------


class TestMaxRoundsTermination:
    """Loop stops after _MAX_TOOL_ROUNDS even if Claude still wants more tools."""

    def test_api_called_three_times_when_all_responses_are_tool_use(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_id="t1"),
            _make_tool_use_response(tool_id="t2"),
            _make_tool_use_response(tool_id="t3"),  # loop exits after this
        ]

        gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        assert gen.client.messages.create.call_count == 3

    def test_execute_tool_called_exactly_twice_at_max_rounds(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_id="t1"),
            _make_tool_use_response(tool_id="t2"),
            _make_tool_use_response(tool_id="t3"),
        ]
        tm = _make_tool_manager()

        gen.generate_response("question", tools=TOOL_DEFINITIONS, tool_manager=tm)

        assert tm.execute_tool.call_count == 2

    def test_returns_fallback_string_when_max_rounds_exhausted(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_id="t1"),
            _make_tool_use_response(tool_id="t2"),
            _make_tool_use_response(tool_id="t3"),
        ]

        result = gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=_make_tool_manager()
        )

        assert isinstance(result, str) and len(result) > 0


# ---------------------------------------------------------------------------
# Tool execution errors
# ---------------------------------------------------------------------------


class TestToolExecutionErrors:

    def test_exception_from_execute_tool_does_not_propagate(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_tool_use_response()
        tm = MagicMock()
        tm.execute_tool.side_effect = Exception("DB unavailable")

        result = gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=tm
        )

        assert isinstance(result, str)

    def test_exception_aborts_after_first_api_call(self):
        """No follow-up API call should be made after a tool execution exception."""
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_tool_use_response()
        tm = MagicMock()
        tm.execute_tool.side_effect = Exception("crash")

        gen.generate_response("question", tools=TOOL_DEFINITIONS, tool_manager=tm)

        assert gen.client.messages.create.call_count == 1

    def test_error_string_from_execute_tool_continues_loop(self):
        """An error string (not exception) is treated as valid content — Claude continues."""
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(),
            _make_text_response("Based on available information..."),
        ]
        tm = MagicMock()
        tm.execute_tool.return_value = "No relevant content found"

        result = gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=tm
        )

        assert gen.client.messages.create.call_count == 2
        assert result == "Based on available information..."

    def test_error_string_content_appears_in_follow_up_messages(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(tool_id="t1"),
            _make_text_response("answer"),
        ]
        tm = MagicMock()
        tm.execute_tool.return_value = "No relevant content found"

        gen.generate_response("question", tools=TOOL_DEFINITIONS, tool_manager=tm)

        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        tool_result_content = second_call_kwargs["messages"][2]["content"][0]["content"]
        assert tool_result_content == "No relevant content found"


# ---------------------------------------------------------------------------
# Miscellaneous / edge cases
# ---------------------------------------------------------------------------


class TestMiscBehavior:

    def test_no_tool_manager_with_tool_use_response_returns_fallback(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_tool_use_response()

        result = gen.generate_response(
            "question", tools=TOOL_DEFINITIONS, tool_manager=None
        )

        assert isinstance(result, str) and len(result) > 0
        assert gen.client.messages.create.call_count == 1

    def test_conversation_history_present_in_all_api_calls(self):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [
            _make_tool_use_response(),
            _make_text_response("done"),
        ]

        gen.generate_response(
            "question",
            conversation_history="User: hello\nAssistant: hi",
            tools=TOOL_DEFINITIONS,
            tool_manager=_make_tool_manager(),
        )

        for i, call in enumerate(gen.client.messages.create.call_args_list):
            system = call[1]["system"]
            assert (
                "User: hello" in system
            ), f"Call #{i + 1} missing conversation history"

    def test_system_prompt_removed_one_search_limit(self):
        assert "One search per query maximum" not in AIGenerator.SYSTEM_PROMPT

    def test_system_prompt_allows_up_to_two_searches(self):
        prompt = AIGenerator.SYSTEM_PROMPT.lower()
        assert "2" in prompt or "two" in prompt or "sequential" in prompt
