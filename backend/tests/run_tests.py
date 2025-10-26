#!/usr/bin/env python3
"""
Test runner script for RAG system tests
"""
import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))

def run_tests():
    """Run all tests and return results"""
    print("🧪 Running RAG System Tests...")
    print("=" * 50)

    # Change to backend directory
    os.chdir(backend_dir)

    # Test command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
        "-x",  # Stop on first failure
        "--disable-warnings"  # Disable warnings
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=backend_dir)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"\nReturn code: {result.returncode}")

        return result.returncode == 0, result.stdout, result.stderr

    except Exception as e:
        print(f"Error running tests: {e}")
        return False, "", str(e)

def main():
    """Main function to run tests and analyze results"""
    print("🚀 Starting RAG System Test Suite")
    print("Purpose: Diagnose why the RAG chatbot returns 'query failed' for content-related questions")
    print()

    success, stdout, stderr = run_tests()

    if success:
        print("\n✅ All tests passed!")
        print("This suggests the components are working correctly in isolation.")
        print("The issue might be in integration, configuration, or environment.")
    else:
        print("\n❌ Tests failed!")
        print("This indicates specific components have issues that need to be addressed.")

        # Analyze common failure patterns
        if "ImportError" in stdout or "ImportError" in stderr:
            print("\n🔍 Found import errors - check dependencies and module structure")

        if "ModuleNotFoundError" in stdout or "ModuleNotFoundError" in stderr:
            print("\n🔍 Module not found - check Python path and module imports")

        if "AttributeError" in stdout or "AttributeError" in stderr:
            print("\n🔍 Attribute errors - check class interfaces and method signatures")

        if "AssertionError" in stdout:
            print("\n🔍 Assertion errors - logic issues in component behavior")

        if "ConnectionError" in stdout or "API" in stdout:
            print("\n🔍 Connection/API errors - check external service integration")

    print("\n" + "=" * 50)
    print("Test Summary Complete")

    return success

if __name__ == "__main__":
    main()