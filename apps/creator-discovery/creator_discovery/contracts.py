"""Public contracts for creator profile enumeration."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


class DiscoveryError(ValueError):
    pass


HOSTS = {
    "youtube": ("youtube.com", "youtu.be"),
    "bilibili": ("bilibili.com", "b23.tv"),
    "douyin": ("douyin.com",),
    "tiktok": ("tiktok.com",),
}


def classify_url(value: str) -> str:
    parsed = urlparse(str(value).strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        raise DiscoveryError("profile URL must be HTTPS")
    for platform, suffixes in HOSTS.items():
        if any(host == suffix or host.endswith("." + suffix) for suffix in suffixes):
            return platform
    raise DiscoveryError("unsupported creator profile URL")


@dataclass(frozen=True)
class ProfileSpec:
    url: str
    platform: str
    max_items: int = 0
    cookie_key: str | None = None

    @classmethod
    def from_url(cls, url: str, *, max_items: int = 0, cookie_key: str | None = None):
        if not isinstance(max_items, int) or max_items < 0:
            raise DiscoveryError("max_items must be zero or a positive integer")
        if cookie_key is not None and (not isinstance(cookie_key, str) or len(cookie_key) != 64):
            raise DiscoveryError("invalid authentication material fingerprint")
        normalized = str(url).strip()
        return cls(normalized, classify_url(normalized), max_items, cookie_key)

    def to_public_dict(self):
        return {"url": self.url, "platform": self.platform, "maxItems": self.max_items}


@dataclass(frozen=True)
class CreatorItem:
    id: str
    url: str
    title: str
    published_at: int | None = None

    def __post_init__(self):
        if not self.id.strip() or classify_url(self.url) not in HOSTS or not self.title.strip():
            raise DiscoveryError("invalid creator item")

    def to_dict(self, ordinal: int):
        return {"ordinal": ordinal, "id": self.id, "url": self.url, "title": self.title, "publishedAt": self.published_at}


@dataclass(frozen=True)
class DiscoveryPage:
    creator_id: str | None
    creator_name: str | None
    items: tuple[CreatorItem, ...]
    next_cursor: str | None
    has_more: bool
    source_kind: str = "profile"

    def __post_init__(self):
        if self.source_kind not in {"profile", "video"}:
            raise DiscoveryError("source_kind must be profile or video")
