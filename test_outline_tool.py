#!/usr/bin/env python3
"""
Quick test script for the CourseOutlineTool
Run this from the backend directory after starting the application
"""

import sys
import os
sys.path.append('backend')

from backend.config import Config
from backend.vector_store import VectorStore
from backend.search_tools import CourseOutlineTool

def test_outline_tool():
    # Load config
    config = Config()

    # Initialize vector store
    vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)

    # Create outline tool
    outline_tool = CourseOutlineTool(vector_store)

    # Get all available courses first
    courses = vector_store.get_all_courses_metadata()
    print("Available courses:")
    for course in courses:
        print(f"  - {course.get('title', 'Unknown')}")

    if not courses:
        print("No courses found. Make sure you've added course documents to the system.")
        return

    # Test with the first available course
    test_course = courses[0].get('title', '')
    print(f"\nTesting outline tool with course: '{test_course}'")

    result = outline_tool.execute(test_course)
    print(f"\nResult:\n{result}")

    # Test with partial course name
    if len(test_course.split()) > 1:
        partial_name = test_course.split()[0]
        print(f"\nTesting with partial name: '{partial_name}'")
        partial_result = outline_tool.execute(partial_name)
        print(f"\nPartial Result:\n{partial_result}")

if __name__ == "__main__":
    test_outline_tool()