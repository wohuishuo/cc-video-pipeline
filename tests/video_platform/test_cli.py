import json
import hashlib

from video_platform.cli import _json_text, _upload_digest, main
from video_platform.models import ProcessResult


def test_doctor_reports_each_required_dependency(capsys):
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code in (0, 1)
    assert set(payload["dependencies"]) == {"python", "yt-dlp", "ffmpeg", "ffprobe", "git"}


def test_capabilities_keeps_platform_statuses_independent(capsys):
    assert main(["capabilities", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["platforms"]) == {"youtube", "bilibili", "douyin", "tiktok"}
    assert all("download" in item and "upload" in item for item in payload["platforms"].values())
    assert payload["platforms"]["youtube"]["upload"] == "private-api-ready"


def test_download_rejects_explicit_platform_mismatch(capsys, tmp_path):
    code = main([
        "download", "tiktok", "https://youtube.com/watch?v=x", "--output-dir", str(tmp_path), "--json"
    ])
    assert code == 2
    assert "belongs to youtube" in json.loads(capsys.readouterr().out)["error"]


def test_upload_defaults_to_preparation_without_execution(capsys, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"sample")
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"Draft","description":"","tags":[]}', encoding="utf-8")
    code = main(["upload", "youtube", str(video), "--metadata", str(metadata), "--account", "me", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "prepared"
    assert "--visibility" in payload["command"]


def test_upload_rejects_missing_named_credential_environment(capsys, tmp_path, monkeypatch):
    monkeypatch.delenv("VIDEO_PLATFORM_CREDENTIAL", raising=False)
    video = tmp_path / "video.mp4"
    video.write_bytes(b"sample")
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"Draft"}', encoding="utf-8")

    code = main([
        "upload", "youtube", str(video), "--metadata", str(metadata),
        "--account", "me", "--credential-env", "VIDEO_PLATFORM_CREDENTIAL", "--json",
    ])

    assert code == 2
    assert "missing or empty" in json.loads(capsys.readouterr().out)["error"]


def test_prepared_upload_never_echoes_environment_credential(capsys, tmp_path, monkeypatch):
    secret = "platform-io-child-secret"
    monkeypatch.setenv("VIDEO_PLATFORM_CREDENTIAL", secret)
    video = tmp_path / "video.mp4"
    video.write_bytes(b"sample")
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"Draft"}', encoding="utf-8")

    code = main([
        "upload", "youtube", str(video), "--metadata", str(metadata),
        "--account", "me", "--credential-env", "VIDEO_PLATFORM_CREDENTIAL", "--json",
    ])
    output = capsys.readouterr().out

    assert code == 0
    assert json.loads(output)["status"] == "prepared"
    assert secret not in output


def test_json_console_output_is_ascii_safe_and_round_trips_unicode():
    text = _json_text({"title": "中文标题"})
    text.encode("ascii")
    assert json.loads(text)["title"] == "中文标题"


def test_credential_backed_youtube_execute_returns_internal_publisher_external_id(capsys, tmp_path, monkeypatch):
    secret = '{"accessToken":"must-not-appear"}'
    monkeypatch.setenv("VIDEO_PLATFORM_CREDENTIAL", secret)
    video = tmp_path / "video.mp4"; video.write_bytes(b"sample")
    metadata = tmp_path / "metadata.json"; metadata.write_text('{"title":"Private"}', encoding="utf-8")
    seen = {}

    class Runner:
        def run(self, args, cwd=None, env=None):
            seen["args"] = list(args); seen["cwd"] = cwd
            output = json.dumps({"resultClass": "COMPLETED", "value": {"externalId": "youtube-private-1", "privacyStatus": "private"}})
            return ProcessResult(tuple(args), 0, output, "")

    monkeypatch.setattr("video_platform.cli.ProcessRunner", Runner)

    code = main(["upload", "youtube", str(video), "--metadata", str(metadata), "--account", "primary", "--credential-env", "VIDEO_PLATFORM_CREDENTIAL", "--execute", "--json"])
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert code == 0
    assert payload["status"] == "ok"
    assert payload["external_id"] == "youtube-private-1"
    assert "youtube-publisher" in " ".join(seen["args"])
    assert secret not in output + json.dumps(seen, default=str)


def test_internal_youtube_execute_rejects_public_visibility(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_PLATFORM_CREDENTIAL", '{"accessToken":"token"}')
    video = tmp_path / "video.mp4"; video.write_bytes(b"sample")
    metadata = tmp_path / "metadata.json"; metadata.write_text('{"title":"Private"}', encoding="utf-8")

    code = main(["upload", "youtube", str(video), "--metadata", str(metadata), "--account", "primary", "--credential-env", "VIDEO_PLATFORM_CREDENTIAL", "--execute", "--public", "--json"])

    assert code == 2
    assert "private" in json.loads(capsys.readouterr().out)["error"]


def test_legacy_upload_digest_remains_compatible_without_account(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"video")
    metadata = tmp_path / "metadata.json"; metadata.write_bytes(b"metadata")

    assert _upload_digest(video, metadata) == hashlib.sha256(b"videometadata").hexdigest()
