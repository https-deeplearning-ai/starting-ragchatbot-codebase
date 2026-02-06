"""End-to-end tests against the real system (not mocked)"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import config
from vector_store import VectorStore
from search_tools import CourseSearchTool, ToolManager


class TestRealVectorStore:
    """Tests against the real ChromaDB database"""

    @pytest.fixture
    def real_vector_store(self):
        """Create a real VectorStore with the actual ChromaDB"""
        # Use the configured path
        chroma_path = config.CHROMA_PATH
        if not os.path.isabs(chroma_path):
            backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            chroma_path = os.path.normpath(os.path.join(backend_dir, chroma_path))

        return VectorStore(
            chroma_path=chroma_path,
            embedding_model=config.EMBEDDING_MODEL,
            max_results=config.MAX_RESULTS
        )

    def test_database_has_courses(self, real_vector_store):
        """Test that the database has courses ingested"""
        course_count = real_vector_store.get_course_count()

        if course_count == 0:
            pytest.fail(
                "DIAGNOSTIC FAILURE: ChromaDB has NO courses ingested. "
                "This is likely the root cause of 'not detail content' errors. "
                "The documents need to be processed and ingested into the database. "
                "Try: 1) Delete backend/chroma_db/ and restart the server, or "
                "2) Ensure docs/ folder contains course files."
            )

        assert course_count > 0, f"Expected courses in database, found {course_count}"

    def test_database_has_course_content(self, real_vector_store):
        """Test that the database has course content chunks"""
        try:
            # Try to get all documents from course_content collection
            results = real_vector_store.course_content.get()
            doc_count = len(results.get('ids', []))

            if doc_count == 0:
                pytest.fail(
                    "DIAGNOSTIC FAILURE: ChromaDB has NO content chunks. "
                    "Courses may be registered but content was not ingested. "
                    "Check document_processor.py for chunking issues."
                )

            assert doc_count > 0, f"Expected content in database, found {doc_count}"

        except Exception as e:
            pytest.fail(f"Error accessing course_content collection: {e}")

    def test_search_returns_results(self, real_vector_store):
        """Test that a basic search returns results"""
        results = real_vector_store.search("computer use")

        if results.is_empty():
            # Get more diagnostic info
            course_count = real_vector_store.get_course_count()
            courses = real_vector_store.get_existing_course_titles()

            pytest.fail(
                f"DIAGNOSTIC FAILURE: Search returned no results. "
                f"Database has {course_count} courses: {courses[:5]}... "
                f"Error: {results.error if results.error else 'No error'}"
            )

        assert not results.is_empty(), "Search should return results"
        assert len(results.documents) > 0, "Should have documents in results"

    def test_search_returns_actual_content(self, real_vector_store):
        """Test that search results contain actual content (not empty strings)"""
        results = real_vector_store.search("machine learning")

        if results.is_empty():
            pytest.skip("No results - may need documents ingested first")

        for i, doc in enumerate(results.documents):
            assert doc, f"Document {i} is empty"
            assert len(doc) > 10, f"Document {i} seems too short: '{doc}'"

    def test_course_name_resolution_works(self, real_vector_store):
        """Test that course name resolution works with real data"""
        # Get available courses
        courses = real_vector_store.get_existing_course_titles()

        if not courses:
            pytest.skip("No courses in database")

        # Try to resolve a partial course name
        first_course = courses[0]
        # Use just part of the name
        partial_name = first_course.split()[0] if ' ' in first_course else first_course[:10]

        resolved = real_vector_store._resolve_course_name(partial_name)

        if resolved is None:
            pytest.fail(
                f"DIAGNOSTIC FAILURE: Course name resolution failed. "
                f"Could not resolve '{partial_name}' from courses: {courses}"
            )


class TestRealSearchPipeline:
    """Test the full search pipeline with real data"""

    @pytest.fixture
    def real_search_tool(self):
        """Create a real CourseSearchTool with actual database"""
        chroma_path = config.CHROMA_PATH
        if not os.path.isabs(chroma_path):
            backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            chroma_path = os.path.normpath(os.path.join(backend_dir, chroma_path))

        store = VectorStore(
            chroma_path=chroma_path,
            embedding_model=config.EMBEDDING_MODEL,
            max_results=config.MAX_RESULTS
        )
        return CourseSearchTool(store)

    def test_tool_execute_returns_content(self, real_search_tool):
        """Test that tool execution returns actual content"""
        result = real_search_tool.execute(query="lesson")

        if "No relevant content found" in result:
            pytest.fail(
                "DIAGNOSTIC FAILURE: CourseSearchTool returns 'No relevant content'. "
                "Check if database has content ingested."
            )

        if result.startswith("No course found"):
            pytest.fail(
                f"DIAGNOSTIC FAILURE: Course resolution failed. Result: {result}"
            )

        # Result should contain formatted content with headers
        assert "[" in result or len(result) > 50, \
            f"Result doesn't look like formatted content: {result[:100]}"

    def test_tool_execute_with_course_filter(self, real_search_tool):
        """Test tool execution with course name filter"""
        # First get available courses
        courses = real_search_tool.store.get_existing_course_titles()

        if not courses:
            pytest.skip("No courses in database")

        # Search within first course
        first_course = courses[0]
        result = real_search_tool.execute(
            query="introduction",
            course_name=first_course
        )

        # Should not return "No course found" since we used exact title
        assert "No course found" not in result, \
            f"Failed to find course '{first_course}' which should exist"

    def test_tool_captures_sources(self, real_search_tool):
        """Test that tool captures sources for citation"""
        result = real_search_tool.execute(query="course")

        if "No relevant content found" in result:
            pytest.skip("No content found - may need ingestion")

        assert len(real_search_tool.last_sources) > 0, \
            "Tool should capture sources for citation"

        for source in real_search_tool.last_sources:
            assert "text" in source, "Source should have 'text' field"


class TestDatabaseDiagnostics:
    """Diagnostic tests to identify database issues"""

    def test_list_all_courses(self):
        """List all courses in database for diagnostic purposes"""
        chroma_path = config.CHROMA_PATH
        if not os.path.isabs(chroma_path):
            backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            chroma_path = os.path.normpath(os.path.join(backend_dir, chroma_path))

        store = VectorStore(
            chroma_path=chroma_path,
            embedding_model=config.EMBEDDING_MODEL,
            max_results=config.MAX_RESULTS
        )

        courses = store.get_existing_course_titles()
        metadata = store.get_all_courses_metadata()

        print(f"\n{'='*60}")
        print("DATABASE DIAGNOSTIC REPORT")
        print(f"{'='*60}")
        print(f"Total courses: {len(courses)}")

        if courses:
            print("\nCourses in database:")
            for i, course in enumerate(courses, 1):
                print(f"  {i}. {course}")

            print("\nCourse metadata:")
            for meta in metadata:
                print(f"  - {meta.get('title', 'Unknown')}")
                print(f"    Instructor: {meta.get('instructor', 'N/A')}")
                print(f"    Lessons: {meta.get('lesson_count', 0)}")
        else:
            print("\n*** NO COURSES FOUND IN DATABASE ***")
            print("This is likely the root cause of the issue.")
            print("\nTo fix:")
            print("1. Ensure docs/ folder contains course files")
            print("2. Delete backend/chroma_db/ directory")
            print("3. Restart the server to re-ingest documents")

        print(f"{'='*60}")

        # Don't fail - this is diagnostic
        assert True

    def test_sample_content_chunks(self):
        """Show sample content chunks for diagnostic purposes"""
        chroma_path = config.CHROMA_PATH
        if not os.path.isabs(chroma_path):
            backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            chroma_path = os.path.normpath(os.path.join(backend_dir, chroma_path))

        store = VectorStore(
            chroma_path=chroma_path,
            embedding_model=config.EMBEDDING_MODEL,
            max_results=5
        )

        try:
            results = store.course_content.get(limit=5)
            docs = results.get('documents', [])
            metadatas = results.get('metadatas', [])

            print(f"\n{'='*60}")
            print("SAMPLE CONTENT CHUNKS")
            print(f"{'='*60}")

            if docs:
                for i, (doc, meta) in enumerate(zip(docs, metadatas)):
                    print(f"\nChunk {i+1}:")
                    print(f"  Course: {meta.get('course_title', 'Unknown')}")
                    print(f"  Lesson: {meta.get('lesson_number', 'N/A')}")
                    print(f"  Content preview: {doc[:100]}...")
            else:
                print("\n*** NO CONTENT CHUNKS FOUND ***")

            print(f"{'='*60}")

        except Exception as e:
            print(f"Error getting content chunks: {e}")

        assert True
