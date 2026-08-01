"""Loopback HTTP transport and static file server."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .api import StudioApplication


MAX_BODY_BYTES = 1024 * 1024


def create_server(
    host: str,
    port: int,
    application: StudioApplication,
    *,
    web_root: Path,
) -> ThreadingHTTPServer:
    if host != "127.0.0.1":
        raise ValueError("Video Graph Studio may bind only to 127.0.0.1")
    root = Path(web_root).resolve()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self._dispatch()

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch()

        def _dispatch(self) -> None:
            parsed = urlsplit(self.path)
            if parsed.path.startswith("/api/"):
                body = self._read_json() if self.command == "POST" else None
                if body is _INVALID:
                    self._send_json(400, {"resultClass": "REJECTED_MALFORMED"})
                    return
                status, payload = application.handle(
                    self.command, parsed.path, parse_qs(parsed.query), body
                )
                self._send_json(status, payload)
                return
            self._serve_static(parsed.path)

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return _INVALID
            if length <= 0 or length > MAX_BODY_BYTES:
                return _INVALID
            try:
                value = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return _INVALID
            return value if isinstance(value, dict) else _INVALID

        def _send_json(self, status: int, payload: dict) -> None:
            content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def _serve_static(self, request_path: str) -> None:
            relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
            candidate = (root / relative).resolve()
            if not (candidate == root or candidate.is_relative_to(root)) or not candidate.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format: str, *args) -> None:
            return

    return ThreadingHTTPServer((host, port), Handler)


_INVALID = object()

