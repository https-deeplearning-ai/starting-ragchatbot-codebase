"""
Tests for AIGenerator in ai_generator.py.

All tests mock the Anthropic client to avoid real API calls.
They verify that AIGenerator correctly:
  - Calls the search_course_content tool for content queries
  - Processes tool_use responses by executing tools and feeding results back
  - Returns plain text when no tool use is needed
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Helpers to build mock Anthropic response objects
# ---------------------------------------------------------------------------

def make_text_content(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_content(tool_name, tool_input, tool_id="tool_call_1"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_id
    return block


def make_response(stop_reason, content_blocks):
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content_blocks
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAIGeneratorDirectResponse:

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_returns_text_for_general_query(self, mock_anthropic_cls):
        """When Claude responds with end_turn, the text is returned directly."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_content("Paris is the capital of France.")],
        )

        gen = AIGenerator(api_key="test-key", model="claude-test")
        result = gen.generate_response(query="What is the capital of France?")

        assert result == "Paris is the capital of France."

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_includes_tools_in_api_call(self, mock_anthropic_cls):
        """When tools are provided, they are included in the API call parameters."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_content("Some answer.")],
        )

        tool_def = {"name": "search_course_content", "description": "...", "input_schema": {}}
        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.generate_response(query="What is in lesson 1?", tools=[tool_def])

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == [tool_def]
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_no_tools_if_not_provided(self, mock_anthropic_cls):
        """When no tools are passed, the API call has no tools key."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_content("Answer.")],
        )

        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.generate_response(query="Hello")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" not in call_kwargs


class TestAIGeneratorToolExecution:

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_is_executed_on_tool_use_stop_reason(self, mock_anthropic_cls):
        """When stop_reason is tool_use, the tool is executed and the final text is returned."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_content(
            "search_course_content", {"query": "transformers"}, "id_1"
        )
        first_response = make_response(stop_reason="tool_use", content_blocks=[tool_block])
        final_response = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_content("Transformers use attention.")],
        )
        mock_client.messages.create.side_effect = [first_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Transformers are attention models."

        gen = AIGenerator(api_key="test-key", model="claude-test")
        result = gen.generate_response(
            query="What are transformers?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert result == "Transformers use attention."
        assert mock_client.messages.create.call_count == 2
        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="transformers"
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_result_sent_back_as_user_message(self, mock_anthropic_cls):
        """Tool result is appended to the conversation as a user message with tool_result type."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_content(
            "search_course_content", {"query": "MCP"}, "call_abc"
        )
        first_response = make_response(stop_reason="tool_use", content_blocks=[tool_block])
        final_response = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_content("MCP stands for Model Context Protocol.")],
        )
        mock_client.messages.create.side_effect = [first_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "MCP lesson content here."

        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.generate_response(
            query="What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        # The second API call should include a user message with tool_result
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        # Find the user message containing tool results
        tool_result_message = next(
            (m for m in messages if m["role"] == "user" and isinstance(m["content"], list)),
            None,
        )
        assert tool_result_message is not None
        tool_result_block = tool_result_message["content"][0]
        assert tool_result_block["type"] == "tool_result"
        assert tool_result_block["tool_use_id"] == "call_abc"
        assert tool_result_block["content"] == "MCP lesson content here."

    @patch("ai_generator.anthropic.Anthropic")
    def test_final_api_call_has_no_tools(self, mock_anthropic_cls):
        """After MAX_ROUNDS of tool use, the post-loop final API call has no tools."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block1 = make_tool_use_content("search_course_content", {"query": "AI"}, "id_1")
        tool_block2 = make_tool_use_content("get_course_outline", {"course_name": "AI"}, "id_2")
        round1_response = make_response(stop_reason="tool_use", content_blocks=[tool_block1])
        round2_response = make_response(stop_reason="tool_use", content_blocks=[tool_block2])
        final_response = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_content("AI answer.")],
        )
        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Some search result."

        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.generate_response(
            query="Tell me about AI",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        # Third call (post-loop) should NOT include tools
        assert mock_client.messages.create.call_count == 3
        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_conversation_history(self, mock_anthropic_cls):
        """Conversation history is injected into the system prompt, not messages."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_content("Follow-up answer.")],
        )

        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.generate_response(
            query="What about lesson 2?",
            conversation_history="User: What is lesson 1?\nAssistant: Lesson 1 covers X.",
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        system_content = call_kwargs["system"]
        assert "Previous conversation" in system_content
        assert "What is lesson 1?" in system_content
        # History should be in system, not in messages
        assert len(call_kwargs["messages"]) == 1


class TestAIGeneratorSearchToolCalling:

    @patch("ai_generator.anthropic.Anthropic")
    def test_content_query_triggers_search_tool_call(self, mock_anthropic_cls):
        """
        Verifies the full loop: content query → Claude requests search_course_content
        tool → tool is executed → final answer is returned.
        """
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_content(
            "search_course_content",
            {"query": "what does lesson 1 cover", "course_name": "AI Course"},
            "search_id_1",
        )
        first_response = make_response(stop_reason="tool_use", content_blocks=[tool_block])
        final_response = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_content("Lesson 1 covers neural networks.")],
        )
        mock_client.messages.create.side_effect = [first_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = (
            "[AI Course - Lesson 1]\nThis lesson introduces neural networks."
        )

        gen = AIGenerator(api_key="test-key", model="claude-test")
        search_tool_def = {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        }
        result = gen.generate_response(
            query="Answer this question about course materials: What does lesson 1 cover?",
            tools=[search_tool_def],
            tool_manager=tool_manager,
        )

        assert result == "Lesson 1 covers neural networks."
        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="what does lesson 1 cover",
            course_name="AI Course",
        )


class TestAIGeneratorTwoRoundToolCalling:
    """Tests for sequential 2-round tool-calling behavior."""

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_sequential_tool_calls_makes_three_api_calls(self, mock_anthropic_cls):
        """Two rounds of tool use followed by end_turn results in exactly 3 API calls."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tb1 = make_tool_use_content("get_course_outline", {"course_name": "X"}, "id_1")
        tb2 = make_tool_use_content("search_course_content", {"query": "topic"}, "id_2")
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tb1]),
            make_response("tool_use", [tb2]),
            make_response("end_turn", [make_text_content("Final answer.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "some result"

        gen = AIGenerator(api_key="test-key", model="claude-test")
        result = gen.generate_response(
            query="Search for a course on the same topic as lesson 4 of course X",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert mock_client.messages.create.call_count == 3
        assert result == "Final answer."
        assert tool_manager.execute_tool.call_count == 2

    @patch("ai_generator.anthropic.Anthropic")
    def test_tools_included_in_second_round_api_call(self, mock_anthropic_cls):
        """The second API call (round 2) still includes tools so Claude can use them again."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tb1 = make_tool_use_content("get_course_outline", {"course_name": "X"}, "id_1")
        tb2 = make_tool_use_content("search_course_content", {"query": "topic"}, "id_2")
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tb1]),
            make_response("tool_use", [tb2]),
            make_response("end_turn", [make_text_content("Done.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.generate_response(
            query="Multi-step query",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_final_call_after_max_rounds_has_no_tools(self, mock_anthropic_cls):
        """The post-loop final call (3rd) after hitting MAX_ROUNDS has no tools."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tb1 = make_tool_use_content("search_course_content", {"query": "a"}, "id_1")
        tb2 = make_tool_use_content("search_course_content", {"query": "b"}, "id_2")
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tb1]),
            make_response("tool_use", [tb2]),
            make_response("end_turn", [make_text_content("Answer.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.generate_response(
            query="Query",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_message_list_grows_with_each_round(self, mock_anthropic_cls):
        """After 2 rounds, the final API call receives 5 messages in the correct order."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tb1 = make_tool_use_content("get_course_outline", {"course_name": "X"}, "id_1")
        tb2 = make_tool_use_content("search_course_content", {"query": "topic"}, "id_2")
        r1 = make_response("tool_use", [tb1])
        r2 = make_response("tool_use", [tb2])
        mock_client.messages.create.side_effect = [
            r1, r2,
            make_response("end_turn", [make_text_content("Done.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.generate_response(
            query="Complex query",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        final_call_messages = mock_client.messages.create.call_args_list[2][1]["messages"]
        assert len(final_call_messages) == 5
        assert final_call_messages[0]["role"] == "user"       # original query
        assert final_call_messages[1]["role"] == "assistant"  # round 1 tool-use
        assert final_call_messages[2]["role"] == "user"       # round 1 tool-results
        assert final_call_messages[3]["role"] == "assistant"  # round 2 tool-use
        assert final_call_messages[4]["role"] == "user"       # round 2 tool-results

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_error_does_not_terminate_loop(self, mock_anthropic_cls):
        """A tool returning an error string is passed as context; the loop continues."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tb = make_tool_use_content("search_course_content", {"query": "x"}, "id_err")
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tb]),
            make_response("end_turn", [make_text_content("Sorry, search failed.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Search error: n_results must be positive"

        gen = AIGenerator(api_key="test-key", model="claude-test")
        result = gen.generate_response(
            query="Find something",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert mock_client.messages.create.call_count == 2
        assert result == "Sorry, search failed."

        # Error string passed as tool_result content in second call
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = next(
            m for m in second_call_messages
            if m["role"] == "user" and isinstance(m["content"], list)
        )
        assert tool_result_msg["content"][0]["content"] == "Search error: n_results must be positive"

    @patch("ai_generator.anthropic.Anthropic")
    def test_early_exit_when_no_tool_use_in_first_response(self, mock_anthropic_cls):
        """When the first response has end_turn, only 1 API call is made."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_response(
            "end_turn", [make_text_content("Direct answer.")]
        )

        gen = AIGenerator(api_key="test-key", model="claude-test")
        result = gen.generate_response(
            query="What is 2+2?",
            tools=[{"name": "search_course_content"}],
            tool_manager=MagicMock(),
        )

        assert mock_client.messages.create.call_count == 1
        assert result == "Direct answer."

    @patch("ai_generator.anthropic.Anthropic")
    def test_early_exit_after_first_round_no_second_tool_use(self, mock_anthropic_cls):
        """When round 2 returns end_turn, exactly 2 API calls are made (no third call)."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tb = make_tool_use_content("search_course_content", {"query": "topic"}, "id_1")
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tb]),
            make_response("end_turn", [make_text_content("Answer after one search.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "search result"

        gen = AIGenerator(api_key="test-key", model="claude-test")
        result = gen.generate_response(
            query="Find info on topic",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert mock_client.messages.create.call_count == 2
        assert result == "Answer after one search."

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_tool_results_in_single_round_appended_correctly(self, mock_anthropic_cls):
        """When a single round contains 2 tool-use blocks, both are executed and appended."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tb1 = make_tool_use_content("search_course_content", {"query": "a"}, "id_a")
        tb2 = make_tool_use_content("get_course_outline", {"course_name": "X"}, "id_b")
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tb1, tb2]),
            make_response("end_turn", [make_text_content("Both results used.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        gen = AIGenerator(api_key="test-key", model="claude-test")
        result = gen.generate_response(
            query="Compare two things",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert tool_manager.execute_tool.call_count == 2
        assert result == "Both results used."

        # Second API call should have a user message with 2 tool_result dicts
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = next(
            m for m in second_call_messages
            if m["role"] == "user" and isinstance(m["content"], list)
        )
        assert len(tool_result_msg["content"]) == 2
        assert tool_result_msg["content"][0]["tool_use_id"] == "id_a"
        assert tool_result_msg["content"][1]["tool_use_id"] == "id_b"
