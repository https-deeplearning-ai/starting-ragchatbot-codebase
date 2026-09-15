"""
Objective 2: AIGenerator unit tests. The Anthropic client is mocked;
tool_manager is a MagicMock(spec=ToolManager) so call args can be asserted
exactly. No network calls, no real tools, no real VectorStore.
"""

from types import SimpleNamespace


class TestToolUseFlow:
    def test_tool_use_triggers_execute_tool_with_exact_kwargs(
        self, ai_generator, mock_tool_manager, text_response, tool_use_response
    ):
        initial = tool_use_response(
            [
                {
                    "name": "search_course_content",
                    "input": {"query": "prompt caching", "course_name": "Computer Use"},
                    "id": "toolu_1",
                }
            ]
        )
        final = text_response("Here is the answer.")
        ai_generator.client.messages.create.side_effect = [initial, final]
        mock_tool_manager.execute_tool.return_value = "tool result text"

        result = ai_generator.generate_response(
            query="What is prompt caching?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="prompt caching", course_name="Computer Use"
        )
        assert result == "Here is the answer."

    def test_follow_up_call_appends_assistant_and_tool_result_messages(
        self, ai_generator, mock_tool_manager, text_response, tool_use_response
    ):
        initial = tool_use_response(
            [
                {
                    "name": "search_course_content",
                    "input": {"query": "x"},
                    "id": "toolu_42",
                }
            ]
        )
        final = text_response("answer")
        ai_generator.client.messages.create.side_effect = [initial, final]
        mock_tool_manager.execute_tool.return_value = "the tool output"

        ai_generator.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert ai_generator.client.messages.create.call_count == 2
        second_call_kwargs = ai_generator.client.messages.create.call_args_list[
            1
        ].kwargs
        messages = second_call_kwargs["messages"]

        assert messages[0] == {"role": "user", "content": "q"}
        assert messages[1] == {"role": "assistant", "content": initial.content}
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_42",
                "content": "the tool output",
            }
        ]

    def test_follow_up_call_excludes_tools_and_tool_choice(
        self, ai_generator, mock_tool_manager, text_response, tool_use_response
    ):
        initial = tool_use_response(
            [
                {
                    "name": "search_course_content",
                    "input": {"query": "x"},
                    "id": "toolu_1",
                }
            ]
        )
        final = text_response("answer")
        ai_generator.client.messages.create.side_effect = [initial, final]
        mock_tool_manager.execute_tool.return_value = "result"

        ai_generator.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        second_call_kwargs = ai_generator.client.messages.create.call_args_list[
            1
        ].kwargs
        assert "tools" not in second_call_kwargs
        assert "tool_choice" not in second_call_kwargs

    def test_multiple_parallel_tool_use_blocks_all_executed(
        self, ai_generator, mock_tool_manager, text_response, tool_use_response
    ):
        initial = tool_use_response(
            [
                {
                    "name": "search_course_content",
                    "input": {"query": "a"},
                    "id": "toolu_1",
                },
                {
                    "name": "get_course_outline",
                    "input": {"course_title": "MCP"},
                    "id": "toolu_2",
                },
            ]
        )
        final = text_response("combined answer")
        ai_generator.client.messages.create.side_effect = [initial, final]
        mock_tool_manager.execute_tool.side_effect = ["result A", "result B"]

        ai_generator.generate_response(
            query="q", tools=[{"name": "x"}], tool_manager=mock_tool_manager
        )

        assert mock_tool_manager.execute_tool.call_count == 2
        second_call_kwargs = ai_generator.client.messages.create.call_args_list[
            1
        ].kwargs
        tool_result_message = second_call_kwargs["messages"][2]
        assert tool_result_message["content"] == [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "result A"},
            {"type": "tool_result", "tool_use_id": "toolu_2", "content": "result B"},
        ]


class TestNoToolUseFlow:
    def test_no_tools_passed_omits_tools_and_tool_choice_keys(
        self, ai_generator, text_response
    ):
        ai_generator.client.messages.create.return_value = text_response("plain answer")

        result = ai_generator.generate_response(query="hello")

        call_kwargs = ai_generator.client.messages.create.call_args.kwargs
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs
        assert result == "plain answer"

    def test_plain_text_stop_reason_never_invokes_tool_manager(
        self, ai_generator, mock_tool_manager, text_response
    ):
        ai_generator.client.messages.create.return_value = text_response(
            "general knowledge answer", stop_reason="end_turn"
        )

        result = ai_generator.generate_response(
            query="what is 2+2?", tools=[{"name": "x"}], tool_manager=mock_tool_manager
        )

        mock_tool_manager.execute_tool.assert_not_called()
        assert result == "general knowledge answer"
        assert ai_generator.client.messages.create.call_count == 1


class TestExtractTextWithRetry:
    def test_retries_exactly_once_when_first_response_has_no_text_block(
        self, ai_generator, text_response
    ):
        empty = SimpleNamespace(stop_reason="end_turn", content=[])
        recovered = text_response("recovered text")
        ai_generator.client.messages.create.side_effect = [empty, recovered]

        result = ai_generator.generate_response(query="q")

        assert result == "recovered text"
        assert ai_generator.client.messages.create.call_count == 2

    def test_returns_empty_string_without_looping_if_retry_is_also_textless(
        self, ai_generator
    ):
        empty1 = SimpleNamespace(stop_reason="end_turn", content=[])
        empty2 = SimpleNamespace(stop_reason="end_turn", content=[])
        ai_generator.client.messages.create.side_effect = [empty1, empty2]

        result = ai_generator.generate_response(query="q")

        assert result == ""
        # confirms no infinite retry loop: exactly initial call + one retry
        assert ai_generator.client.messages.create.call_count == 2


class TestSystemPromptAndParams:
    def test_conversation_history_is_appended_to_system_prompt(
        self, ai_generator, text_response
    ):
        ai_generator.client.messages.create.return_value = text_response("ok")

        ai_generator.generate_response(
            query="q", conversation_history="User: hi\nAssistant: hello"
        )

        call_kwargs = ai_generator.client.messages.create.call_args.kwargs
        assert "Previous conversation:" in call_kwargs["system"]
        assert "User: hi" in call_kwargs["system"]

    def test_no_conversation_history_uses_bare_system_prompt(
        self, ai_generator, text_response
    ):
        ai_generator.client.messages.create.return_value = text_response("ok")

        ai_generator.generate_response(query="q")

        call_kwargs = ai_generator.client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == ai_generator.SYSTEM_PROMPT

    def test_never_sends_a_temperature_param(self, ai_generator, text_response):
        """
        Regression guard: this specific model rejects `temperature` as a
        deprecated param (confirmed via a live 400 error). Must never appear
        in base_params or in any messages.create call.
        """
        ai_generator.client.messages.create.return_value = text_response("ok")

        ai_generator.generate_response(query="q")

        assert "temperature" not in ai_generator.base_params
        call_kwargs = ai_generator.client.messages.create.call_args.kwargs
        assert "temperature" not in call_kwargs
