"""Small standard-library YouTube resumable-upload client."""

from __future__ import annotations

from dataclasses import dataclass
import http.client
import json
import mimetypes
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .contracts import YouTubeCredential


TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
UPLOAD_ENDPOINT = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
RETRIABLE = frozenset({500, 502, 503, 504})


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes

    def header(self, name: str) -> str | None:
        expected = name.lower()
        return next((str(value) for key, value in self.headers.items() if str(key).lower() == expected), None)

    def json(self) -> dict[str, Any]:
        try:
            value = json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("API returned invalid JSON") from error
        if not isinstance(value, dict):
            raise ValueError("API returned invalid JSON")
        return value


class Transport(Protocol):
    def request(self, method: str, url: str, *, headers: Mapping[str, str] | None = None, json_body: dict[str, Any] | None = None, form_body: dict[str, str] | None = None, file_path: Path | None = None, offset: int = 0, total: int | None = None) -> HttpResponse: ...


class StdlibTransport:
    def request(self, method: str, url: str, *, headers: Mapping[str, str] | None = None, json_body: dict[str, Any] | None = None, form_body: dict[str, str] | None = None, file_path: Path | None = None, offset: int = 0, total: int | None = None) -> HttpResponse:
        request_headers = dict(headers or {})
        if file_path is not None:
            return self._file_request(method, url, request_headers, Path(file_path), offset, total)
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json; charset=UTF-8")
        elif form_body is not None:
            body = urlencode(form_body).encode("ascii")
            request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            body = b""
        request = Request(url, data=body, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=60) as response:
                return HttpResponse(response.status, dict(response.headers.items()), response.read())
        except HTTPError as error:
            return HttpResponse(error.code, dict(error.headers.items()), error.read())

    @staticmethod
    def _file_request(method: str, url: str, headers: dict[str, str], path: Path, offset: int, total: int | None) -> HttpResponse:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("upload session returned an invalid URL")
        size = path.stat().st_size if total is None else total
        if offset < 0 or offset >= size:
            raise ValueError("upload offset is outside the video")
        remaining = size - offset
        headers["Content-Length"] = str(remaining)
        headers.setdefault("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        if offset:
            headers["Content-Range"] = f"bytes {offset}-{size - 1}/{size}"
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port, timeout=120)
        target = parsed.path or "/"
        if parsed.query:
            target += f"?{parsed.query}"
        try:
            connection.putrequest(method, target)
            for key, value in headers.items():
                connection.putheader(key, value)
            connection.endheaders()
            with path.open("rb") as source:
                source.seek(offset)
                while chunk := source.read(1024 * 1024):
                    connection.send(chunk)
            response = connection.getresponse()
            return HttpResponse(response.status, dict(response.getheaders()), response.read())
        finally:
            connection.close()


@dataclass(frozen=True)
class UploadOutcome:
    result_class: str
    external_id: str | None
    facts: dict[str, Any]
    error: str | None = None


class YouTubeResumableClient:
    def __init__(self, transport: Transport | None = None, *, maximum_attempts: int = 6, sleeper: Callable[[float], None] = time.sleep):
        if maximum_attempts < 1:
            raise ValueError("maximum_attempts must be positive")
        self.transport = transport or StdlibTransport()
        self.maximum_attempts = maximum_attempts
        self.sleeper = sleeper

    def upload(self, video: Path, metadata: dict[str, Any], credential: YouTubeCredential) -> UploadOutcome:
        video = Path(video).resolve()
        if not video.is_file():
            return UploadOutcome("FAILED", None, {}, "video does not exist")
        if metadata.get("status", {}).get("privacyStatus") != "private":
            return UploadOutcome("FAILED", None, {}, "YouTube Publisher accepts private visibility only")
        try:
            token = self._access_token(credential)
            size = video.stat().st_size
            if size < 1:
                return UploadOutcome("FAILED", None, {}, "video must not be empty")
            mime = mimetypes.guess_type(video.name)[0] or "application/octet-stream"
            started = self.transport.request(
                "POST", UPLOAD_ENDPOINT,
                headers={"Authorization": f"Bearer {token}", "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": mime},
                json_body=metadata,
            )
            if started.status not in {200, 201}:
                return UploadOutcome("FAILED", None, {"httpStatus": started.status}, "YouTube rejected upload-session creation")
            session = started.header("Location")
            if not session:
                return UploadOutcome("FAILED", None, {"httpStatus": started.status}, "YouTube omitted the resumable upload location")
            session_url = urlsplit(session)
            hostname = (session_url.hostname or "").lower()
            if session_url.scheme != "https" or not (hostname == "googleapis.com" or hostname.endswith(".googleapis.com")):
                return UploadOutcome("FAILED", None, {"httpStatus": started.status}, "YouTube returned an untrusted resumable upload location")
        except (OSError, ValueError, TimeoutError):
            return UploadOutcome("FAILED", None, {}, "could not create a YouTube upload session")
        try:
            return self._upload_session(session, video, size, mime, token)
        except (OSError, ValueError, TimeoutError):
            return UploadOutcome("UNKNOWN", None, {}, "upload outcome could not be determined")

    def _access_token(self, credential: YouTubeCredential) -> str:
        if not credential.refreshable:
            assert credential.access_token
            return credential.access_token
        refreshed = self.transport.request(
            "POST", TOKEN_ENDPOINT,
            form_body={"client_id": credential.client_id or "", "client_secret": credential.client_secret or "", "refresh_token": credential.refresh_token or "", "grant_type": "refresh_token"},
        )
        if refreshed.status != 200:
            raise ValueError("YouTube OAuth refresh failed")
        token = refreshed.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise ValueError("YouTube OAuth response omitted access_token")
        return token

    def _upload_session(self, session: str, video: Path, size: int, mime: str, token: str) -> UploadOutcome:
        offset = 0
        attempts = 0
        headers = {"Authorization": f"Bearer {token}", "Content-Type": mime}
        while attempts < self.maximum_attempts:
            attempts += 1
            try:
                response = self.transport.request("PUT", session, headers=headers, file_path=video, offset=offset, total=size)
            except (OSError, TimeoutError):
                response = HttpResponse(503, {}, b"")
            completed = self._completed(response, attempts)
            if completed:
                return completed
            if response.status == 308:
                offset = self._next_offset(response, size)
                continue
            if response.status not in RETRIABLE:
                return UploadOutcome("FAILED", None, {"httpStatus": response.status, "attempts": attempts}, "YouTube rejected video bytes")
            if attempts >= self.maximum_attempts:
                break
            attempts += 1
            status = self.transport.request("PUT", session, headers={**headers, "Content-Length": "0", "Content-Range": f"bytes */{size}"})
            completed = self._completed(status, attempts)
            if completed:
                return completed
            if status.status == 308:
                offset = self._next_offset(status, size)
            elif status.status not in RETRIABLE:
                return UploadOutcome("FAILED", None, {"httpStatus": status.status, "attempts": attempts}, "YouTube rejected resumable status query")
            if attempts < self.maximum_attempts:
                self.sleeper(min(2 ** (attempts - 1), 32))
        return UploadOutcome("UNKNOWN", None, {"attempts": attempts}, "upload outcome could not be determined")

    @staticmethod
    def _completed(response: HttpResponse, attempts: int) -> UploadOutcome | None:
        if response.status not in {200, 201}:
            return None
        try:
            payload = response.json()
        except ValueError:
            return UploadOutcome("FAILED", None, {"httpStatus": response.status, "attempts": attempts}, "YouTube completion response was invalid")
        external_id = payload.get("id")
        if not isinstance(external_id, str) or not external_id.strip():
            return UploadOutcome("FAILED", None, {"httpStatus": response.status, "attempts": attempts}, "YouTube completion response omitted video ID")
        privacy = payload.get("status", {}).get("privacyStatus") if isinstance(payload.get("status", {}), dict) else None
        if privacy != "private":
            return UploadOutcome("FAILED", None, {"httpStatus": response.status, "attempts": attempts}, "YouTube returned non-private visibility")
        return UploadOutcome("COMPLETED", external_id.strip(), {"httpStatus": response.status, "attempts": attempts, "privacyStatus": "private"})

    @staticmethod
    def _next_offset(response: HttpResponse, size: int) -> int:
        value = response.header("Range") or ""
        match = re.fullmatch(r"bytes=0-([0-9]+)", value.strip())
        offset = int(match.group(1)) + 1 if match else 0
        if offset >= size:
            raise ValueError("YouTube returned an invalid resumable range")
        return offset
