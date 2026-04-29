import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator
from tests.helpers import make_text_block, make_tool_use_block, make_message


@pytest.fixture
def generator():
    with patch("ai_generator.anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
        gen._mock_create = mock_client.messages.create
        yield gen


class TestDirectResponse:

    def test_direct_response_returns_text(self, generator):
        generator._mock_create.return_value = make_message(
            [make_text_block("Here is your answer.")], stop_reason="end_turn"
        )
        result = generator.generate_response(query="What is Python?")
        assert result == "Here is your answer."

    def test_no_history_uses_bare_system_prompt(self, generator):
        generator._mock_create.return_value = make_message(
            [make_text_block("answer")], stop_reason="end_turn"
        )
        generator.generate_response(query="Hello", conversation_history=None)
        call_kwargs = generator._mock_create.call_args.kwargs
        assert call_kwargs["system"] == AIGenerator.SYSTEM_PROMPT

    def test_with_history_appends_to_system_prompt(self, generator):
        generator._mock_create.return_value = make_message(
            [make_text_block("answer")], stop_reason="end_turn"
        )
        history = "User: hi\nAssistant: hello"
        generator.generate_response(query="follow-up", conversation_history=history)
        call_kwargs = generator._mock_create.call_args.kwargs
        assert AIGenerator.SYSTEM_PROMPT in call_kwargs["system"]
        assert history in call_kwargs["system"]

    def test_empty_content_returns_empty_string(self, generator):
        generator._mock_create.return_value = make_message([], stop_reason="end_turn")
        result = generator.generate_response(query="anything")
        assert result == ""


class TestToolUseFlow:

    def test_tool_use_calls_execute_tool_with_correct_args(self, generator):
        tool_input = {"query": "what is RAG?", "course_name": "AI Fundamentals"}
        generator._mock_create.side_effect = [
            make_message(
                [make_tool_use_block("search_course_content", tool_input)],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("RAG stands for Retrieval-Augmented Generation.")],
                stop_reason="end_turn",
            ),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "search result"
        generator.generate_response(
            query="what is RAG?", tools=[{}], tool_manager=mock_tm
        )
        mock_tm.execute_tool.assert_called_once_with(
            "search_course_content", query="what is RAG?", course_name="AI Fundamentals"
        )

    def test_tool_use_second_call_has_tool_result_in_messages(self, generator):
        tool_input = {"query": "loops"}
        generator._mock_create.side_effect = [
            make_message(
                [
                    make_tool_use_block(
                        "search_course_content", tool_input, block_id="tu_42"
                    )
                ],
                stop_reason="tool_use",
            ),
            make_message([make_text_block("Final answer.")], stop_reason="end_turn"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "Tool output text"
        generator.generate_response(query="loops", tools=[{}], tool_manager=mock_tm)
        assert generator._mock_create.call_count == 2
        second_call_kwargs = generator._mock_create.call_args.kwargs
        messages = second_call_kwargs["messages"]
        last_msg = messages[-1]
        assert last_msg["role"] == "user"
        assert last_msg["content"][0]["type"] == "tool_result"
        assert last_msg["content"][0]["tool_use_id"] == "tu_42"
        assert last_msg["content"][0]["content"] == "Tool output text"

    def test_tool_use_second_call_preserves_tools_param(self, generator):
        tool_input = {"query": "x"}
        generator._mock_create.side_effect = [
            make_message(
                [make_tool_use_block("search_course_content", tool_input)],
                stop_reason="tool_use",
            ),
            make_message([make_text_block("Answer.")], stop_reason="end_turn"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "result"
        generator.generate_response(query="x", tools=[{}], tool_manager=mock_tm)
        second_call_kwargs = generator._mock_create.call_args.kwargs
        assert "tools" in second_call_kwargs

    def test_tool_use_returns_synthesized_text(self, generator):
        generator._mock_create.side_effect = [
            make_message(
                [make_tool_use_block("search_course_content", {"query": "q"})],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("Synthesized answer here.")], stop_reason="end_turn"
            ),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "search result"
        result = generator.generate_response(
            query="q", tools=[{}], tool_manager=mock_tm
        )
        assert result == "Synthesized answer here."

    def test_exceeds_max_rounds_returns_fallback(self, generator):
        # Every API call returns tool_use — loop exhausts max_rounds then returns fallback
        generator._mock_create.return_value = make_message(
            [make_tool_use_block("search_course_content", {"query": "q"})],
            stop_reason="tool_use",
        )
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "result"
        result = generator.generate_response(
            query="q", tools=[{}], tool_manager=mock_tm, max_rounds=2
        )
        assert result != ""
        assert generator._mock_create.call_count == 3  # 1 initial + 2 loop iterations

    def test_two_round_tool_calling(self, generator):
        generator._mock_create.side_effect = [
            make_message(
                [make_tool_use_block("search_course_content", {"query": "q1"}, "tu_1")],
                stop_reason="tool_use",
            ),
            make_message(
                [make_tool_use_block("search_course_content", {"query": "q2"}, "tu_2")],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("Final answer after two searches.")],
                stop_reason="end_turn",
            ),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "result"
        result = generator.generate_response(
            query="q", tools=[{}], tool_manager=mock_tm, max_rounds=5
        )
        assert result == "Final answer after two searches."
        assert generator._mock_create.call_count == 3
