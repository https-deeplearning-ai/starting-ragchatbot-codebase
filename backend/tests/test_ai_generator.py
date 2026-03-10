"""
Tests for AIGenerator.generate_response() and _handle_tool_execution()

The Anthropic client is fully mocked so no real API calls are made.
"""

import pytest
from unittest.mock import MagicMock, patch

from helpers import build_text_response, build_tool_use_response
from ai_generator import AIGenerator


@pytest.fixture
def mock_anthropic_client():
    """Patch anthropic.Anthropic so no real client is created"""
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def generator(mock_anthropic_client):
    return AIGenerator(api_key="test-key", model="claude-test")


# ── basic text response ───────────────────────────────────────────────────────


def test_returns_text_from_content_block(generator, mock_anthropic_client):
    mock_anthropic_client.messages.create.return_value = build_text_response(
        "Hello world"
    )
    result = generator.generate_response(query="Hi")
    assert result == "Hello world"


def test_does_not_call_tool_manager_when_end_turn(generator, mock_anthropic_client):
    mock_anthropic_client.messages.create.return_value = build_text_response("Answer")
    tool_manager = MagicMock()
    generator.generate_response(query="Hi", tool_manager=tool_manager)
    tool_manager.execute_tool.assert_not_called()


# ── tools forwarding ──────────────────────────────────────────────────────────


def test_includes_tools_in_api_params_when_provided(generator, mock_anthropic_client):
    """tools + tool_choice must appear in the first API call; missing → Claude never searches"""
    mock_anthropic_client.messages.create.return_value = build_text_response("Answer")
    tools = [
        {"name": "search_course_content", "description": "Search", "input_schema": {}}
    ]
    generator.generate_response(query="Hi", tools=tools)

    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert (
        "tools" in call_kwargs
    ), "tools not forwarded to API — Claude will never search"
    assert call_kwargs.get("tool_choice") == {
        "type": "auto"
    }, "tool_choice missing or wrong"


def test_no_tool_choice_when_tools_not_provided(generator, mock_anthropic_client):
    mock_anthropic_client.messages.create.return_value = build_text_response("Answer")
    generator.generate_response(query="Hi")

    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert "tool_choice" not in call_kwargs


# ── conversation history ──────────────────────────────────────────────────────


def test_includes_conversation_history_in_system_prompt(
    generator, mock_anthropic_client
):
    mock_anthropic_client.messages.create.return_value = build_text_response("Answer")
    generator.generate_response(query="Hi", conversation_history="User: hello\nAI: hi")

    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert "Previous conversation:" in call_kwargs["system"]


# ── error handling ────────────────────────────────────────────────────────────


def test_api_exception_propagates(generator, mock_anthropic_client):
    mock_anthropic_client.messages.create.side_effect = Exception("API error")
    with pytest.raises(Exception, match="API error"):
        generator.generate_response(query="Hi")


# ── tool-use flow ─────────────────────────────────────────────────────────────


def test_tool_use_response_triggers_tool_execution(generator, mock_anthropic_client):
    """stop_reason='tool_use' must cause execute_tool() to be called"""
    tool_response = build_tool_use_response(
        tool_name="search_course_content",
        tool_id="toolu_01",
        tool_input={"query": "Python basics"},
    )
    final_response = build_text_response("Here is the answer")
    mock_anthropic_client.messages.create.side_effect = [tool_response, final_response]

    tool_manager = MagicMock()
    tool_manager.execute_tool.return_value = "Search results here"

    generator.generate_response(
        query="What is Python?", tools=[], tool_manager=tool_manager
    )
    tool_manager.execute_tool.assert_called_once_with(
        "search_course_content", query="Python basics"
    )


def test_tool_result_sent_as_user_message_in_follow_up(
    generator, mock_anthropic_client
):
    """Tool result must be a user message containing type='tool_result' with matching tool_use_id"""
    tool_response = build_tool_use_response(
        tool_name="search_course_content",
        tool_id="toolu_01",
        tool_input={"query": "Python basics"},
    )
    final_response = build_text_response("Here is the answer")
    mock_anthropic_client.messages.create.side_effect = [tool_response, final_response]

    tool_manager = MagicMock()
    tool_manager.execute_tool.return_value = "Search results here"

    generator.generate_response(
        query="What is Python?", tools=[], tool_manager=tool_manager
    )

    second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
    messages = second_call_kwargs["messages"]
    user_msg = messages[-1]
    assert user_msg["role"] == "user", f"Expected user role, got {user_msg['role']}"
    content = user_msg["content"]
    assert isinstance(content, list), "tool_result content must be a list"
    assert content[0]["type"] == "tool_result"
    assert content[0]["tool_use_id"] == "toolu_01"


def test_follow_up_call_does_not_include_tools(generator, mock_anthropic_client):
    """The follow-up (2nd) API call must not include tools to avoid an infinite tool loop"""
    tool_response = build_tool_use_response(
        tool_name="search_course_content",
        tool_id="toolu_01",
        tool_input={"query": "Python basics"},
    )
    final_response = build_text_response("Here is the answer")
    mock_anthropic_client.messages.create.side_effect = [tool_response, final_response]

    tool_manager = MagicMock()
    tool_manager.execute_tool.return_value = "Results"

    generator.generate_response(
        query="What is Python?",
        tools=[{"name": "search_course_content"}],
        tool_manager=tool_manager,
    )

    second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
    assert "tools" not in second_call_kwargs


def test_follow_up_call_returns_text_content(generator, mock_anthropic_client):
    tool_response = build_tool_use_response(
        tool_name="search_course_content",
        tool_id="toolu_01",
        tool_input={"query": "Python basics"},
    )
    final_response = build_text_response("Final answer here")
    mock_anthropic_client.messages.create.side_effect = [tool_response, final_response]

    tool_manager = MagicMock()
    tool_manager.execute_tool.return_value = "Results"

    result = generator.generate_response(
        query="What is Python?", tools=[], tool_manager=tool_manager
    )
    assert result == "Final answer here"


def test_makes_exactly_two_api_calls_for_tool_use(generator, mock_anthropic_client):
    tool_response = build_tool_use_response(
        tool_name="search_course_content",
        tool_id="toolu_01",
        tool_input={"query": "Python basics"},
    )
    final_response = build_text_response("Answer")
    mock_anthropic_client.messages.create.side_effect = [tool_response, final_response]

    tool_manager = MagicMock()
    tool_manager.execute_tool.return_value = "Results"

    generator.generate_response(
        query="What is Python?", tools=[], tool_manager=tool_manager
    )
    assert mock_anthropic_client.messages.create.call_count == 2
