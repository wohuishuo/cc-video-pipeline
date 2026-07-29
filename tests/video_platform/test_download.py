from pathlib import Path

import pytest

from video_platform.download import DownloadRequest, YtDlpDownloader
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


def test_download_args_add_explicit_cookie_file(tmp_path):
    cookie = tmp_path / "cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    request = DownloadRequest(Platform.BILIBILI, "https://b23.tv/x", tmp_path, 1080, cookie)
    args = YtDlpDownloader().build_args(request)
    assert args[args.index("--cookies") + 1] == str(cookie.resolve())


def test_request_rejects_platform_url_mismatch(tmp_path):
    with pytest.raises(ValueError, match="belongs to"):
        DownloadRequest(Platform.TIKTOK, "https://youtube.com/watch?v=x", tmp_path)
