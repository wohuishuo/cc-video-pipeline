from __future__ import annotations

from urllib.parse import urlparse

from .models import Platform

_HOSTS = {
    Platform.YOUTUBE: ("youtube.com", "youtu.be"),
    Platform.BILIBILI: ("bilibili.com", "b23.tv"),
    Platform.DOUYIN: ("douyin.com",),
    Platform.TIKTOK: ("tiktok.com",),
}


def detect_platform(url: str) -> Platform:
    host = (urlparse(url).hostname or "").lower()
    for platform, suffixes in _HOSTS.items():
        if any(host == suffix or host.endswith("." + suffix) for suffix in suffixes):
            return platform
    raise ValueError(f"Unsupported video URL host: {host or url}")
