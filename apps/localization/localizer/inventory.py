"""Resolve corrected Douyin URLs to one immutable local source per video ID."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import urlparse

from .contracts import BatchManifest, JobRecord, sha256_file


class InventoryError(ValueError):
    """The corrected source manifest and local source directory do not agree."""


_URL_ID = re.compile(r"(?:^|/)video/(\d+)(?:/|$)")
_FILENAME_ID = re.compile(r"^\[(\d+)\]")


def _manifest_ids(path: Path) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for line_number, raw_url in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        url = raw_url.strip()
        if not url:
            continue
        match = _URL_ID.search(urlparse(url).path)
        if match is None:
            raise InventoryError(f"invalid manifest URL at line {line_number}: {url}")
        video_id = match.group(1)
        if video_id in seen:
            raise InventoryError(f"duplicate manifest ID: {video_id}")
        seen.add(video_id)
        ids.append(video_id)
    if not ids:
        raise InventoryError("manifest contains no video IDs")
    return ids


def _source_by_id(directory: Path) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for candidate in sorted(directory.iterdir(), key=lambda path: path.name):
        if not candidate.is_file() or candidate.suffix.lower() != ".mp4":
            continue
        match = _FILENAME_ID.match(candidate.name)
        if match is None:
            raise InventoryError(f"source filename does not begin with an ID: {candidate.name}")
        video_id = match.group(1)
        if video_id in sources:
            raise InventoryError(f"duplicate source ID: {video_id}")
        sources[video_id] = candidate
    return sources


def discover_jobs(manifest_path: str | Path, source_directory: str | Path) -> BatchManifest:
    """Return source jobs only when local files exactly cover the URL manifest."""

    manifest = Path(manifest_path)
    directory = Path(source_directory)
    if not manifest.is_file():
        raise InventoryError(f"manifest file does not exist: {manifest}")
    if not directory.is_dir():
        raise InventoryError(f"source directory does not exist: {directory}")

    manifest_ids = _manifest_ids(manifest)
    sources = _source_by_id(directory)
    expected = set(manifest_ids)
    actual = set(sources)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing source IDs: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected source IDs: {', '.join(unexpected)}")
        raise InventoryError("; ".join(details))

    return BatchManifest(
        manifest=str(manifest),
        expected_ids=tuple(manifest_ids),
        jobs=[
            JobRecord(
                id=video_id,
                source=str(sources[video_id]),
                source_sha256=sha256_file(sources[video_id]),
            )
            for video_id in manifest_ids
        ],
    )
