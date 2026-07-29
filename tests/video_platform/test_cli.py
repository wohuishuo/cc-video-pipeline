import json

from video_platform.cli import main


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
