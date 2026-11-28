"""Offline tests for sequential tool calling; assert external behavior only."""
import copy
from types import SimpleNamespace
from unittest.mock import patch

from ai_generator import AIGenerator

TOOLS = [{"name": "t", "description": "d", "input_schema": {"type": "object"}}]


def text(t):
    return SimpleNamespace(stop_reason="end_turn",
                           content=[SimpleNamespace(type="text", text=t)])


def tool_use(*calls):
    """calls: (id, name, input) tuples."""
    return SimpleNamespace(stop_reason="tool_use", content=[
        SimpleNamespace(type="tool_use", id=i, name=n, input=inp) for i, n, inp in calls])


class FakeTools:
    def __init__(self, results=None, raises=()):
        self.results, self.raises, self.calls = results or {}, set(raises), []

    def execute_tool(self, name, **kw):
        self.calls.append((name, kw))
        if name in self.raises:
            raise RuntimeError("boom")
        return self.results.get(name, f"{name}-result")


def run(responses, tm=None, tools=TOOLS, history=None):
    sent = []

    def create(**kw):
        sent.append(copy.deepcopy(kw))
        return responses[len(sent) - 1]

    with patch("ai_generator.anthropic.Anthropic") as A:
        A.return_value.messages.create.side_effect = create
        gen = AIGenerator("k", "m")
        out = gen.generate_response("q", history, tools, tm)
    return out, sent


def test_no_tool_needed():
    out, sent = run([text("hi")], FakeTools())
    assert out == "hi" and len(sent) == 1


def test_single_tool_round():
    tm = FakeTools()
    out, sent = run([tool_use(("a", "t", {"x": 1})), text("done")], tm)
    assert out == "done" and len(sent) == 2
    assert tm.calls == [("t", {"x": 1})]
    result = sent[1]["messages"][-1]["content"][0]
    assert result["tool_use_id"] == "a" and result["content"] == "t-result"


def test_two_sequential_rounds_pass_context():
    tm = FakeTools({"get_course_outline": "Lesson 4: Embeddings"})
    out, sent = run([
        tool_use(("a", "get_course_outline", {"course": "X"})),
        tool_use(("b", "search_course_content", {"query": "Embeddings"})),
        text("answer"),
    ], tm)
    assert out == "answer" and len(sent) == 3
    assert [c[0] for c in tm.calls] == ["get_course_outline", "search_course_content"]
    assert tm.calls[1][1] == {"query": "Embeddings"}
    ids = [m["content"][0]["tool_use_id"] for m in sent[2]["messages"]
           if m["role"] == "user" and isinstance(m["content"], list)]
    assert ids == ["a", "b"]
    assert sent[1]["tool_choice"] == {"type": "auto"}


def test_round_cap_forces_final_answer():
    tm = FakeTools()
    out, sent = run([tool_use(("a", "t", {})), tool_use(("b", "t", {})),
                     text("final")], tm)
    assert out == "final" and len(sent) == 3 and len(tm.calls) == 2
    assert sent[2]["tool_choice"] == {"type": "none"}
    assert sent[2]["tools"] == TOOLS


def test_tool_error_stops_and_reports():
    tm = FakeTools(raises={"t"})
    out, sent = run([tool_use(("a", "t", {})), text("sorry")], tm)
    assert out == "sorry" and len(sent) == 2 and len(tm.calls) == 1
    assert sent[1]["messages"][-1]["content"][0]["is_error"] is True
    assert sent[1]["tool_choice"] == {"type": "none"}


def test_tool_error_in_round_two():
    tm = FakeTools(raises={"bad"})
    out, sent = run([tool_use(("a", "t", {})), tool_use(("b", "bad", {})),
                     text("sorry")], tm)
    assert out == "sorry" and len(sent) == 3
    assert sent[2]["messages"][-1]["content"][0]["is_error"] is True


def test_parallel_tool_use_all_answered():
    tm = FakeTools()
    out, sent = run([tool_use(("a", "t", {}), ("b", "u", {})), text("ok")], tm)
    assert len(tm.calls) == 2
    ids = [r["tool_use_id"] for r in sent[1]["messages"][-1]["content"]]
    assert ids == ["a", "b"]


def test_history_in_system_and_no_tools_param():
    out, sent = run([text("x")], None, tools=None, history="earlier")
    assert "earlier" in sent[0]["system"]
    assert "tools" not in sent[0]


def test_tool_use_without_manager_returns_text():
    resp = SimpleNamespace(stop_reason="tool_use", content=[
        SimpleNamespace(type="text", text="partial"),
        SimpleNamespace(type="tool_use", id="a", name="t", input={})])
    out, sent = run([resp], None)
    assert out == "partial" and len(sent) == 1
