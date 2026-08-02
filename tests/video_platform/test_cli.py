import json

from video_platform.cli import _json_text, main


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
