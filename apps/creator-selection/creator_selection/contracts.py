"""Immutable contracts for selecting an exact subset of a Creator Manifest."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit


PLATFORM_HOSTS = {
    "youtube": ("youtube.com", "youtu.be"),
    "bilibili": ("bilibili.com", "b23.tv"),
    "douyin": ("douyin.com",),
    "tiktok": ("tiktok.com",),
}


class SelectionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_platform_url(value: str, platform: str) -> bool:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(
        host == suffix or host.endswith("." + suffix)
        for suffix in PLATFORM_HOSTS[platform]
    )


@dataclass(frozen=True)
class SelectionSpec:
    creator_manifest: Path
    creator_manifest_sha256: str
    platform: str
    creator_id: str | None
    creator_name: str | None
    selected_item_ids: tuple[str, ...]
    items: tuple[dict[str, Any], ...]

    @classmethod
    def load(cls, path: Path, selected_ids: Sequence[str]) -> "SelectionSpec":
        resolved = Path(path).resolve()
        try:
            raw = resolved.read_bytes()
            value = json.loads(raw.decode("utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SelectionError("INVALID_CREATOR_MANIFEST", "Creator Manifest must be readable JSON") from error
        if not isinstance(value, dict) or value.get("schemaVersion") != 1:
            raise SelectionError("INVALID_CREATOR_MANIFEST", "Creator Manifest schemaVersion must be 1")
        platform = value.get("platform")
        rows = value.get("items")
        if platform not in PLATFORM_HOSTS or not isinstance(rows, list) or not rows:
            raise SelectionError("INVALID_CREATOR_MANIFEST", "Creator Manifest requires a supported platform and items")
        normalized_ids = tuple(str(item).strip() for item in selected_ids)
        if not normalized_ids or any(not item for item in normalized_ids):
            raise SelectionError("EMPTY_SELECTION", "at least one video ID must be selected")
        if len(set(normalized_ids)) != len(normalized_ids):
            raise SelectionError("DUPLICATE_SELECTION", "selected video IDs must be unique")

        source_items: list[dict[str, Any]] = []
        source_ids: set[str] = set()
        for expected_ordinal, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                raise SelectionError("INVALID_CREATOR_MANIFEST", "creator item must be an object")
            identity = row.get("id")
            url = row.get("url")
            title = row.get("title")
            published_at = row.get("publishedAt")
            if (
                row.get("ordinal") != expected_ordinal
                or not isinstance(identity, str)
                or not identity.strip()
                or identity in source_ids
                or not isinstance(url, str)
                or not _valid_platform_url(url, platform)
                or not isinstance(title, str)
                or not title.strip()
                or published_at is not None
                and (isinstance(published_at, bool) or not isinstance(published_at, int))
            ):
                raise SelectionError("INVALID_CREATOR_MANIFEST", "creator item contract is invalid")
            source_ids.add(identity)
            source_items.append(
                {"id": identity, "url": url, "title": title, "publishedAt": published_at}
            )
        unknown = [identity for identity in normalized_ids if identity not in source_ids]
        if unknown:
            raise SelectionError("UNKNOWN_VIDEO_ID", f"unknown selected video ID: {unknown[0]}")
        wanted = set(normalized_ids)
        selected = tuple(item for item in source_items if item["id"] in wanted)
        creator = value.get("creator") if isinstance(value.get("creator"), dict) else {}
        return cls(
            resolved,
            hashlib.sha256(raw).hexdigest(),
            platform,
            str(creator.get("id")).strip() if creator.get("id") is not None else None,
            str(creator.get("name")).strip() if creator.get("name") is not None else None,
            tuple(item["id"] for item in selected),
            selected,
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json(
                {
                    "schemaVersion": 1,
                    "creatorManifestSha256": self.creator_manifest_sha256,
                    "selectedItemIds": self.selected_item_ids,
                }
            ).encode("utf-8")
        ).hexdigest()

    def to_manifest(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "creatorManifest": str(self.creator_manifest),
            "creatorManifestSha256": self.creator_manifest_sha256,
            "platform": self.platform,
            "creator": {"id": self.creator_id, "name": self.creator_name},
            "selectedItemIds": list(self.selected_item_ids),
            "items": [
                {"ordinal": ordinal, **item}
                for ordinal, item in enumerate(self.items, 1)
            ],
        }
