"""
Simple HTTP server to serve the frontend
Run this from the Claussifier directory
"""

import http.server
import socketserver
import os

# Change to frontend directory
os.chdir('frontend')

PORT = 8080

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"✓ Frontend server running at http://localhost:{PORT}")
    print(f"✓ Open http://localhost:{PORT}/index.html in your browser")
    print(f"\nMake sure the API server is also running on port 8000!")
    print("Press Ctrl+C to stop")
    httpd.serve_forever()
