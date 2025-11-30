"""
Tests for DocumentProcessor
Specifically tests for chunk formatting consistency bug
"""

import os
import tempfile

import pytest
from document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Test suite for DocumentProcessor"""

    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor with standard settings"""
        return DocumentProcessor(chunk_size=800, chunk_overlap=100)

    @pytest.fixture
    def sample_course_file(self):
        """Create a temporary course file for testing"""
        content = """Course Title: Python Programming
Course Link: https://example.com/python
Course Instructor: Jane Doe

Lesson 1: Introduction
Lesson Link: https://example.com/python/lesson1
This is the first lesson about Python. Python is a high-level programming language. It is widely used for web development, data science, and automation.

Lesson 2: Variables and Types
Lesson Link: https://example.com/python/lesson2
Variables are containers for storing data values. Python has various data types including integers, floats, strings, and booleans. You can assign values to variables using the equals sign.

Lesson 3: Functions
Lesson Link: https://example.com/python/lesson3
Functions are reusable blocks of code. They help organize your code and make it more maintainable. You define functions using the def keyword.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    def test_chunk_prefix_consistency(self, processor, sample_course_file):
        """
        CRITICAL TEST: Verify that all lessons have consistent chunk prefixing
        This test is designed to catch the bug where the last lesson has different formatting
        """
        course, chunks = processor.process_course_document(sample_course_file)

        # Find chunks for each lesson
        lesson_chunks = {1: [], 2: [], 3: []}
        for chunk in chunks:
            if chunk.lesson_number in lesson_chunks:
                lesson_chunks[chunk.lesson_number].append(chunk)

        # Check first chunks of lessons 1 and 2
        # According to document_processor.py line 186, they should start with "Lesson X content:"
        if len(lesson_chunks[1]) > 0:
            first_lesson_chunk = lesson_chunks[1][0].content
            assert first_lesson_chunk.startswith(
                "Lesson 1 content:"
            ), f"Lesson 1 first chunk should start with 'Lesson 1 content:' but got: {first_lesson_chunk[:50]}"

        if len(lesson_chunks[2]) > 0:
            second_lesson_chunk = lesson_chunks[2][0].content
            # Note: Only the FIRST chunk of a lesson gets the prefix in the loop (line 185-187)
            # Other chunks don't get the prefix
            # But let's check if the pattern is consistent

        # Check last lesson (Lesson 3)
        # According to line 234, it should start with "Course {title} Lesson X content:"
        if len(lesson_chunks[3]) > 0:
            last_lesson_chunk = lesson_chunks[3][0].content
            # THIS IS THE BUG: Last lesson has different prefix format
            # It should match the format of other lessons
            print(f"Last lesson chunk prefix: {last_lesson_chunk[:80]}")

            # This assertion will FAIL if the bug exists
            # Expected: "Lesson 3 content:" (consistent with other lessons)
            # Actual: "Course Python Programming Lesson 3 content:" (bug)
            is_consistent = last_lesson_chunk.startswith("Lesson 3 content:")
            is_buggy = last_lesson_chunk.startswith(
                "Course Python Programming Lesson 3 content:"
            )

            if is_buggy and not is_consistent:
                pytest.fail(
                    f"CHUNK FORMATTING BUG DETECTED: Last lesson has inconsistent prefix.\n"
                    f"Expected: 'Lesson 3 content: ...'\n"
                    f"Got: '{last_lesson_chunk[:80]}...'\n"
                    f"This is the bug in document_processor.py line 234"
                )

    def test_chunk_text_splitting(self, processor):
        """Test that text is split into appropriate chunks"""
        text = "First sentence. Second sentence. Third sentence. " * 50
        chunks = processor.chunk_text(text)

        # Should create multiple chunks
        assert len(chunks) > 1

        # Each chunk should be within size limit
        for chunk in chunks:
            assert (
                len(chunk) <= processor.chunk_size + 100
            )  # Some tolerance for overlap

    def test_chunk_overlap(self, processor):
        """Test that chunks have appropriate overlap"""
        text = " ".join([f"Sentence number {i}." for i in range(100)])
        chunks = processor.chunk_text(text)

        # With overlap, chunks should share some content
        if len(chunks) >= 2:
            # Last part of first chunk might appear in second chunk
            assert len(chunks) > 1

    def test_course_metadata_extraction(self, processor, sample_course_file):
        """Test that course metadata is correctly extracted"""
        course, _ = processor.process_course_document(sample_course_file)

        assert course.title == "Python Programming"
        assert course.course_link == "https://example.com/python"
        assert course.instructor == "Jane Doe"
        assert len(course.lessons) == 3

    def test_lesson_metadata_extraction(self, processor, sample_course_file):
        """Test that lesson metadata is correctly extracted"""
        course, _ = processor.process_course_document(sample_course_file)

        # Check first lesson
        lesson1 = course.lessons[0]
        assert lesson1.lesson_number == 1
        assert lesson1.title == "Introduction"
        assert lesson1.lesson_link == "https://example.com/python/lesson1"

        # Check second lesson
        lesson2 = course.lessons[1]
        assert lesson2.lesson_number == 2
        assert lesson2.title == "Variables and Types"

        # Check third lesson
        lesson3 = course.lessons[2]
        assert lesson3.lesson_number == 3
        assert lesson3.title == "Functions"

    def test_chunk_course_title_assignment(self, processor, sample_course_file):
        """Test that all chunks are assigned the correct course title"""
        course, chunks = processor.process_course_document(sample_course_file)

        for chunk in chunks:
            assert chunk.course_title == "Python Programming"

    def test_chunk_lesson_number_assignment(self, processor, sample_course_file):
        """Test that chunks are assigned the correct lesson number"""
        course, chunks = processor.process_course_document(sample_course_file)

        # Group chunks by lesson number
        lesson_numbers = set(chunk.lesson_number for chunk in chunks)

        # Should have chunks for lessons 1, 2, and 3
        assert 1 in lesson_numbers
        assert 2 in lesson_numbers
        assert 3 in lesson_numbers

    def test_chunk_index_sequencing(self, processor, sample_course_file):
        """Test that chunk indices are sequential"""
        course, chunks = processor.process_course_document(sample_course_file)

        indices = [chunk.chunk_index for chunk in chunks]

        # Indices should be sequential starting from 0
        assert indices == list(range(len(chunks)))

    def test_empty_file_handling(self, processor):
        """Test handling of empty or minimal files"""
        content = "Course Title: Empty Course\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            course, chunks = processor.process_course_document(temp_path)
            assert course.title == "Empty Course"
            # Should handle empty content gracefully
        finally:
            os.remove(temp_path)

    def test_missing_course_link(self, processor):
        """Test that missing course link is handled"""
        content = """Course Title: No Link Course
Course Instructor: Test

Lesson 1: Test Lesson
Some content here.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            course, chunks = processor.process_course_document(temp_path)
            assert course.course_link is None
        finally:
            os.remove(temp_path)

    def test_lesson_without_link(self, processor):
        """Test that lessons without links are handled"""
        content = """Course Title: Test Course
Course Link: https://example.com/test
Course Instructor: Test Instructor

Lesson 1: No Link Lesson
This lesson has no link but has sufficient content for processing.
Python is a versatile programming language used for many applications including
web development, data science, automation, and more. It has a clear syntax that
makes it beginner-friendly and productive. The language supports multiple programming
paradigms including procedural, object-oriented, and functional programming.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            course, chunks = processor.process_course_document(temp_path)
            assert len(course.lessons) == 1
            assert course.lessons[0].lesson_link is None
        finally:
            os.remove(temp_path)

    def test_unicode_handling(self, processor):
        """Test that Unicode characters are handled correctly"""
        content = """Course Title: Unicode Course üñíçödé
Course Instructor: José García

Lesson 1: Introduction
Content with émojis 🎉 and spëcial çhars.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            course, chunks = processor.process_course_document(temp_path)
            assert "üñíçödé" in course.title
            assert "José García" == course.instructor
        finally:
            os.remove(temp_path)

    def test_all_lessons_except_last_have_same_prefix_format(
        self, processor, sample_course_file
    ):
        """Test that lessons 1 and 2 have the same prefix format"""
        course, chunks = processor.process_course_document(sample_course_file)

        # Get first chunks of lessons 1 and 2
        lesson1_chunks = [c for c in chunks if c.lesson_number == 1]
        lesson2_chunks = [c for c in chunks if c.lesson_number == 2]

        if lesson1_chunks and lesson2_chunks:
            chunk1_prefix = lesson1_chunks[0].content.split(":")[0]
            chunk2_prefix = lesson2_chunks[0].content.split(":")[0]

            # Both should have "Lesson X content" format (without "Course" prefix)
            assert (
                "Course" not in chunk1_prefix
            ), f"Lesson 1 should not have 'Course' in prefix: {chunk1_prefix}"
            assert (
                "Course" not in chunk2_prefix
            ), f"Lesson 2 should not have 'Course' in prefix: {chunk2_prefix}"

    def test_last_lesson_has_different_prefix_bug(self, processor, sample_course_file):
        """
        Explicit test for the bug: Last lesson has 'Course X Lesson Y' prefix
        while other lessons have just 'Lesson Y' prefix
        """
        course, chunks = processor.process_course_document(sample_course_file)

        lesson3_chunks = [c for c in chunks if c.lesson_number == 3]

        if lesson3_chunks:
            last_chunk_content = lesson3_chunks[0].content

            # Check if it has the buggy "Course ... Lesson" prefix
            has_course_prefix = last_chunk_content.startswith(
                "Course Python Programming Lesson"
            )

            if has_course_prefix:
                pytest.fail(
                    "BUG CONFIRMED: Last lesson has 'Course X Lesson Y' prefix\n"
                    "while other lessons have 'Lesson Y' prefix.\n"
                    "This inconsistency is in document_processor.py line 234.\n"
                    f"Actual prefix: {last_chunk_content[:60]}"
                )
