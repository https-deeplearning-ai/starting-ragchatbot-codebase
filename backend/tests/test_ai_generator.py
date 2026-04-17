"""
Unit tests for AIGenerator.generate_response() and _handle_tool_execution().

Diagnostic focus: Does tool_use branching work correctly?
Does the final API call correctly omit tools?
Does the tool result make it back to Claude?
"""
import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator
from tests.conftest import make_text_response, make_tool_use_response


@pytest.fixture
def generator():
    """AIGenerator with a fake API key; client.messages.create will be mocked per test."""
    return AIGenerator(api_key="sk-test-fake", model="claude-3-haiku-20240307")


class TestGenerateResponseDirectPath:

    def test_returns_text_on_end_turn(self, generator):
        """
        WHAT: stop_reason=end_turn → generate_response returns text of first content block.
        ASSERT: return value equals the text in the mock.
        FAILURE MEANS: Direct (no-tool) responses are broken.
        """
        with patch.object(generator.client.messages, 'create',
                          return_value=make_text_response("Hello, I am Claude.")):
            result = generator.generate_response("What is Python?")
        assert result == "Hello, I am Claude."

    def test_system_prompt_included_without_history(self, generator):
        """
        WHAT: Without conversation_history, system param equals SYSTEM_PROMPT exactly.
        ASSERT: system kwarg passed to create() equals AIGenerator.SYSTEM_PROMPT.
        FAILURE MEANS: System prompt is corrupted on clean queries.
        """
        with patch.object(generator.client.messages, 'create',
                          return_value=make_text_response("ok")) as mock_create:
            generator.generate_response("test")
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["system"] == AIGenerator.SYSTEM_PROMPT

    def test_system_prompt_includes_history_when_provided(self, generator):
        """
        WHAT: When conversation_history is provided, system includes 'Previous conversation:'.
        ASSERT: system kwarg contains both SYSTEM_PROMPT content and the history.
        FAILURE MEANS: Conversation context is silently dropped.
        """
        with patch.object(generator.client.messages, 'create',
                          return_value=make_text_response("ok")) as mock_create:
            generator.generate_response("test", conversation_history="User: hi\nAssistant: hello")
            call_kwargs = mock_create.call_args[1]
            assert "Previous conversation:" in call_kwargs["system"]
            assert "User: hi" in call_kwargs["system"]

    def test_tools_included_in_api_call_when_provided(self, generator):
        """
        WHAT: When tools list is non-empty, tools and tool_choice appear in the API call.
        ASSERT: 'tools' and 'tool_choice' are in call kwargs.
        FAILURE MEANS: Claude never sees the search tool → answers from general knowledge only.
        """
        tool_defs = [{"name": "search_course_content", "description": "...", "input_schema": {}}]
        with patch.object(generator.client.messages, 'create',
                          return_value=make_text_response("ok")) as mock_create:
            generator.generate_response("test", tools=tool_defs)
            call_kwargs = mock_create.call_args[1]
            assert "tools" in call_kwargs
            assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_tools_absent_from_api_call_when_not_provided(self, generator):
        """
        WHAT: When no tools are passed, 'tools' key is absent from the API call.
        ASSERT: 'tools' not in call kwargs.
        FAILURE MEANS: Empty tools list might cause an API validation error.
        """
        with patch.object(generator.client.messages, 'create',
                          return_value=make_text_response("ok")) as mock_create:
            generator.generate_response("test", tools=None)
            call_kwargs = mock_create.call_args[1]
            assert "tools" not in call_kwargs


class TestHandleToolExecution:

    def test_tool_use_branch_triggers_second_api_call(self, generator):
        """
        WHAT: stop_reason=tool_use + tool_manager → _handle_tool_execution runs.
        ASSERT: create() is called TWICE (initial + intermediate follow-up WITH tools).
               Call 2 is an intermediate follow-up that still includes tools, allowing
               Claude to call another tool in a second round if needed. Here it returns
               end_turn, so no third call is made.
        FAILURE MEANS: Tool results never make it back to Claude; only one API call happens.
        """
        tool_response = make_tool_use_response("search_course_content", {"query": "python"})
        final_response = make_text_response("Python is a programming language.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "Lesson content: Python basics..."

        with patch.object(generator.client.messages, 'create',
                          side_effect=[tool_response, final_response]) as mock_create:
            result = generator.generate_response("What is Python?", tools=[{}], tool_manager=mock_manager)

        assert mock_create.call_count == 2
        assert result == "Python is a programming language."

    def test_tool_use_with_no_tool_manager_skips_tool_execution(self, generator):
        """
        WHAT: stop_reason=tool_use but tool_manager=None → the `and tool_manager` guard
              skips the tool loop entirely. The `if response.stop_reason == "tool_use"`
              guard after the loop then triggers a plain-text synthesis call.
        ASSERT: create() is called TWICE (initial tool_use response + synthesis call).
               execute_tool is never called.
        FAILURE MEANS: No synthesis call is made, causing an AttributeError when trying
                       to access .text on a ToolUseBlock.
        """
        tool_response = make_tool_use_response("search_course_content", {"query": "python"})
        final_response = make_text_response("Python is a programming language.")
        with patch.object(generator.client.messages, 'create',
                          side_effect=[tool_response, final_response]) as mock_create:
            result = generator.generate_response("What is Python?", tools=[{}], tool_manager=None)
        assert mock_create.call_count == 2
        assert result == "Python is a programming language."

    def test_synthesis_call_after_round_cap_has_no_tools(self, generator):
        """
        WHAT: When both tool rounds are exhausted (MAX_TOOL_ROUNDS=2) and Claude still
              returns tool_use, generate_response forces a final synthesis call WITHOUT
              tools to obtain a plain-text answer.
        ASSERT: The last (4th) call lacks 'tools' and 'tool_choice'.
        FAILURE MEANS: Synthesis call includes tools and fails with an API error, or
                       Claude never produces a text answer after hitting the round cap.
        """
        r1 = make_tool_use_response("search_course_content", {"query": "python"}, "tu_1")
        r2 = make_tool_use_response("search_course_content", {"query": "python2"}, "tu_2")
        r3 = make_tool_use_response("search_course_content", {"query": "python3"}, "tu_3")
        final = make_text_response("Python answer.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "tool result content"

        with patch.object(generator.client.messages, 'create',
                          side_effect=[r1, r2, r3, final]) as mock_create:
            generator.generate_response("What is Python?", tools=[{}], tool_manager=mock_manager)

        last_call_kwargs = mock_create.call_args_list[-1][1]
        assert "tools" not in last_call_kwargs
        assert "tool_choice" not in last_call_kwargs

    def test_tool_result_appended_as_user_message(self, generator):
        """
        WHAT: Tool execution result is added as a user-role message with type=tool_result.
        ASSERT: Second create() call (the intermediate follow-up WITH tools) receives 3
                messages: [original user query, assistant tool-use block, tool result].
        FAILURE MEANS: Claude never sees the search results — answers blind.
                       Critical check for the 'query failed' symptom.
        """
        tool_response = make_tool_use_response(
            "search_course_content", {"query": "python"}, "tu_test_id"
        )
        final_response = make_text_response("Python answer.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "Search result: Python basics"

        with patch.object(generator.client.messages, 'create',
                          side_effect=[tool_response, final_response]) as mock_create:
            generator.generate_response("What is Python?", tools=[{}], tool_manager=mock_manager)

        second_call_messages = mock_create.call_args_list[1][1]["messages"]
        assert len(second_call_messages) == 3
        tool_result_message = second_call_messages[2]
        assert tool_result_message["role"] == "user"
        result_blocks = tool_result_message["content"]
        assert any(
            b.get("type") == "tool_result"
            and b.get("tool_use_id") == "tu_test_id"
            and "Python basics" in b.get("content", "")
            for b in result_blocks
        )

    def test_tool_manager_execute_called_with_correct_args(self, generator):
        """
        WHAT: execute_tool() is called with the exact tool name and input that Claude requested.
        ASSERT: execute_tool called with name='search_course_content', query='variables', lesson_number=2.
        FAILURE MEANS: Parameters lost/renamed between Claude's response and the tool call.
        """
        tool_input = {"query": "variables", "lesson_number": 2}
        tool_response = make_tool_use_response("search_course_content", tool_input)
        final_response = make_text_response("Variables are...")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "content about variables"

        with patch.object(generator.client.messages, 'create',
                          side_effect=[tool_response, final_response]):
            generator.generate_response("What are variables?", tools=[{}], tool_manager=mock_manager)

        mock_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="variables", lesson_number=2
        )

    def test_tool_error_string_passed_through_to_claude(self, generator):
        """
        WHAT: If execute_tool returns an error string (e.g. from VectorStore failure),
              that error string is what Claude receives as tool_result.content.
        ASSERT: Second API call's messages include the error string verbatim.
        FAILURE MEANS: THIS EXPOSES THE ROOT CAUSE. Claude receives 'Search error: ...'
                       as its context, then tells the user it cannot answer.
        """
        error_str = (
            "Search error: Number of requested results 5 is greater than "
            "number of elements in index 0"
        )
        tool_response = make_tool_use_response("search_course_content", {"query": "python"})
        final_response = make_text_response("I couldn't find information about that.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = error_str

        with patch.object(generator.client.messages, 'create',
                          side_effect=[tool_response, final_response]) as mock_create:
            generator.generate_response("What is Python?", tools=[{}], tool_manager=mock_manager)

        second_call_messages = mock_create.call_args_list[1][1]["messages"]
        tool_result_msg = second_call_messages[2]
        content_blocks = tool_result_msg["content"]
        assert any(error_str in b.get("content", "") for b in content_blocks)


class TestSequentialToolCalling:

    def test_two_tool_rounds_makes_three_api_calls(self, generator):
        """
        WHAT: Two sequential tool rounds where each follow-up triggers another tool call,
              until the third response is end_turn.
        ASSERT: create() called 3 times, execute_tool called twice, result is the
                text from the third response.
        FAILURE MEANS: The loop exits after round 1, preventing a second tool call
                       even when Claude wants to search again.
        """
        r1 = make_tool_use_response("get_course_outline", {"course_name": "Python"}, "tu_1")
        r2 = make_tool_use_response("search_course_content", {"query": "loops"}, "tu_2")
        r3 = make_text_response("Python loops are covered in lesson 3.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "tool result"

        with patch.object(generator.client.messages, 'create',
                          side_effect=[r1, r2, r3]) as mock_create:
            result = generator.generate_response(
                "What lesson covers loops?", tools=[{}], tool_manager=mock_manager
            )

        assert mock_create.call_count == 3
        assert mock_manager.execute_tool.call_count == 2
        assert result == "Python loops are covered in lesson 3."

    def test_second_round_intermediate_call_has_tools(self, generator):
        """
        WHAT: The intermediate follow-up call after round 1 must include tools so
              Claude can decide to make a second tool call.
        ASSERT: The second create() call (index 1) has 'tools' in its kwargs.
        FAILURE MEANS: Claude cannot make a second tool call because the intermediate
                       call strips tools — the sequential feature is broken.
        """
        r1 = make_tool_use_response("get_course_outline", {"course_name": "Python"}, "tu_1")
        r2 = make_tool_use_response("search_course_content", {"query": "loops"}, "tu_2")
        r3 = make_text_response("Python loops answer.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "outline content"

        with patch.object(generator.client.messages, 'create',
                          side_effect=[r1, r2, r3]) as mock_create:
            generator.generate_response(
                "What lesson covers loops?", tools=[{}], tool_manager=mock_manager
            )

        second_call_kwargs = mock_create.call_args_list[1][1]
        assert "tools" in second_call_kwargs
        assert second_call_kwargs["tool_choice"] == {"type": "auto"}

    def test_round_cap_forces_toolless_synthesis_call(self, generator):
        """
        WHAT: When MAX_TOOL_ROUNDS (2) is exhausted and Claude still returns tool_use,
              a final synthesis call WITHOUT tools is forced to get a text answer.
        ASSERT: create() called 4 times total; last call has no 'tools' or 'tool_choice'.
        FAILURE MEANS: The round cap does not terminate the loop, or the forced synthesis
                       call incorrectly includes tools causing an API error.
        """
        r1 = make_tool_use_response("search_course_content", {"query": "q1"}, "tu_1")
        r2 = make_tool_use_response("search_course_content", {"query": "q2"}, "tu_2")
        r3 = make_tool_use_response("search_course_content", {"query": "q3"}, "tu_3")
        final = make_text_response("Here is the answer.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "result"

        with patch.object(generator.client.messages, 'create',
                          side_effect=[r1, r2, r3, final]) as mock_create:
            result = generator.generate_response(
                "Complex query", tools=[{}], tool_manager=mock_manager
            )

        assert mock_create.call_count == 4
        last_call_kwargs = mock_create.call_args_list[-1][1]
        assert "tools" not in last_call_kwargs
        assert "tool_choice" not in last_call_kwargs
        assert result == "Here is the answer."

    def test_tool_exception_stops_loop_and_proceeds_to_synthesis(self, generator):
        """
        WHAT: If execute_tool raises an Exception, the loop stops (success=False) and
              the intermediate follow-up call provides the next response. If that
              response is end_turn, no further calls are made.
        ASSERT: create() called twice, execute_tool called once, result is the text
                from the second response.
        FAILURE MEANS: An exception in execute_tool propagates uncaught, or the loop
                       continues trying more tool rounds after a hard failure.
        """
        r1 = make_tool_use_response("search_course_content", {"query": "python"}, "tu_1")
        r2 = make_text_response("I encountered an error retrieving that information.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.side_effect = Exception("DB connection failed")

        with patch.object(generator.client.messages, 'create',
                          side_effect=[r1, r2]) as mock_create:
            result = generator.generate_response(
                "What is Python?", tools=[{}], tool_manager=mock_manager
            )

        assert mock_create.call_count == 2
        assert mock_manager.execute_tool.call_count == 1
        assert result == "I encountered an error retrieving that information."

    def test_accumulated_messages_grow_across_rounds(self, generator):
        """
        WHAT: After two tool rounds, the third API call receives the full accumulated
              message history: [user_query, asst_tool1, tool_result_1, asst_tool2, tool_result_2].
        ASSERT: Third create() call's messages list has exactly 5 items.
        FAILURE MEANS: Context is not preserved between rounds; Claude answers without
                       seeing results from earlier tool calls.
        """
        r1 = make_tool_use_response("get_course_outline", {"course_name": "Python"}, "tu_1")
        r2 = make_tool_use_response("search_course_content", {"query": "lesson 3"}, "tu_2")
        r3 = make_text_response("Lesson 3 covers loops.")
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "tool content"

        with patch.object(generator.client.messages, 'create',
                          side_effect=[r1, r2, r3]) as mock_create:
            generator.generate_response(
                "What does lesson 3 cover?", tools=[{}], tool_manager=mock_manager
            )

        third_call_messages = mock_create.call_args_list[2][1]["messages"]
        assert len(third_call_messages) == 5
