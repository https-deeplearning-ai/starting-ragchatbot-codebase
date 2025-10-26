"""
Simple test runner for API tests to verify the testing infrastructure
This script validates that the API test structure is correct without relying on uv environment
"""
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all required imports work"""
    print("Testing imports...")

    try:
        # Test FastAPI imports
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient
        from pydantic import BaseModel
        from typing import List, Optional
        print("✓ FastAPI imports successful")
    except ImportError as e:
        print(f"✗ FastAPI import failed: {e}")
        return False

    try:
        # Test TestClient creation
        app = FastAPI()
        client = TestClient(app)
        print("✓ TestClient creation successful")
    except Exception as e:
        print(f"✗ TestClient creation failed: {e}")
        return False

    return True

def test_fixtures():
    """Test that fixtures can be loaded"""
    print("\nTesting fixtures...")

    try:
        # Import conftest
        import conftest
        print("✓ conftest.py imports successfully")
    except Exception as e:
        print(f"✗ conftest.py import failed: {e}")
        return False

    # Check if key fixtures are defined
    fixtures_to_check = [
        'test_app',
        'client',
        'mock_rag_system',
        'sample_query_requests',
        'sample_api_responses'
    ]

    for fixture_name in fixtures_to_check:
        if hasattr(conftest, fixture_name):
            print(f"✓ Fixture '{fixture_name}' exists")
        else:
            print(f"✗ Fixture '{fixture_name}' missing")
            return False

    return True

def test_app_creation():
    """Test that the test app can be created"""
    print("\nTesting app creation...")

    try:
        import conftest

        # Create test app
        app = conftest.test_app()
        print("✓ Test app creation successful")

        # Create test client
        client = TestClient(app)
        print("✓ Test client creation successful")

        # Test root endpoint
        response = client.get("/")
        if response.status_code == 200:
            print("✓ Root endpoint accessible")
        else:
            print(f"✗ Root endpoint failed: {response.status_code}")
            return False

        return True

    except Exception as e:
        print(f"✗ App creation failed: {e}")
        return False

def test_api_endpoints():
    """Test basic API endpoint functionality"""
    print("\nTesting API endpoints...")

    try:
        import conftest
        from fastapi.testclient import TestClient

        app = conftest.test_app()
        client = TestClient(app)

        # Test query endpoint
        query_data = {"query": "What is machine learning?"}
        response = client.post("/api/query", json=query_data)

        if response.status_code == 200:
            print("✓ Query endpoint works")
            data = response.json()
            if "answer" in data and "sources" in data and "session_id" in data:
                print("✓ Query response structure correct")
            else:
                print("✗ Query response structure incorrect")
                return False
        else:
            print(f"✗ Query endpoint failed: {response.status_code}")
            return False

        # Test courses endpoint
        response = client.get("/api/courses")
        if response.status_code == 200:
            print("✓ Courses endpoint works")
            data = response.json()
            if "total_courses" in data and "course_titles" in data:
                print("✓ Courses response structure correct")
            else:
                print("✗ Courses response structure incorrect")
                return False
        else:
            print(f"✗ Courses endpoint failed: {response.status_code}")
            return False

        return True

    except Exception as e:
        print(f"✗ API endpoint test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== API Testing Infrastructure Validation ===\n")

    tests = [
        test_imports,
        test_fixtures,
        test_app_creation,
        test_api_endpoints
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests

    print("=== Summary ===")
    print(f"Passed: {passed}/{total} tests")

    if passed == total:
        print("🎉 All API testing infrastructure tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)