import sys
from pathlib import Path

import pytest

# Make backend/ importable (ai_generator, config)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_generator import AIGenerator  # noqa: E402
from config import config  # noqa: E402  (also loads .env)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "functional: hits the real Anthropic API (needs key + network)"
    )


@pytest.fixture
def api_key():
    signed_in = (Path.home() / ".config/anthropic/credentials").exists()
    if not config.ANTHROPIC_API_KEY and not signed_in:
        pytest.skip("no ANTHROPIC_API_KEY and not signed in (`ant auth login`)")
    return config.ANTHROPIC_API_KEY


@pytest.fixture
def generator(api_key):
    return AIGenerator(api_key, config.ANTHROPIC_MODEL)


class StubToolManager:
    """Records tool calls and returns a canned result; no ChromaDB involved."""

    def __init__(self, result="sunny 21C"):
        self.result = result
        self.calls = []

    def execute_tool(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return self.result


@pytest.fixture
def tool_manager():
    return StubToolManager()


WEATHER_TOOL = {
    "name": "get_weather",
    "description": "Get the current weather for a city.",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}


@pytest.fixture
def tools():
    return [WEATHER_TOOL]


@pytest.fixture(scope="session")
def rag(tmp_path_factory):
    """RAGSystem over a throwaway ChromaDB built from ../docs (local embeddings, no API)."""
    import dataclasses

    from rag_system import RAGSystem

    cfg = dataclasses.replace(
        config, CHROMA_PATH=str(tmp_path_factory.mktemp("chroma"))
    )
    system = RAGSystem(cfg)
    docs = Path(__file__).resolve().parent.parent.parent / "docs"
    courses, _ = system.add_course_folder(str(docs))
    assert courses > 0, "no course docs ingested"
    return system
