"""Debug test to see tool calling in action"""
import requests


def test_single_query_with_debug():
    """Test a single query and watch debug output"""
    url = "http://127.0.0.1:8000/api/query"

    payload = {
        "query": "What does the MCP course teach?",
        "session_id": None
    }

    print("\n" + "="*60)
    print("SENDING QUERY: What does the MCP course teach?")
    print("="*60)

    response = requests.post(url, json=payload, timeout=30)

    print("\n" + "="*60)
    print("RESPONSE RECEIVED")
    print("="*60)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nAnswer (first 300 chars): {data['answer'][:300]}...")
        print(f"\nSources: {data['sources']}")
        print(f"Source Links: {data['source_links']}")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    test_single_query_with_debug()
