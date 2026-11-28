"""Functional tests: real calls to the Anthropic API (no mocks)."""
import anthropic
import pytest

from ai_generator import AIGenerator

pytestmark = pytest.mark.functional


def test_plain_response(generator):
    answer = generator.generate_response("Reply with exactly the word: pong")
    assert isinstance(answer, str)
    assert "pong" in answer.lower()


def test_conversation_history_reaches_model(generator):
    answer = generator.generate_response(
        "What is my favourite colour?",
        conversation_history="User: My favourite colour is teal.\nAssistant: Noted.",
    )
    assert "teal" in answer.lower()


def test_tool_call_round_trip(generator, tools, tool_manager):
    answer = generator.generate_response(
        "What's the weather in Paris? Use the tool.",
        tools=tools,
        tool_manager=tool_manager,
    )
    assert len(tool_manager.calls) == 1
    name, kwargs = tool_manager.calls[0]
    assert name == "get_weather"
    assert "paris" in kwargs["city"].lower()
    assert answer.strip()
    assert "21" in answer or "sunny" in answer.lower()


def test_no_tool_needed(generator, tools, tool_manager):
    answer = generator.generate_response(
        "What is 2+2? Answer with just the number.",
        tools=tools,
        tool_manager=tool_manager,
    )
    assert "4" in answer
    assert tool_manager.calls == []


def test_bad_model_id_raises_not_found(api_key):
    bad = AIGenerator(api_key, "claude-does-not-exist")
    with pytest.raises(anthropic.NotFoundError):
        bad.generate_response("hi")


def test_two_sequential_tool_calls(generator):
    """Second call depends on the first result -> two rounds, 3 API calls max."""
    tools = [
        {"name": "get_lesson_title",
         "description": "Return the title of a lesson number of course X.",
         "input_schema": {"type": "object",
                          "properties": {"lesson": {"type": "integer"}},
                          "required": ["lesson"]}},
        {"name": "find_course_by_topic",
         "description": "Find a course about a topic string.",
         "input_schema": {"type": "object",
                          "properties": {"topic": {"type": "string"}},
                          "required": ["topic"]}},
    ]

    class TM:
        calls = []

        def execute_tool(self, name, **kw):
            self.calls.append((name, kw))
            return "Quantum Gardening" if name == "get_lesson_title" else "Course: Plants 101"

    tm = TM()
    tm.calls = []
    answer = generator.generate_response(
        "Find a course on the same topic as lesson 4 of course X. First get the "
        "lesson title, then search for a course on that topic.",
        tools=tools, tool_manager=tm)
    assert [c[0] for c in tm.calls] == ["get_lesson_title", "find_course_by_topic"]
    assert "quantum" in tm.calls[1][1]["topic"].lower()
    assert "Plants 101" in answer


def test_invalid_api_key_raises_authentication_error():
    bad = AIGenerator("sk-ant-invalid", "claude-sonnet-5-5")
    with pytest.raises(anthropic.AuthenticationError):
        bad.generate_response("hi")
