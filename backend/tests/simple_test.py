#!/usr/bin/env python3
"""
Simple diagnostic test to check basic functionality
"""
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all modules can be imported"""
    try:
        print("Testing basic imports...")

        import config

        print("✅ config imported")

        import models

        print("✅ models imported")

        import vector_store

        print("✅ vector_store imported")

        import search_tools

        print("✅ search_tools imported")

        import session_manager

        print("✅ session_manager imported")

        import ai_generator

        print("✅ ai_generator imported")

        import rag_system

        print("✅ rag_system imported")

        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality without external dependencies"""
    try:
        print("\nTesting basic functionality...")

        # Test config
        from config import config

        print(
            f"✅ Config loaded: ANTHROPIC_API_KEY exists = {bool(config.ANTHROPIC_API_KEY)}"
        )

        # Test models
        from models import Course, CourseChunk, Lesson

        lesson = Lesson(lesson_number=1, title="Test Lesson", lesson_link="test.com")
        course = Course(
            title="Test Course",
            instructor="Test Instructor",
            course_link="test.com",
            lessons=[lesson],
        )
        chunk = CourseChunk(
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0,
            content="Test content",
        )
        print("✅ Models created successfully")

        # Test search tools (without vector store)
        from search_tools import CourseSearchTool, ToolManager

        manager = ToolManager()
        print("✅ ToolManager created")

        # Test session manager
        from session_manager import SessionManager

        session = SessionManager()
        session_id = session.create_session()
        print(f"✅ SessionManager created session: {session_id}")

        return True

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run diagnostic tests"""
    print("🔍 RAG System Diagnostic Test")
    print("=" * 40)

    # Test imports
    imports_ok = test_imports()

    if not imports_ok:
        print("\n❌ Import tests failed - cannot continue")
        return False

    # Test basic functionality
    functionality_ok = test_basic_functionality()

    if functionality_ok:
        print("\n✅ All diagnostic tests passed!")
        print("The basic components seem to be working correctly.")
        print("The issue might be in integration or external dependencies.")
    else:
        print("\n❌ Some diagnostic tests failed")

    return functionality_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
