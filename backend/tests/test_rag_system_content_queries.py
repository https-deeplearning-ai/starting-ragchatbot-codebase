"""
Objective 3: integration tests against the REAL, populated backend/chroma_db
via the REAL VectorStore/ToolManager/CourseSearchTool/CourseOutlineTool.
Only AIGenerator.client.messages.create is scripted -- no live network call,
no API cost, fully deterministic, while still exercising real chunk
retrieval/formatting/source-resolution code against real data.

NOTE: query/course terms below are chosen because they are the course's own
name/topic (e.g. "Computer Use" for the "Building Towards Computer Use with
Anthropic" course) to maximize confidence of real content overlap.
"""

from unittest.mock import MagicMock

import pytest

# These load the embedding model and read the real Chroma store, and they only
# pass once `./run.sh` (or app startup) has ingested docs/ into backend/chroma_db.
# Skip them on a fast run with: uv run pytest -m "not slow"
pytestmark = pytest.mark.slow


class TestContentQueries:
    def test_content_query_returns_scripted_answer_with_real_resolvable_sources(
        self, rag_system, text_response, tool_use_response
    ):
        initial = tool_use_response(
            [
                {
                    "name": "search_course_content",
                    "input": {"query": "computer use", "course_name": "Computer Use"},
                    "id": "toolu_1",
                }
            ]
        )
        final = text_response(
            "Computer use lets Claude interact with a desktop environment."
        )
        rag_system.ai_generator.client.messages.create.side_effect = [initial, final]

        answer, sources = rag_system.query("What is computer use in that course?")

        assert answer == "Computer use lets Claude interact with a desktop environment."
        assert len(sources) > 0
        # every real source must resolve to either no link or a real http(s) link
        assert all(s.link is None or s.link.startswith("http") for s in sources)

    def test_lesson_zero_scoped_search_finds_real_content_not_the_bug_path(
        self, rag_system, text_response, tool_use_response
    ):
        initial = tool_use_response(
            [
                {
                    "name": "search_course_content",
                    "input": {
                        "query": "introduction",
                        "course_name": "Computer Use",
                        "lesson_number": 0,
                    },
                    "id": "toolu_1",
                }
            ]
        )
        final = text_response("Lesson 0 introduces the course.")
        rag_system.ai_generator.client.messages.create.side_effect = [initial, final]

        answer, sources = rag_system.query("What does lesson 0 cover?")

        assert answer == "Lesson 0 introduces the course."
        assert len(sources) > 0
        assert any(s.text.endswith("Lesson 0") for s in sources)

    def test_nonexistent_course_name_degrades_gracefully_without_crashing(
        self, rag_system
    ):
        # Direct tool-manager call: exercises the real fuzzy _resolve_course_name
        # path against the real catalog without needing a scripted Anthropic turn.
        result = rag_system.tool_manager.execute_tool(
            "search_course_content",
            query="anything",
            course_name="Totally Fake Course Title Xyz123",
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_sources_reset_between_sequential_queries(
        self, rag_system, text_response, tool_use_response
    ):
        initial = tool_use_response(
            [
                {
                    "name": "search_course_content",
                    "input": {"query": "computer use", "course_name": "Computer Use"},
                    "id": "toolu_1",
                }
            ]
        )
        final1 = text_response("first answer")
        final2 = text_response("second answer, no tool used")
        rag_system.ai_generator.client.messages.create.side_effect = [
            initial,
            final1,
            final2,
        ]

        _, sources1 = rag_system.query("What is computer use?")
        assert len(sources1) > 0

        _, sources2 = rag_system.query("Thanks, that's all")
        assert sources2 == []


class TestSessionHistory:
    def test_two_queries_same_session_record_both_exchanges_and_pass_history(
        self, rag_system, text_response
    ):
        rag_system.ai_generator.client.messages.create.side_effect = [
            text_response("answer one"),
            text_response("answer two"),
        ]

        rag_system.query("first question", session_id="sess-1")
        rag_system.query("second question", session_id="sess-1")

        history = rag_system.session_manager.get_conversation_history("sess-1")
        assert "first question" in history
        assert "answer one" in history
        assert "second question" in history

        second_call_kwargs = (
            rag_system.ai_generator.client.messages.create.call_args_list[1].kwargs
        )
        assert "Previous conversation:" in second_call_kwargs["system"]
        assert "first question" in second_call_kwargs["system"]


class TestGeneralKnowledge:
    def test_general_knowledge_question_never_touches_the_vector_store(
        self, rag_system, text_response, monkeypatch
    ):
        rag_system.ai_generator.client.messages.create.return_value = text_response(
            "Paris is the capital of France.", stop_reason="end_turn"
        )
        search_spy = MagicMock(wraps=rag_system.vector_store.search)
        monkeypatch.setattr(rag_system.vector_store, "search", search_spy)

        answer, sources = rag_system.query("What is the capital of France?")

        assert answer == "Paris is the capital of France."
        assert sources == []
        search_spy.assert_not_called()
