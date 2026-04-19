"""
Tests for VectorStore — pure logic and None-metadata safety.

ChromaDB collection interactions are mocked so no real DB is needed.
"""
import pytest
from unittest.mock import MagicMock, patch
from models import Course, Lesson, CourseChunk
from vector_store import VectorStore, SearchResults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_store(max_results=5):
    """Return a VectorStore with all ChromaDB I/O mocked out."""
    with patch("vector_store.chromadb.PersistentClient") as mock_client_cls, \
         patch("vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"), \
         patch("vector_store.SentenceTransformer"):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_or_create_collection.return_value = MagicMock()
        store = VectorStore(
            chroma_path="/tmp/test_chroma",
            embedding_model="all-MiniLM-L6-v2",
            max_results=max_results,
        )
    return store


# ---------------------------------------------------------------------------
# _build_filter pure-logic tests
# ---------------------------------------------------------------------------

class TestBuildFilter:
    def setup_method(self):
        self.store = make_store()

    def test_no_filter_when_no_params(self):
        assert self.store._build_filter(None, None) is None

    def test_filter_with_course_title_only(self):
        result = self.store._build_filter("Python Basics", None)
        assert result == {"course_title": "Python Basics"}

    def test_filter_with_lesson_number_only(self):
        result = self.store._build_filter(None, 3)
        assert result == {"lesson_number": 3}

    def test_filter_with_both(self):
        result = self.store._build_filter("Python Basics", 2)
        assert result == {"$and": [
            {"course_title": "Python Basics"},
            {"lesson_number": 2},
        ]}


# ---------------------------------------------------------------------------
# add_course_metadata None-safety tests
# ---------------------------------------------------------------------------

class TestAddCourseMetadataNoneSafety:
    """
    Verify that None optional fields are sanitised before reaching ChromaDB.
    After the fix, None values must be replaced with empty strings so the
    strict ChromaDB 1.0.x validator never sees them.
    """

    def _make_strict_collection_mock(self):
        """
        Return a mock whose .add() side-effect mimics ChromaDB 1.0.x
        behaviour: raises ValueError when any metadata value is None.
        """
        def _strict_add(documents, metadatas, ids):
            for meta in metadatas:
                for key, value in meta.items():
                    if value is None:
                        raise ValueError(
                            f"Expected metadata value to be a str, int, float or bool, got None"
                        )

        collection = MagicMock()
        collection.add.side_effect = _strict_add
        return collection

    def test_add_course_metadata_with_none_instructor(self):
        """None instructor must be sanitised to '' — should NOT raise after fix."""
        store = make_store()
        store.course_catalog = self._make_strict_collection_mock()

        course = Course(
            title="Test Course",
            course_link="https://example.com",
            instructor=None,
            lessons=[],
        )
        store.add_course_metadata(course)  # must not raise

    def test_add_course_metadata_with_none_course_link(self):
        """None course_link must be sanitised to '' — should NOT raise after fix."""
        store = make_store()
        store.course_catalog = self._make_strict_collection_mock()

        course = Course(
            title="Test Course 2",
            course_link=None,
            instructor="Someone",
            lessons=[],
        )
        store.add_course_metadata(course)  # must not raise

    def test_add_course_metadata_with_all_fields(self, sample_course):
        """Fully-populated course should not raise."""
        store = make_store()
        store.course_catalog = self._make_strict_collection_mock()

        store.add_course_metadata(sample_course)  # should not raise


# ---------------------------------------------------------------------------
# add_course_content None-safety tests
# ---------------------------------------------------------------------------

class TestAddCourseContentNoneSafety:
    def _make_strict_collection_mock(self):
        def _strict_add(documents, metadatas, ids):
            for meta in metadatas:
                for key, value in meta.items():
                    if value is None:
                        raise ValueError(
                            f"Expected metadata value to be a str, int, float or bool, got None"
                        )

        collection = MagicMock()
        collection.add.side_effect = _strict_add
        return collection

    def test_add_course_content_with_none_lesson_number(self):
        """None lesson_number must be sanitised to -1 — should NOT raise after fix."""
        store = make_store()
        store.course_content = self._make_strict_collection_mock()

        chunks = [
            CourseChunk(
                content="some text",
                course_title="Python Basics",
                lesson_number=None,
                chunk_index=0,
            )
        ]
        store.add_course_content(chunks)  # must not raise

    def test_add_course_content_with_lesson_number(self):
        """Integer lesson_number should not raise."""
        store = make_store()
        store.course_content = self._make_strict_collection_mock()

        chunks = [
            CourseChunk(
                content="some text",
                course_title="Python Basics",
                lesson_number=1,
                chunk_index=0,
            )
        ]
        store.add_course_content(chunks)  # should not raise


# ---------------------------------------------------------------------------
# search tests
# ---------------------------------------------------------------------------

class TestSearch:
    def _make_store_with_content_mock(self, query_return, doc_count=10):
        store = make_store()
        store.course_content = MagicMock()
        store.course_content.count.return_value = doc_count
        store.course_content.query.return_value = query_return
        return store

    def _chroma_result(self, docs, metas=None, dists=None):
        if metas is None:
            metas = [{"course_title": "Python Basics", "lesson_number": 1}] * len(docs)
        if dists is None:
            dists = [0.1] * len(docs)
        return {
            "documents": [docs],
            "metadatas": [metas],
            "distances": [dists],
        }

    def test_search_returns_results(self):
        chroma_result = self._chroma_result(["doc 1", "doc 2"])
        store = self._make_store_with_content_mock(chroma_result)

        results = store.search("python variables")

        assert not results.is_empty()
        assert len(results.documents) == 2

    def test_search_with_fewer_results_than_n_results(self):
        """When ChromaDB returns fewer docs than requested, should not raise."""
        chroma_result = self._chroma_result(["only one doc"])
        store = self._make_store_with_content_mock(chroma_result)

        results = store.search("python variables")

        assert not results.is_empty()
        assert len(results.documents) == 1

    def test_search_with_no_results_returns_empty(self):
        chroma_result = self._chroma_result([])
        store = self._make_store_with_content_mock(chroma_result)

        results = store.search("obscure query")

        assert results.is_empty()

    def test_search_passes_filter_to_chroma(self):
        """Filter built from course_title should be forwarded to ChromaDB."""
        chroma_result = self._chroma_result(["doc"])
        store = self._make_store_with_content_mock(chroma_result)
        # Bypass course resolution by making _resolve_course_name return a title
        store._resolve_course_name = MagicMock(return_value="Python Basics")

        store.search("variables", course_name="Python")

        call_kwargs = store.course_content.query.call_args.kwargs
        assert call_kwargs["where"] == {"course_title": "Python Basics"}

    def test_search_exception_returns_error_result(self):
        """If ChromaDB raises, search() should return SearchResults with error set."""
        store = make_store()
        store.course_content = MagicMock()
        store.course_content.count.return_value = 10
        store.course_content.query.side_effect = RuntimeError("chroma exploded")

        results = store.search("anything")

        assert results.error is not None
        assert "chroma exploded" in results.error
        assert results.is_empty()
