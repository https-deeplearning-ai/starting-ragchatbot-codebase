"""Verify the fix works for different query types"""
import requests


def test_queries():
    """Test various query types after the fix"""
    url = "http://127.0.0.1:8000/api/query"

    test_cases = [
        {
            "query": "What does the MCP course teach?",
            "expected_sources": True,
            "description": "General course question - should NOW have sources"
        },
        {
            "query": "Hello, how are you?",
            "expected_sources": False,
            "description": "Greeting - should NOT search"
        },
        {
            "query": "Tell me about lesson 2 in the MCP course",
            "expected_sources": True,
            "description": "Specific lesson query - should have sources"
        },
        {
            "query": "What is retrieval in the Advanced Retrieval course?",
            "expected_sources": True,
            "description": "Content question about specific course - should have sources"
        },
        {
            "query": "What can you help me with?",
            "expected_sources": False,
            "description": "Meta question - should NOT search"
        }
    ]

    print("\n" + "="*70)
    print("TESTING FIX VERIFICATION")
    print("="*70)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {test_case['description']}")
        print(f"Query: {test_case['query']}")

        try:
            response = requests.post(url, json={"query": test_case['query']}, timeout=30)

            if response.status_code == 200:
                data = response.json()
                has_sources = len(data['sources']) > 0

                print(f"[OK] Status: 200")
                print(f"[OK] Sources: {len(data['sources'])} found")

                if test_case['expected_sources'] and not has_sources:
                    print(f"[FAIL] Expected sources but got none!")
                elif not test_case['expected_sources'] and has_sources:
                    print(f"[WARN] Didn't expect sources but got {len(data['sources'])}")
                else:
                    print(f"[PASS] Source expectation met")

            else:
                print(f"[FAIL] Status {response.status_code}")

        except Exception as e:
            print(f"[ERROR] {e}")

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_queries()
