#!/usr/bin/env python3
"""Test script for sequential tool calling"""
import json

import requests


def test_query(query):
    url = "http://localhost:8000/api/query"
    payload = {"query": query}

    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print(f"{'='*80}\n")

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        data = response.json()
        print("FULL RESPONSE DATA:")
        print(json.dumps(data, indent=2))
        print("\n" + "=" * 80)
        if "response" in data:
            print("\nRESPONSE:")
            print(data["response"])
            print("\nSOURCES:")
            for source in data.get("sources", []):
                print(f"  - {source['text']}")
                if source.get("link"):
                    print(f"    Link: {source['link']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    # Test 1: Query that should trigger sequential tool calling
    # Expected: get_course_outline (to find lesson 3) → search_course_content (to get details)
    test_query("What does lesson 3 of the MCP course cover?")

    # Test 2: Another sequential query
    # Expected: get_course_outline (to see structure) → possibly search for specifics
    test_query("Compare what's taught in lesson 1 versus lesson 2 of the MCP course")
