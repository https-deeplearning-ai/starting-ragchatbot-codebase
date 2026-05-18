"""
Integration tests for VectorStore using a real (temporary) ChromaDB instance.

Unlike the other test files that mock VectorStore entirely, these tests exercise
the actual ChromaDB layer. This is where bugs like MAX_RESULTS = 0 become visible:
a misconfigured value won't raise an error — it will silently return empty results,
which only an end-to-end test can catch.

NOTE: First run downloads the sentence-transformer model if not already cached.
Subsequent runs are fast.
"""

import pytest
from vector_store import VectorStore
from models import Course, Lesson, CourseChunk
from config import Config

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    """Real VectorStore backed by a temporary ChromaDB directory."""
    return VectorStore(
        chroma_path=str(tmp_path / "test_chroma"),
        embedding_model="all-MiniLM-L6-v2",
        max_results=Config.MAX_RESULTS,
    )


@pytest.fixture
def sample_course():
    """A minimal course with two lessons for use in multiple tests."""
    return Course(
        title="Introduction to RAG",
        course_link="https://example.com/rag",
        instructor="Test Instructor",
        lessons=[
            Lesson(
                lesson_number=0,
                title="Overview",
                lesson_link="https://example.com/rag/0",
            ),
            Lesson(
                lesson_number=1,
                title="Embeddings and Vector Search",
                lesson_link="https://example.com/rag/1",
            ),
        ],
    )


@pytest.fixture
def sample_chunks(sample_course):
    """Content chunks for sample_course, more than MAX_RESULTS to test the cap."""
    return [
        CourseChunk(
            content=f"RAG lesson content chunk number {i}. Retrieval augmented generation.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=i,
        )
        for i in range(Config.MAX_RESULTS + 3)
    ]


# ---------------------------------------------------------------------------
# 1. Config validation — catches silent misconfigurations
# ---------------------------------------------------------------------------


class TestConfigValidation:
    def test_max_results_is_positive(self):
        """MAX_RESULTS = 0 causes ChromaDB to return nothing; must be > 0."""
        assert Config.MAX_RESULTS > 0

    def test_chunk_size_is_positive(self):
        assert Config.CHUNK_SIZE > 0

    def test_chunk_overlap_less_than_chunk_size(self):
        """Overlap >= chunk size would cause infinite chunking loops."""
        assert Config.CHUNK_OVERLAP < Config.CHUNK_SIZE

    def test_embedding_model_is_set(self):
        assert Config.EMBEDDING_MODEL != ""

    def test_anthropic_model_is_set(self):
        assert Config.ANTHROPIC_MODEL != ""


# ---------------------------------------------------------------------------
# 2. Initialization — collections are created on startup
# ---------------------------------------------------------------------------


class TestInitialization:
    def test_course_catalog_collection_created(self, store):
        assert store.course_catalog is not None

    def test_course_content_collection_created(self, store):
        assert store.course_content is not None

    def test_new_store_has_zero_courses(self, store):
        assert store.get_course_count() == 0

    def test_new_store_has_empty_titles_list(self, store):
        assert store.get_existing_course_titles() == []


# ---------------------------------------------------------------------------
# 3. Data ingestion and retrieval
# ---------------------------------------------------------------------------


class TestDataIngestion:
    def test_add_course_increments_count(self, store, sample_course):
        store.add_course_metadata(sample_course)
        assert store.get_course_count() == 1

    def test_added_course_appears_in_titles(self, store, sample_course):
        store.add_course_metadata(sample_course)
        assert sample_course.title in store.get_existing_course_titles()

    def test_course_link_retrievable_by_exact_title(self, store, sample_course):
        store.add_course_metadata(sample_course)
        assert store.get_course_link(sample_course.title) == sample_course.course_link

    def test_lesson_link_retrievable(self, store, sample_course):
        store.add_course_metadata(sample_course)
        url = store.get_lesson_link(sample_course.title, lesson_number=1)
        assert url == "https://example.com/rag/1"

    def test_unknown_course_link_returns_none(self, store):
        result = store.get_course_link("Nonexistent Course Title")
        assert result is None

    def test_multiple_courses_counted_correctly(self, store, sample_course):
        course2 = Course(
            title="Advanced Prompt Engineering",
            course_link="https://example.com/pe",
            instructor="Another Instructor",
            lessons=[
                Lesson(
                    lesson_number=0,
                    title="Intro",
                    lesson_link="https://example.com/pe/0",
                )
            ],
        )
        store.add_course_metadata(sample_course)
        store.add_course_metadata(course2)
        assert store.get_course_count() == 2


# ---------------------------------------------------------------------------
# 4. Search — the MAX_RESULTS = 0 guard
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_returns_results_for_relevant_query(
        self, store, sample_course, sample_chunks
    ):
        """
        The critical integration test. With real content indexed, a relevant
        query must return results. If MAX_RESULTS = 0, this fails even though
        no error is raised — ChromaDB just returns nothing.
        """
        store.add_course_content(sample_chunks)
        results = store.search(query="RAG retrieval augmented generation")
        assert not results.is_empty()

    def test_search_result_count_respects_max_results(
        self, store, sample_course, sample_chunks
    ):
        """Number of results returned must never exceed MAX_RESULTS."""
        store.add_course_content(sample_chunks)
        results = store.search(query="RAG retrieval")
        assert len(results.documents) <= Config.MAX_RESULTS

    def test_search_result_metadata_contains_course_title(
        self, store, sample_course, sample_chunks
    ):
        store.add_course_content(sample_chunks)
        results = store.search(query="RAG retrieval")
        assert all(
            m.get("course_title") == sample_course.title for m in results.metadata
        )

    def test_search_with_course_filter_returns_only_matching_course(
        self, store, sample_course, sample_chunks
    ):
        other_chunks = [
            CourseChunk(
                content="Machine learning neural networks deep learning.",
                course_title="Deep Learning Fundamentals",
                lesson_number=1,
                chunk_index=0,
            )
        ]
        store.add_course_content(sample_chunks)
        store.add_course_content(other_chunks)

        results = store.search(
            query="neural networks", course_name="Introduction to RAG"
        )
        # All returned results must be from the filtered course
        assert all(m["course_title"] == sample_course.title for m in results.metadata)

    def test_search_returns_no_error_on_success(self, store, sample_chunks):
        store.add_course_content(sample_chunks)
        results = store.search(query="RAG retrieval")
        assert results.error is None

    def test_search_empty_catalog_returns_empty_results(self, store):
        """With no content indexed, search should return empty (not crash)."""
        results = store.search(query="anything")
        assert results.is_empty()


# ---------------------------------------------------------------------------
# 5. Course outline (our new get_course_outline method)
# ---------------------------------------------------------------------------


class TestCourseOutline:
    def test_outline_contains_correct_title(self, store, sample_course):
        store.add_course_metadata(sample_course)
        outline = store.get_course_outline(sample_course.title)
        assert outline["title"] == sample_course.title

    def test_outline_contains_correct_course_link(self, store, sample_course):
        store.add_course_metadata(sample_course)
        outline = store.get_course_outline(sample_course.title)
        assert outline["course_link"] == sample_course.course_link

    def test_outline_contains_all_lessons(self, store, sample_course):
        store.add_course_metadata(sample_course)
        outline = store.get_course_outline(sample_course.title)
        assert len(outline["lessons"]) == len(sample_course.lessons)

    def test_outline_lessons_have_number_and_title(self, store, sample_course):
        store.add_course_metadata(sample_course)
        outline = store.get_course_outline(sample_course.title)
        for lesson in outline["lessons"]:
            assert "lesson_number" in lesson
            assert "lesson_title" in lesson

    def test_outline_fuzzy_matches_partial_name(self, store, sample_course):
        """Partial names (e.g. 'RAG') should resolve to the right course."""
        store.add_course_metadata(sample_course)
        outline = store.get_course_outline("RAG")
        assert outline is not None
        assert outline["title"] == sample_course.title

    def test_outline_returns_none_for_empty_catalog(self, store):
        """With no courses indexed, any lookup should return None."""
        result = store.get_course_outline("Introduction to RAG")
        assert result is None

    def test_get_all_courses_metadata_returns_parsed_lessons(
        self, store, sample_course
    ):
        store.add_course_metadata(sample_course)
        all_meta = store.get_all_courses_metadata()
        assert len(all_meta) == 1
        # lessons_json should be parsed into a list
        assert "lessons" in all_meta[0]
        assert isinstance(all_meta[0]["lessons"], list)
        assert "lessons_json" not in all_meta[0]
