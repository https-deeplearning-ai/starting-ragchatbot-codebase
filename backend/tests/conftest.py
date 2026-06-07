import sys
import os

# Add the backend directory to the Python path so test files can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile

from models import Course, Lesson, CourseChunk
from vector_store import VectorStore


@pytest.fixture
def tmp_chroma_path():
    """Create a temporary directory for ChromaDB during tests.

    ignore_cleanup_errors=True avoids PermissionError on Windows where
    ChromaDB holds file handles open until the process exits.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield tmpdir


@pytest.fixture
def empty_vector_store(tmp_chroma_path):
    """A VectorStore backed by a fresh empty ChromaDB."""
    return VectorStore(
        chroma_path=tmp_chroma_path,
        embedding_model="all-MiniLM-L6-v2",
        max_results=5,
    )


@pytest.fixture
def sample_course():
    return Course(
        title="Introduction to RAG",
        course_link="https://example.com/rag",
        instructor="Test Instructor",
        lessons=[
            Lesson(lesson_number=1, title="What is RAG"),
            Lesson(lesson_number=2, title="Vector Databases"),
        ],
    )


@pytest.fixture
def sample_chunks():
    return [
        CourseChunk(
            content="Lesson 1 content: RAG stands for Retrieval-Augmented Generation. "
                    "It combines a retrieval system with a generative language model.",
            course_title="Introduction to RAG",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="Vector databases store embeddings and enable fast similarity search "
                    "over large document collections.",
            course_title="Introduction to RAG",
            lesson_number=2,
            chunk_index=1,
        ),
        CourseChunk(
            content="ChromaDB is an open-source vector database well-suited for local development.",
            course_title="Introduction to RAG",
            lesson_number=2,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def populated_vector_store(empty_vector_store, sample_course, sample_chunks):
    """A VectorStore with one test course and three content chunks loaded."""
    empty_vector_store.add_course_metadata(sample_course)
    empty_vector_store.add_course_content(sample_chunks)
    return empty_vector_store
