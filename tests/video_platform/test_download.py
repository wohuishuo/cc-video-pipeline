import hashlib
import json
from pathlib import Path

import pytest

from video_platform.download import DownloadRequest, YtDlpDownloader, extract_download_metadata, fallback_heights
from video_platform.models import Platform
from video_platform.platforms import detect_platform


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://www.youtube.com/watch?v=x", Platform.YOUTUBE),
        ("https://youtu.be/x", Platform.YOUTUBE),
        ("https://www.bilibili.com/video/BV1x", Platform.BILIBILI),
        ("https://b23.tv/abc", Platform.BILIBILI),
        ("https://www.douyin.com/video/1", Platform.DOUYIN),
        ("https://v.douyin.com/abc", Platform.DOUYIN),
        ("https://www.tiktok.com/@a/video/1", Platform.TIKTOK),
    ],
)
def test_detect_platform_rejects_wrong_adapter_routing(url, platform):
    assert detect_platform(url) is platform


def test_detect_platform_rejects_unsupported_hosts():
    with pytest.raises(ValueError, match="Unsupported"):
        detect_platform("https://example.com/video/1")


def test_download_args_cap_height_without_requiring_cookie(tmp_path):
    request = DownloadRequest(Platform.YOUTUBE, "https://youtu.be/x", tmp_path, 1080)
    args = YtDlpDownloader().build_args(request)
    joined = " ".join(args)
    assert "height<=1080" in joined
    assert "--cookies" not in args
    assert str(tmp_path.resolve()) in joined
    assert "--write-thumbnail" in args
    assert args[args.index("--convert-thumbnails") + 1] == "jpg"


def test_extract_download_metadata_preserves_publishable_source_facts(tmp_path):
    media = tmp_path / "Useful title [abc].mp4"
    media.write_bytes(b"video")
    info = tmp_path / "Useful title [abc].info.json"
    info.write_text(json.dumps({
        "id": "abc",
        "title": "Useful title",
        "description": "A useful description",
        "tags": ["one", "two", 3, ""],
        "webpage_url": "https://youtu.be/abc",
        "uploader": "Creator",
        "thumbnail": "https://example.invalid/remote.jpg",
        "cookies": "must-not-leak",
    }), encoding="utf-8")
    thumbnail = tmp_path / "Useful title [abc].jpg"
    thumbnail.write_bytes(b"image")

    metadata = extract_download_metadata(media)

    assert metadata["title"] == "Useful title"
    assert metadata["description"] == "A useful description"
    assert metadata["tags"] == ["one", "two"]
    assert metadata["sourceUrl"] == "https://youtu.be/abc"
    assert metadata["uploader"] == "Creator"
    assert metadata["info"]["path"] == str(info.resolve())
    assert metadata["info"]["sha256"] == hashlib.sha256(info.read_bytes()).hexdigest()
    assert metadata["thumbnail"] == {
        "path": str(thumbnail.resolve()),
        "sha256": hashlib.sha256(thumbnail.read_bytes()).hexdigest(),
        "size": len(b"image"),
    }
    assert "cookies" not in metadata


def test_extract_download_metadata_is_optional_for_older_downloads(tmp_path):
    media = tmp_path / "legacy.mp4"
    media.write_bytes(b"video")

    assert extract_download_metadata(media) == {}


def test_download_args_add_explicit_cookie_file(tmp_path):
    cookie = tmp_path / "cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    request = DownloadRequest(Platform.BILIBILI, "https://b23.tv/x", tmp_path, 1080, cookie)
    args = YtDlpDownloader().build_args(request)
    assert args[args.index("--cookies") + 1] == str(cookie.resolve())


def test_request_rejects_platform_url_mismatch(tmp_path):
    with pytest.raises(ValueError, match="belongs to"):
        DownloadRequest(Platform.TIKTOK, "https://youtube.com/watch?v=x", tmp_path)


def test_bilibili_uses_native_chunked_retries_instead_of_external_downloader(tmp_path):
    request = DownloadRequest(Platform.BILIBILI, "https://www.bilibili.com/video/BV1x", tmp_path)
    args = YtDlpDownloader().build_args(request)
    assert args[args.index("--http-chunk-size") + 1] == "10M"
    assert args[args.index("--concurrent-fragments") + 1] == "16"
    assert "--downloader" not in args


def test_quality_fallback_never_exceeds_request_and_reaches_360p():
    assert fallback_heights(1080) == (1080, 720, 480, 360)
    assert fallback_heights(720) == (720, 480, 360)
