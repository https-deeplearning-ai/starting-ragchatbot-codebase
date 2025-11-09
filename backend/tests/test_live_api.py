"""Test actual API endpoint to debug 'query failed' issue"""
import pytest
import requests
import json


def test_api_query_content_question():
    """Test actual API with a content-related question"""
    url = "http://127.0.0.1:8000/api/query"

    payload = {
        "query": "What is Python?",
        "session_id": None
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        print(f"\n=== API Response ===")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {response.headers}")

        if response.status_code != 200:
            print(f"Error Response: {response.text}")
        else:
            data = response.json()
            print(f"Success Response: {json.dumps(data, indent=2)}")

        # Assert that we get a valid response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed: {e}")


def test_api_general_knowledge_question():
    """Test API with a general knowledge question (no search needed)"""
    url = "http://127.0.0.1:8000/api/query"

    payload = {
        "query": "Hello, how are you?",
        "session_id": None
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        print(f"\n=== General Question Response ===")
        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: {response.text}")
        else:
            data = response.json()
            print(f"Answer: {data.get('answer', 'N/A')}")

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed: {e}")


if __name__ == "__main__":
    # Run this test directly to see output
    print("Testing live API...")
    test_api_query_content_question()
