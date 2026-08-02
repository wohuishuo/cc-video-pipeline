"""Single-purpose loopback HTTP receiver for the desktop OAuth redirect."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Empty, Queue
import time

from .flow import OAuthAttempt, OAuthError, OAuthFlow


SUCCESS_PAGE = b"<!doctype html><meta charset=utf-8><title>Connected</title><h1>YouTube connected</h1><p>You can close this tab and return to Video Graph Studio.</p>"
FAILURE_PAGE = b"<!doctype html><meta charset=utf-8><title>Not connected</title><h1>Connection not accepted</h1><p>Return to Video Graph Studio and try again.</p>"


class LoopbackReceiver:
    def __init__(self) -> None:
        self._results: Queue[tuple[str, str]] = Queue()
        self._attempt: OAuthAttempt | None = None
        self._last_error: OAuthError | None = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                status = 404
                page = FAILURE_PAGE
                if owner._attempt is not None:
                    try:
                        code = OAuthFlow.accept_callback(owner._attempt, self.path)
                    except OAuthError as error:
                        owner._last_error = error
                        status = 400 if self.path.startswith("/oauth/callback") else 404
                        if "denied" in str(error):
                            owner._results.put(("error", str(error)))
                    else:
                        owner._results.put(("code", code)); status = 200; page = SUCCESS_PAGE
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(page)

            def log_message(self, format, *args):
                return

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._server.timeout = 0.2

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def receive(self, attempt: OAuthAttempt, timeout: float) -> str:
        self._attempt = attempt
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._server.handle_request()
            try:
                kind, value = self._results.get_nowait()
            except Empty:
                continue
            if kind == "code":
                return value
            raise OAuthError(value)
        raise OAuthError("OAuth callback timed out") from self._last_error

    def close(self) -> None:
        self._server.server_close()
