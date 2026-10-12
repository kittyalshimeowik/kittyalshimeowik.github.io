"""
Local HTTP Server for Screenshot Testing.
Spawns a clean background HTTP server on an ephemeral port to serve static assets
without CORS or file-protocol restrictions.
"""

import functools
import http.server
import os
import socketserver
import threading
from typing import Optional


class QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Silences standard HTTP request logging in terminal output."""

    def log_message(self, format, *args):
        # Suppress standard GET / POST logs during testing
        pass


class LocalSiteServer:
    """Manages an ephemeral background HTTP server serving project root."""

    def __init__(self, root_dir: Optional[str] = None, host: str = "127.0.0.1", port: int = 0):
        if root_dir is None:
            # Default to root of the repo (one level above this directory)
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.root_dir = os.path.abspath(root_dir)
        self.host = host
        self.requested_port = port
        self.httpd: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.port: Optional[int] = None

    def start(self) -> str:
        """Starts the server in a daemon thread and returns base URL."""
        if self.httpd is not None:
            return self.base_url

        handler_factory = functools.partial(QuietHTTPHandler, directory=self.root_dir)

        # Allow immediate reuse of address
        class ReusableTCPServer(socketserver.TCPServer):
            allow_reuse_address = True

        self.httpd = ReusableTCPServer((self.host, self.requested_port), handler_factory)
        self.port = self.httpd.server_address[1]

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self.base_url

    def stop(self):
        """Shuts down the server and cleans up resources."""
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            finally:
                self.httpd = None
                self.thread = None
                self.port = None

    @property
    def base_url(self) -> str:
        if self.port is None:
            raise RuntimeError("LocalSiteServer has not been started.")
        return f"http://{self.host}:{self.port}"

    def get_url(self, path: str = "index.html") -> str:
        """Returns fully qualified URL for a given relative path."""
        clean_path = path.lstrip("/")
        return f"{self.base_url}/{clean_path}"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
