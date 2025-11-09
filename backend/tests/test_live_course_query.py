"""Test API with course-specific content queries"""
import pytest
import requests
import json


def test_api_course_specific_query():
    """Test API with a query about specific course content"""
    url = "http://127.0.0.1:8000/api/query"

    # First check what courses are available
    courses_response = requests.get("http://127.0.0.1:8000/api/courses")
    print(f"\n=== Available Courses ===")
    print(f"Status: {courses_response.status_code}")
    if courses_response.status_code == 200:
        courses_data = courses_response.json()
        print(f"Total courses: {courses_data['total_courses']}")
        print(f"Course titles: {courses_data['course_titles']}")
    else:
        print(f"Error: {courses_response.text}")

    # Now test a course content query
    payload = {
        "query": "Tell me about the MCP course",
        "session_id": None
    }

    response = requests.post(url, json=payload, timeout=30)

    print(f"\n=== Course Query Response ===")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"Error Response: {response.text}")
    else:
        data = response.json()
        print(f"Answer: {data.get('answer', 'N/A')[:200]}...")
        print(f"Sources: {data.get('sources', [])}")
        print(f"Source Links: {data.get('source_links', [])}")


def test_api_lesson_specific_query():
    """Test API with a lesson-specific query"""
    url = "http://127.0.0.1:8000/api/query"

    payload = {
        "query": "What is covered in lesson 1?",
        "session_id": None
    }

    response = requests.post(url, json=payload, timeout=30)

    print(f"\n=== Lesson Query Response ===")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"Error Response: {response.text}")
    else:
        data = response.json()
        print(f"Answer: {data.get('answer', 'N/A')[:200]}...")
        print(f"Sources: {data.get('sources', [])}")


def test_api_nonexistent_course_query():
    """Test API with query about non-existent course"""
    url = "http://127.0.0.1:8000/api/query"

    payload = {
        "query": "Tell me about the XYZ Nonexistent Course that doesn't exist",
        "session_id": None
    }

    response = requests.post(url, json=payload, timeout=30)

    print(f"\n=== Nonexistent Course Query Response ===")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"Error Response: {response.text}")
    else:
        data = response.json()
        print(f"Answer: {data.get('answer', 'N/A')}")
        print(f"Sources: {data.get('sources', [])}")


if __name__ == "__main__":
    print("Testing course-specific queries...")
    test_api_course_specific_query()
    test_api_lesson_specific_query()
    test_api_nonexistent_course_query()
