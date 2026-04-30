#!/usr/bin/env python3
"""
Port Talbot Decision Framework — Local Launcher
Run this file to start a local server and open the app in your browser.

Usage:
  python launch.py
  python3 launch.py

Works on Mac, Windows, and Linux.
"""

import os
import sys
import time
import platform
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
HOST = "localhost"
FILE = "port_talbot_decision_framework.html"
URL  = f"http://{HOST}:{PORT}/{FILE}"


class QuietHandler(SimpleHTTPRequestHandler):
    """Serve files silently — no request logs cluttering the terminal."""
    def log_message(self, format, *args):
        pass  # suppress access logs
    def end_headers(self):
        # Add CORS headers so the Groq API call works from localhost
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def open_browser():
    """Wait 1 second for the server to start, then open the browser."""
    time.sleep(1.0)
    webbrowser.open(URL)


def check_file():
    """Make sure the HTML file exists in the same folder."""
    if not os.path.exists(FILE):
        print(f"\n  ERROR: '{FILE}' not found in this folder.")
        print(f"  Make sure launch.py and {FILE} are in the same directory.\n")
        sys.exit(1)


def find_free_port(start=8080):
    """Find a free port starting from start."""
    import socket
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, port))
                return port
            except OSError:
                continue
    return start


def main():
    # Change working directory to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    check_file()

    global PORT, URL
    PORT = find_free_port(8080)
    URL  = f"http://{HOST}:{PORT}/{FILE}"

    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │   PORT TALBOT · DECISION FRAMEWORK              │")
    print("  ├─────────────────────────────────────────────────┤")
    print(f"  │   Server:   http://{HOST}:{PORT}                   │")
    print(f"  │   Opening:  {URL[:46]}  │")
    print("  ├─────────────────────────────────────────────────┤")
    print("  │   Press Ctrl+C to stop the server               │")
    print("  └─────────────────────────────────────────────────┘")
    print()

    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Start server
    server = HTTPServer((HOST, PORT), QuietHandler)
    print(f"  Server running — browser opening at {URL}")
    print(f"  Waiting for Ctrl+C ...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped. Goodbye.\n")
        server.shutdown()


if __name__ == "__main__":
    main()
