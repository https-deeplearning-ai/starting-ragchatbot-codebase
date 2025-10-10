"""Simple validation tests that don't require heavy dependencies"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_imports():
    """Test that basic imports work"""
    try:
        from config import Config
        from models import Course, CourseChunk, Lesson

        assert True
    except ImportError as e:
        assert False, f"Import failed: {e}"


def test_course_model():
    """Test Course model creation"""
    from models import Course, Lesson

    course = Course(
        title="Test Course",
        course_link="https://example.com",
        instructor="Test Instructor",
        lessons=[
            Lesson(
                lesson_number=0,
                title="Intro",
                lesson_link="https://example.com/lesson0",
            ),
            Lesson(
                lesson_number=1, title="Main", lesson_link="https://example.com/lesson1"
            ),
        ],
    )

    assert course.title == "Test Course"
    assert course.instructor == "Test Instructor"
    assert len(course.lessons) == 2
    assert course.lessons[0].lesson_number == 0


def test_course_chunk_model():
    """Test CourseChunk model creation"""
    from models import CourseChunk

    chunk = CourseChunk(
        content="Course Test Lesson 1 content: This is test content.",
        course_title="Test Course",
        lesson_number=1,
        chunk_index=0,
    )

    assert chunk.course_title == "Test Course"
    assert chunk.lesson_number == 1
    assert chunk.chunk_index == 0
    assert "Course Test Lesson 1 content:" in chunk.content


def test_config():
    """Test configuration loading"""
    from config import Config

    config = Config()

    assert config.CHUNK_SIZE > 0
    assert config.CHUNK_OVERLAP >= 0
    assert config.MAX_RESULTS > 0
    assert config.MAX_HISTORY > 0
    assert config.ANTHROPIC_MODEL is not None


def test_document_processor_imports():
    """Test document processor can be imported"""
    try:
        from document_processor import DocumentProcessor

        processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)
        assert processor.chunk_size == 800
        assert processor.chunk_overlap == 100
    except ImportError as e:
        assert False, f"DocumentProcessor import failed: {e}"


def test_chunk_text_basic():
    """Test basic text chunking"""
    from document_processor import DocumentProcessor

    processor = DocumentProcessor(chunk_size=50, chunk_overlap=10)
    text = "This is sentence one. This is sentence two. This is sentence three."

    chunks = processor.chunk_text(text)

    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)


def test_chunk_context_format():
    """Test that chunk context follows the fixed format"""
    import re

    from document_processor import DocumentProcessor
    from models import Course

    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    # Create a simple test document
    test_content = """Course Title: Test Course
Course Link: https://example.com
Course Instructor: Test Instructor

Lesson 0: Introduction
Lesson Link: https://example.com/lesson0
This is the introduction lesson content. It has multiple sentences. This helps test chunking.

Lesson 1: Main Content
Lesson Link: https://example.com/lesson1
This is the main lesson content with more details. It should also be chunked properly.
"""

    # Write to temp file
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt", encoding="utf-8"
    ) as f:
        f.write(test_content)
        temp_path = f.name

    try:
        course, chunks = processor.process_course_document(temp_path)

        # Verify all chunks have consistent format
        for chunk in chunks:
            # All chunks should start with "Course {title} Lesson {number} content:"
            assert (
                "Course" in chunk.content
            ), f"Missing 'Course' in chunk: {chunk.content[:100]}"
            assert (
                "Lesson" in chunk.content
            ), f"Missing 'Lesson' in chunk: {chunk.content[:100]}"
            assert (
                "content:" in chunk.content
            ), f"Missing 'content:' in chunk: {chunk.content[:100]}"

            # Should match the pattern: "Course {title} Lesson {n} content: ..."
            pattern = r"Course .+ Lesson \d+ content:"
            assert re.match(
                pattern, chunk.content
            ), f"Chunk doesn't match expected format: {chunk.content[:100]}"

        # Verify consistency: all chunks should have the same prefix pattern
        prefixes = []
        for chunk in chunks:
            match = re.match(r"(Course .+ Lesson \d+ content:)", chunk.content)
            if match:
                # Extract just the pattern, not the specific values
                prefix_template = re.sub(r"Lesson \d+", "Lesson N", match.group(1))
                prefix_template = re.sub(
                    r"Course .+ Lesson", "Course X Lesson", prefix_template
                )
                prefixes.append(prefix_template)

        # All should follow the same template
        assert (
            len(set(prefixes)) == 1
        ), f"Inconsistent prefix formats found: {set(prefixes)}"

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_ai_generator_system_prompt():
    """Test that AI generator system prompt doesn't have one-tool limitation"""
    from ai_generator import AIGenerator

    prompt = AIGenerator.SYSTEM_PROMPT

    # Should NOT have the old limitation
    assert (
        "One tool call per query maximum" not in prompt
    ), "System prompt still contains 'One tool call per query maximum' limitation!"

    # Should have the new flexible guidance
    assert (
        "Use tools judiciously" in prompt or "multiple tools" in prompt
    ), "System prompt missing flexible tool usage guidance"


def test_ai_generator_creation():
    """Test AI generator can be created"""
    from ai_generator import AIGenerator

    generator = AIGenerator(api_key="test-key", model="test-model")

    assert generator.model == "test-model"
    assert generator.base_params["temperature"] == 0
    assert generator.base_params["max_tokens"] == 800


def test_session_manager():
    """Test session manager functionality"""
    from session_manager import SessionManager

    manager = SessionManager(max_history=2)

    # Create session
    session_id = manager.create_session()
    assert session_id is not None
    assert session_id in manager.sessions

    # Add exchange
    manager.add_exchange(session_id, "Question 1", "Answer 1")

    # Get history
    history = manager.get_conversation_history(session_id)
    assert history is not None
    assert "Question 1" in history
    assert "Answer 1" in history

    # Add more exchanges
    manager.add_exchange(session_id, "Question 2", "Answer 2")
    manager.add_exchange(session_id, "Question 3", "Answer 3")

    # Should respect max_history limit
    messages = manager.sessions[session_id]
    assert len(messages) <= manager.max_history * 2


if __name__ == "__main__":
    # Run tests manually
    import traceback

    tests = [
        test_imports,
        test_course_model,
        test_course_chunk_model,
        test_config,
        test_document_processor_imports,
        test_chunk_text_basic,
        test_chunk_context_format,
        test_ai_generator_system_prompt,
        test_ai_generator_creation,
        test_session_manager,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}")
            print(f"   {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    sys.exit(0 if failed == 0 else 1)
