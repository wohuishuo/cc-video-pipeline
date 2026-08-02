import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-publisher"
sys.path.insert(0, str(APP))

from youtube_publisher.client import HttpResponse, YouTubeResumableClient
from youtube_publisher.contracts import YouTubeCredential


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, *, headers=None, json_body=None, form_body=None, file_path=None, offset=0, total=None):
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {}), "json": json_body, "form": form_body, "file": file_path, "offset": offset, "total": total})
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def response(status, payload=None, headers=None):
    return HttpResponse(status, headers or {}, json.dumps(payload or {}).encode())


def test_refreshes_token_starts_private_session_and_returns_video_id(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"abcdefgh")
    transport = FakeTransport([
        response(200, {"access_token": "temporary"}),
        response(200, headers={"location": "https://www.googleapis.com/upload/session"}),
        response(201, {"id": "youtube-id-1", "status": {"privacyStatus": "private"}}),
    ])
    credential = YouTubeCredential.parse(json.dumps({"clientId": "client", "clientSecret": "secret", "refreshToken": "refresh"}))

    result = YouTubeResumableClient(transport).upload(video, {"snippet": {"title": "Demo"}, "status": {"privacyStatus": "private"}}, credential)

    assert result.result_class == "COMPLETED"
    assert result.external_id == "youtube-id-1"
    assert transport.calls[1]["json"]["status"]["privacyStatus"] == "private"
    assert transport.calls[2]["offset"] == 0
    observable_calls = [{key: value for key, value in call.items() if key != "file"} for call in transport.calls[1:]]
    assert all("secret" not in json.dumps(call, default=str) and "refresh" not in json.dumps(call, default=str) for call in observable_calls)


def test_resumes_from_server_committed_range(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"abcdefgh")
    transport = FakeTransport([
        response(200, headers={"Location": "https://www.googleapis.com/upload/session"}),
        response(308, headers={"Range": "bytes=0-3"}),
        response(201, {"id": "youtube-id-2", "status": {"privacyStatus": "private"}}),
    ])
    credential = YouTubeCredential.parse(json.dumps({"accessToken": "temporary"}))

    result = YouTubeResumableClient(transport).upload(video, {"snippet": {"title": "Demo"}, "status": {"privacyStatus": "private"}}, credential)

    assert result.result_class == "COMPLETED"
    assert [call["offset"] for call in transport.calls if call["method"] == "PUT"] == [0, 4]


def test_exhausted_server_failures_become_unknown_not_success(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"abcdefgh")
    transport = FakeTransport([
        response(200, headers={"Location": "https://www.googleapis.com/upload/session"}),
        response(503), response(503), response(503),
    ])
    credential = YouTubeCredential.parse(json.dumps({"accessToken": "temporary"}))

    result = YouTubeResumableClient(transport, maximum_attempts=3, sleeper=lambda _: None).upload(video, {"snippet": {"title": "Demo"}, "status": {"privacyStatus": "private"}}, credential)

    assert result.result_class == "UNKNOWN"
    assert result.external_id is None
    assert "session" not in (result.error or "")


def test_transport_loss_after_session_is_unknown_and_redacts_session(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"abcdefgh")
    transport = FakeTransport([
        response(200, headers={"Location": "https://www.googleapis.com/upload/sensitive-session"}),
        OSError("failed at https://www.googleapis.com/upload/sensitive-session with temporary-token"),
        OSError("status failed at https://www.googleapis.com/upload/sensitive-session"),
    ])
    credential = YouTubeCredential.parse(json.dumps({"accessToken": "temporary-token"}))

    result = YouTubeResumableClient(transport, maximum_attempts=2, sleeper=lambda _: None).upload(video, {"snippet": {"title": "Demo"}, "status": {"privacyStatus": "private"}}, credential)

    assert result.result_class == "UNKNOWN"
    assert "sensitive-session" not in (result.error or "")
    assert "temporary-token" not in (result.error or "")


def test_non_private_completion_is_rejected(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"abcdefgh")
    transport = FakeTransport([
        response(200, headers={"Location": "https://www.googleapis.com/upload/session"}),
        response(201, {"id": "youtube-id-public", "status": {"privacyStatus": "public"}}),
    ])

    result = YouTubeResumableClient(transport).upload(video, {"snippet": {"title": "Demo"}, "status": {"privacyStatus": "private"}}, YouTubeCredential.parse(json.dumps({"accessToken": "token"})))

    assert result.result_class == "FAILED"
    assert result.external_id is None


def test_rejects_resumable_location_outside_google_without_sending_token(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"abcdefgh")
    transport = FakeTransport([response(200, headers={"Location": "https://attacker.example/upload"})])

    result = YouTubeResumableClient(transport).upload(video, {"snippet": {"title": "Demo"}, "status": {"privacyStatus": "private"}}, YouTubeCredential.parse(json.dumps({"accessToken": "temporary-token"})))

    assert result.result_class == "FAILED"
    assert len(transport.calls) == 1


def test_completion_without_private_visibility_fact_is_rejected(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"abcdefgh")
    transport = FakeTransport([
        response(200, headers={"Location": "https://www.googleapis.com/upload/session"}),
        response(201, {"id": "youtube-id-without-status"}),
    ])

    result = YouTubeResumableClient(transport).upload(video, {"snippet": {"title": "Demo"}, "status": {"privacyStatus": "private"}}, YouTubeCredential.parse(json.dumps({"accessToken": "token"})))

    assert result.result_class == "FAILED"
    assert result.external_id is None
