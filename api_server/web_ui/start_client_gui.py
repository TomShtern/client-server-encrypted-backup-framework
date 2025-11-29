#!/usr/bin/env python3
"""
One-click launcher for CyberBackup Client GUI
Starts HTTP server and opens browser automatically
"""

import os
import signal
import socket
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler


class ClientGUIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(__file__), **kwargs)

    def log_message(self, format, *args):
        # Suppress HTTP server logs for cleaner output
        pass

    def guess_type(self, path):
        """Override to ensure .js files are served with correct MIME type for ES6 modules"""
        mimetype = super().guess_type(path)
        return "application/javascript" if str(path).endswith(".js") else mimetype

    def end_headers(self):
        """Add necessary headers for module loading"""
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        """Handle GET requests with error suppression for client disconnects"""
        try:
            super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            # Client disconnected before response was fully sent - this is normal
            pass


def find_free_port(start_port=8080):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("localhost", port))
            sock.close()
            return port
        except OSError:
            continue
    return start_port


def start_server(port):
    """Start the HTTP server"""
    server = HTTPServer(("localhost", port), ClientGUIHandler)
    print(f"🚀 CyberBackup Client GUI running at http://localhost:{port}")
    print("📁 Serving files from:", os.path.dirname(__file__))
    print("⏹️  Press Ctrl+C to stop the server")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.server_close()


def open_browser(port, delay=1):
    """Open browser after a short delay"""
    time.sleep(delay)
    url = f"http://localhost:{port}/NewGUIforClient.html"
    print(f"🌐 Opening browser: {url}")
    webbrowser.open(url)


def main():
    """Main launcher function"""
    print("=" * 60)
    print("🎯 CyberBackup Client GUI Launcher")
    print("=" * 60)

    # Find free port
    port = find_free_port(8080)

    # Start server in main thread
    # Start browser opener in separate thread
    browser_thread = threading.Thread(target=open_browser, args=(port, 1), daemon=True)
    browser_thread.start()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Start the server
    start_server(port)


if __name__ == "__main__":
    main()
