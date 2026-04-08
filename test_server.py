#!/usr/bin/env python3
import http.server
import socketserver
import os

PORT = 8000

# 改变工作目录到 frontend
os.chdir("frontend")

Handler = http.server.SimpleHTTPRequestHandler

print(f"Starting server at http://localhost:{PORT}")
print(f"Serving files from: {os.getcwd()}")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")