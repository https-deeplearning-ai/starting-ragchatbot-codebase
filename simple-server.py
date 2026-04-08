#!/usr/bin/env python3
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Simple HTTP server for frontend only
import http.server
import socketserver

PORT = 8000
os.chdir('frontend')

Handler = http.server.SimpleHTTPRequestHandler

print(f"Starting simple server on http://localhost:{PORT}")
print(f"Serving files from: {os.getcwd()}")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")