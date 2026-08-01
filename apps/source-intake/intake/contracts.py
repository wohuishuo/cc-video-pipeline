"""Immutable Source Intake contracts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SUPPORTED_EXTENSIONS = frozenset({".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"})
PLATFORM_HOSTS = {
    "youtube": ("youtube.com", "youtu.be"),
    "bilibili": ("bilibili.com", "b23.tv"),
    "douyin": ("douyin.com",),
    "tiktok": ("tiktok.com",),
}


class IntakeError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def classify_url(value: str) -> str:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        raise IntakeError("UNSUPPORTED_SOURCE", "source URL must use HTTPS")
    for platform, suffixes in PLATFORM_HOSTS.items():
        if any(host == suffix or host.endswith("." + suffix) for suffix in suffixes):
            return platform
    raise IntakeError("UNSUPPORTED_SOURCE", f"unsupported source host: {host}")


@dataclass(frozen=True)
class SourceSpec:
    kind: str
    value: str
    platform: str | None = None
    max_height: int = 1080
    transport_key: str | None = None

    @classmethod
    def folder(cls, value: str | Path) -> "SourceSpec":
        path = Path(value).resolve()
        if not path.is_dir():
            raise IntakeError("SOURCE_NOT_FOUND", f"folder does not exist: {path}")
        return cls("folder", str(path))

    @classmethod
    def url(
        cls, value: str, *, max_height: int = 1080, transport_key: str | None = None
    ) -> "SourceSpec":
        platform = classify_url(value)
        if max_height < 144:
            raise IntakeError("UNSUPPORTED_SOURCE", "max height must be at least 144")
        return cls("url", value, platform, max_height, transport_key)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind, "value": self.value}
        if self.platform:
            result["platform"] = self.platform
            result["maxHeight"] = self.max_height
        if self.transport_key:
            result["transportKey"] = self.transport_key
        return result


@dataclass(frozen=True)
class MediaEntry:
    id: str
    path: str
    size: int
    extension: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "path": self.path, "size": self.size, "extension": self.extension}


@dataclass(frozen=True)
class SourceManifest:
    source_kind: str
    source: dict[str, Any]
    media: tuple[MediaEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "sourceKind": self.source_kind,
            "source": self.source,
            "media": [entry.to_dict() for entry in self.media],
        }

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()
