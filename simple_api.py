#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

class SimpleAPIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/query':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Simple mock response
            response = {
                "answer": "这是一个测试回复。后端 API 需要修复导入问题才能正常工作。",
                "sources": ["course1.pdf", "course2.pdf"],
                "session_id": "test-session-123"
            }

            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/api/courses':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = {
                "total_courses": 5,
                "course_titles": ["MCP: Build Rich-Context AI Apps", "Introduction to Python", "Advanced Machine Learning"]
            }

            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), SimpleAPIHandler)
    print("Simple API server running on http://localhost:8000")
    server.serve_forever()