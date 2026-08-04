import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from search_tools import CourseSearchTool
from vector_store import SearchResults


class FakeVectorStore:
    def __init__(self, lesson_links=None):
        self.lesson_links = lesson_links or {}
        self.lesson_link_calls = []

    def get_lesson_link(self, course_title, lesson_number):
        self.lesson_link_calls.append((course_title, lesson_number))
        return self.lesson_links.get((course_title, lesson_number))


class CourseSearchToolFormattingTests(unittest.TestCase):
    def test_returns_structured_deduplicated_sources_without_changing_model_text(self):
        store = FakeVectorStore({("RAG Course", 2): "https://example.com/lesson-2"})
        tool = CourseSearchTool(store)
        results = SearchResults(
            documents=["First chunk", "Second chunk"],
            metadata=[
                {"course_title": "RAG Course", "lesson_number": 2},
                {"course_title": "RAG Course", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
        )

        formatted = tool._format_results(results)

        self.assertEqual(
            formatted,
            "[RAG Course - Lesson 2]\nFirst chunk\n\n"
            "[RAG Course - Lesson 2]\nSecond chunk",
        )
        self.assertEqual(
            tool.last_sources,
            [{"text": "RAG Course - Lesson 2", "link": "https://example.com/lesson-2"}],
        )
        self.assertEqual(store.lesson_link_calls, [("RAG Course", 2)])

    def test_missing_lesson_link_is_returned_as_null(self):
        tool = CourseSearchTool(FakeVectorStore())
        results = SearchResults(
            documents=["Chunk"],
            metadata=[{"course_title": "RAG Course", "lesson_number": 3}],
            distances=[0.1],
        )

        tool._format_results(results)

        self.assertEqual(
            tool.last_sources,
            [{"text": "RAG Course - Lesson 3", "link": None}],
        )

    def test_lesson_zero_uses_its_lesson_link(self):
        store = FakeVectorStore({("RAG Course", 0): "https://example.com/lesson-0"})
        tool = CourseSearchTool(store)
        results = SearchResults(
            documents=["Introduction"],
            metadata=[{"course_title": "RAG Course", "lesson_number": 0}],
            distances=[0.1],
        )

        tool._format_results(results)

        self.assertEqual(
            tool.last_sources,
            [{"text": "RAG Course - Lesson 0", "link": "https://example.com/lesson-0"}],
        )


if __name__ == "__main__":
    unittest.main()
