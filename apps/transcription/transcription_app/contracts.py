"""Versioned immutable contracts for serial transcription."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


class TranscriptionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise TranscriptionError("INVALID_CONTRACT", f"{label} must be a lowercase SHA-256")


@dataclass(frozen=True)
class SourceMedia:
    id: str
    path: str
    size: int
    extension: str


@dataclass(frozen=True)
class SourceManifestInput:
    path: Path
    sha256: str
    source_kind: str
    source: dict[str, Any]
    media: tuple[SourceMedia, ...]


def load_source_manifest(path: str | Path) -> SourceManifestInput:
    manifest_path = Path(path).resolve()
    if not manifest_path.is_file():
        raise TranscriptionError("SOURCE_MANIFEST_MISSING", f"source manifest missing: {manifest_path}")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise TranscriptionError("INVALID_SOURCE_MANIFEST", f"invalid source manifest: {error}") from error
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise TranscriptionError("INVALID_SOURCE_MANIFEST", "source manifest schemaVersion must be 1")
    if value.get("sourceKind") not in {"folder", "url"} or not isinstance(value.get("source"), dict):
        raise TranscriptionError("INVALID_SOURCE_MANIFEST", "source manifest owner fields are invalid")
    rows = value.get("media")
    if not isinstance(rows, list) or not rows:
        raise TranscriptionError("EMPTY_SOURCE", "source manifest requires media")
    media: list[SourceMedia] = []
    identities: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TranscriptionError("INVALID_SOURCE_MANIFEST", f"media row {index} must be an object")
        identifier = row.get("id")
        raw_path = row.get("path")
        size = row.get("size")
        extension = row.get("extension")
        if not isinstance(identifier, str) or not identifier.strip():
            raise TranscriptionError("INVALID_SOURCE_MANIFEST", f"media row {index} has invalid ID")
        if identifier in identities:
            raise TranscriptionError("INVALID_SOURCE_MANIFEST", f"duplicate media ID: {identifier}")
        if not isinstance(raw_path, str) or not isinstance(size, int) or size <= 0 or not isinstance(extension, str):
            raise TranscriptionError("INVALID_SOURCE_MANIFEST", f"media row {identifier} has invalid fields")
        media_path = Path(raw_path).resolve()
        if not media_path.is_file():
            raise TranscriptionError("SOURCE_MEDIA_MISSING", f"source media missing: {media_path}")
        if media_path.stat().st_size != size:
            raise TranscriptionError("SOURCE_MEDIA_CHANGED", f"source media size mismatch: {media_path}")
        if media_path.suffix.lower() != extension.lower():
            raise TranscriptionError("INVALID_SOURCE_MANIFEST", f"source media extension mismatch: {media_path}")
        identities.add(identifier)
        media.append(SourceMedia(identifier, str(media_path), size, extension.lower()))
    return SourceManifestInput(
        manifest_path,
        sha256_file(manifest_path),
        str(value["sourceKind"]),
        dict(value["source"]),
        tuple(media),
    )


@dataclass(frozen=True)
class Segment:
    id: int
    start: float
    end: float
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or self.id <= 0:
            raise TranscriptionError("INVALID_TRANSCRIPT", "segment ID must be positive")
        if not isinstance(self.start, (int, float)) or float(self.start) < 0:
            raise TranscriptionError("INVALID_TRANSCRIPT", "segment start must be non-negative")
        if not isinstance(self.end, (int, float)) or float(self.end) <= float(self.start):
            raise TranscriptionError("INVALID_TRANSCRIPT", "segment end must follow start")
        if not isinstance(self.text, str) or not self.text.strip():
            raise TranscriptionError("INVALID_TRANSCRIPT", "segment text is required")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "start": float(self.start), "end": float(self.end), "text": self.text}


@dataclass(frozen=True)
class TranscriptDocument:
    media_id: str
    source_path: str
    source_sha256: str
    detected_language: str
    segments: tuple[Segment, ...]

    def __post_init__(self) -> None:
        if not self.media_id or not Path(self.source_path).is_file():
            raise TranscriptionError("INVALID_TRANSCRIPT", "transcript source is invalid")
        _digest(self.source_sha256, "sourceSha256")
        if not self.detected_language.strip() or not self.segments:
            raise TranscriptionError("INVALID_TRANSCRIPT", "language and segments are required")
        if [segment.id for segment in self.segments] != list(range(1, len(self.segments) + 1)):
            raise TranscriptionError("INVALID_TRANSCRIPT", "segments require ordered unique IDs")
        if any(right.start < left.start for left, right in zip(self.segments, self.segments[1:])):
            raise TranscriptionError("INVALID_TRANSCRIPT", "segments require ordered unique timing")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "source": {
                "mediaId": self.media_id,
                "path": str(Path(self.source_path).resolve()),
                "sha256": self.source_sha256,
            },
            "detectedLanguage": self.detected_language,
            "segments": [segment.to_dict() for segment in self.segments],
        }


@dataclass(frozen=True)
class TranscriptArtifact:
    media_id: str
    source_path: str
    source_sha256: str
    transcript_path: str
    transcript_sha256: str
    srt_path: str
    srt_sha256: str
    detected_language: str
    segment_count: int

    def __post_init__(self) -> None:
        if not self.media_id or self.segment_count <= 0 or not self.detected_language.strip():
            raise TranscriptionError("INVALID_TRANSCRIPT_MANIFEST", "transcript artifact fields are invalid")
        for digest, label in (
            (self.source_sha256, "sourceSha256"),
            (self.transcript_sha256, "transcriptSha256"),
            (self.srt_sha256, "srtSha256"),
        ):
            _digest(digest, label)
        for path, expected, label in (
            (self.source_path, self.source_sha256, "source"),
            (self.transcript_path, self.transcript_sha256, "transcript"),
            (self.srt_path, self.srt_sha256, "srt"),
        ):
            resolved = Path(path).resolve()
            if not resolved.is_file() or sha256_file(resolved) != expected:
                raise TranscriptionError("INVALID_TRANSCRIPT_MANIFEST", f"{label} artifact does not match")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mediaId": self.media_id,
            "sourcePath": str(Path(self.source_path).resolve()),
            "sourceSha256": self.source_sha256,
            "transcriptPath": str(Path(self.transcript_path).resolve()),
            "transcriptSha256": self.transcript_sha256,
            "srtPath": str(Path(self.srt_path).resolve()),
            "srtSha256": self.srt_sha256,
            "detectedLanguage": self.detected_language,
            "segmentCount": self.segment_count,
        }


@dataclass(frozen=True)
class TranscriptManifest:
    source_manifest: str
    source_manifest_sha256: str
    expected_media_ids: tuple[str, ...]
    transcripts: tuple[TranscriptArtifact, ...]

    def __post_init__(self) -> None:
        source = Path(self.source_manifest).resolve()
        _digest(self.source_manifest_sha256, "sourceManifestSha256")
        if not source.is_file() or sha256_file(source) != self.source_manifest_sha256:
            raise TranscriptionError("INVALID_TRANSCRIPT_MANIFEST", "source manifest fingerprint mismatch")
        if not self.expected_media_ids or len(set(self.expected_media_ids)) != len(self.expected_media_ids):
            raise TranscriptionError("INVALID_TRANSCRIPT_MANIFEST", "expected media IDs are invalid")
        if tuple(row.media_id for row in self.transcripts) != self.expected_media_ids:
            raise TranscriptionError("INVALID_TRANSCRIPT_MANIFEST", "transcript manifest requires exact source coverage")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "sourceManifest": str(Path(self.source_manifest).resolve()),
            "sourceManifestSha256": self.source_manifest_sha256,
            "expectedMediaIds": list(self.expected_media_ids),
            "transcripts": [row.to_dict() for row in self.transcripts],
        }
