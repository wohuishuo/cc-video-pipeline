"""Versioned contracts for serial transcript translation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


class TranslationError(ValueError):
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
        raise TranslationError("INVALID_CONTRACT", f"{label} must be a lowercase SHA-256")


LANGUAGE_ALIASES = {
    "ru": "ru-RU", "ru-ru": "ru-RU",
    "en": "en-US", "en-us": "en-US",
    "kk": "kk-KZ", "kk-kz": "kk-KZ",
    "zh": "zh-CN", "zh-cn": "zh-CN",
    "es": "es-ES", "es-es": "es-ES",
    "fr": "fr-FR", "fr-fr": "fr-FR",
    "de": "de-DE", "de-de": "de-DE",
    "it": "it-IT", "it-it": "it-IT",
    "pt": "pt-BR", "pt-br": "pt-BR",
    "ja": "ja-JP", "ja-jp": "ja-JP",
    "ko": "ko-KR", "ko-kr": "ko-KR",
    "ar": "ar-SA", "ar-sa": "ar-SA",
    "hi": "hi-IN", "hi-in": "hi-IN",
    "tr": "tr-TR", "tr-tr": "tr-TR",
    "uk": "uk-UA", "uk-ua": "uk-UA",
    "pl": "pl-PL", "pl-pl": "pl-PL",
    "nl": "nl-NL", "nl-nl": "nl-NL",
    "id": "id-ID", "id-id": "id-ID",
    "vi": "vi-VN", "vi-vn": "vi-VN",
    "th": "th-TH", "th-th": "th-TH",
}


def normalize_target_languages(values: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in values:
        if not isinstance(raw, str) or not raw.strip():
            raise TranslationError("INVALID_LANGUAGE", "target language is required")
        language = LANGUAGE_ALIASES.get(raw.strip().lower())
        if language is None:
            raise TranslationError("UNSUPPORTED_LANGUAGE", f"unsupported target language: {raw}")
        if language in normalized:
            raise TranslationError("DUPLICATE_LANGUAGE", f"duplicate target language: {language}")
        normalized.append(language)
    if not normalized:
        raise TranslationError("INVALID_LANGUAGE", "at least one target language is required")
    return tuple(normalized)


@dataclass(frozen=True)
class SourceSegment:
    id: int
    start: float
    end: float
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or self.id <= 0:
            raise TranslationError("INVALID_TRANSCRIPT", "segment ID must be positive")
        if not isinstance(self.start, (int, float)) or float(self.start) < 0:
            raise TranslationError("INVALID_TRANSCRIPT", "segment start must be non-negative")
        if not isinstance(self.end, (int, float)) or float(self.end) <= float(self.start):
            raise TranslationError("INVALID_TRANSCRIPT", "segment end must follow start")
        if not isinstance(self.text, str) or not self.text.strip():
            raise TranslationError("INVALID_TRANSCRIPT", "segment text is required")


@dataclass(frozen=True)
class TranscriptInput:
    media_id: str
    source_path: str
    source_sha256: str
    transcript_path: str
    transcript_sha256: str
    srt_path: str
    srt_sha256: str
    detected_language: str
    segments: tuple[SourceSegment, ...]


@dataclass(frozen=True)
class TranscriptManifestInput:
    path: Path
    sha256: str
    source_manifest: str
    source_manifest_sha256: str
    expected_media_ids: tuple[str, ...]
    transcripts: tuple[TranscriptInput, ...]


def _verified_file(raw_path: Any, expected: Any, label: str) -> Path:
    if not isinstance(raw_path, str) or not isinstance(expected, str):
        raise TranslationError("INVALID_TRANSCRIPT_MANIFEST", f"{label} artifact fields are invalid")
    _digest(expected, f"{label}Sha256")
    path = Path(raw_path).resolve()
    if not path.is_file() or sha256_file(path) != expected:
        raise TranslationError("TRANSCRIPT_FINGERPRINT_CONFLICT", f"{label} artifact fingerprint mismatch")
    return path


def load_transcript_manifest(path: str | Path) -> TranscriptManifestInput:
    manifest_path = Path(path).resolve()
    if not manifest_path.is_file():
        raise TranslationError("TRANSCRIPT_MANIFEST_MISSING", f"transcript manifest missing: {manifest_path}")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise TranslationError("INVALID_TRANSCRIPT_MANIFEST", f"invalid transcript manifest: {error}") from error
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise TranslationError("INVALID_TRANSCRIPT_MANIFEST", "transcript manifest schemaVersion must be 1")
    source_manifest = _verified_file(value.get("sourceManifest"), value.get("sourceManifestSha256"), "sourceManifest")
    expected = value.get("expectedMediaIds")
    rows = value.get("transcripts")
    if not isinstance(expected, list) or not expected or len(set(expected)) != len(expected):
        raise TranslationError("INVALID_TRANSCRIPT_MANIFEST", "expected media IDs are invalid")
    if not isinstance(rows, list) or [row.get("mediaId") if isinstance(row, dict) else None for row in rows] != expected:
        raise TranslationError("INVALID_TRANSCRIPT_MANIFEST", "transcript manifest requires exact media coverage")
    transcripts: list[TranscriptInput] = []
    for row in rows:
        assert isinstance(row, dict)
        source = _verified_file(row.get("sourcePath"), row.get("sourceSha256"), "source")
        transcript_path = _verified_file(row.get("transcriptPath"), row.get("transcriptSha256"), "transcript")
        srt = _verified_file(row.get("srtPath"), row.get("srtSha256"), "srt")
        try:
            document = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
            raw_segments = document["segments"]
            segments = tuple(
                SourceSegment(int(item["id"]), float(item["start"]), float(item["end"]), str(item["text"]))
                for item in raw_segments
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise TranslationError("INVALID_TRANSCRIPT", f"invalid transcript document: {error}") from error
        media_id = str(row.get("mediaId", ""))
        detected_language = str(row.get("detectedLanguage", ""))
        if (
            not media_id
            or document.get("schemaVersion") != 1
            or document.get("source", {}).get("mediaId") != media_id
            or document.get("source", {}).get("sha256") != row.get("sourceSha256")
            or document.get("detectedLanguage") != detected_language
            or len(segments) != int(row.get("segmentCount", 0))
            or [segment.id for segment in segments] != list(range(1, len(segments) + 1))
        ):
            raise TranslationError("INVALID_TRANSCRIPT", f"transcript contract mismatch: {media_id}")
        transcripts.append(
            TranscriptInput(
                media_id,
                str(source),
                str(row["sourceSha256"]),
                str(transcript_path),
                str(row["transcriptSha256"]),
                str(srt),
                str(row["srtSha256"]),
                detected_language,
                segments,
            )
        )
    return TranscriptManifestInput(
        manifest_path,
        sha256_file(manifest_path),
        str(source_manifest),
        str(value["sourceManifestSha256"]),
        tuple(str(item) for item in expected),
        tuple(transcripts),
    )


@dataclass(frozen=True)
class TranslationSegment:
    id: int
    start: float
    end: float
    source_text: str
    translated_text: str

    def __post_init__(self) -> None:
        SourceSegment(self.id, self.start, self.end, self.source_text)
        if not isinstance(self.translated_text, str) or not self.translated_text.strip():
            raise TranslationError("INVALID_TRANSLATION", "translated text is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "start": float(self.start),
            "end": float(self.end),
            "sourceText": self.source_text,
            "translatedText": self.translated_text,
        }


@dataclass(frozen=True)
class TranslationDocument:
    media_id: str
    transcript_path: str
    transcript_sha256: str
    source_language: str
    target_language: str
    review_status: str
    segments: tuple[TranslationSegment, ...]

    def __post_init__(self) -> None:
        _digest(self.transcript_sha256, "transcriptSha256")
        if not Path(self.transcript_path).is_file() or sha256_file(self.transcript_path) != self.transcript_sha256:
            raise TranslationError("INVALID_TRANSLATION", "transcript fingerprint mismatch")
        if not self.media_id or not self.source_language.strip() or self.target_language not in LANGUAGE_ALIASES.values():
            raise TranslationError("INVALID_TRANSLATION", "translation owner fields are invalid")
        if self.review_status not in {"MACHINE", "REVIEWED"}:
            raise TranslationError("INVALID_TRANSLATION", "review status must be MACHINE or REVIEWED")
        if not self.segments or [row.id for row in self.segments] != list(range(1, len(self.segments) + 1)):
            raise TranslationError("INVALID_TRANSLATION", "segments require ordered unique IDs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "source": {
                "mediaId": self.media_id,
                "transcriptPath": str(Path(self.transcript_path).resolve()),
                "transcriptSha256": self.transcript_sha256,
                "language": self.source_language,
            },
            "targetLanguage": self.target_language,
            "reviewStatus": self.review_status,
            "segments": [row.to_dict() for row in self.segments],
        }


@dataclass(frozen=True)
class TranslationArtifact:
    media_id: str
    target_language: str
    translation_path: str
    translation_sha256: str
    srt_path: str
    srt_sha256: str
    review_status: str
    segment_count: int

    def __post_init__(self) -> None:
        if not self.media_id or self.target_language not in LANGUAGE_ALIASES.values() or self.segment_count <= 0:
            raise TranslationError("INVALID_TRANSLATION_MANIFEST", "translation artifact fields are invalid")
        if self.review_status not in {"MACHINE", "REVIEWED"}:
            raise TranslationError("INVALID_TRANSLATION_MANIFEST", "review status is invalid")
        for path, expected, label in (
            (self.translation_path, self.translation_sha256, "translation"),
            (self.srt_path, self.srt_sha256, "srt"),
        ):
            _digest(expected, f"{label}Sha256")
            resolved = Path(path).resolve()
            if not resolved.is_file() or sha256_file(resolved) != expected:
                raise TranslationError("INVALID_TRANSLATION_MANIFEST", f"{label} artifact does not match")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mediaId": self.media_id,
            "targetLanguage": self.target_language,
            "translationPath": str(Path(self.translation_path).resolve()),
            "translationSha256": self.translation_sha256,
            "srtPath": str(Path(self.srt_path).resolve()),
            "srtSha256": self.srt_sha256,
            "reviewStatus": self.review_status,
            "segmentCount": self.segment_count,
        }


@dataclass(frozen=True)
class TranslationManifest:
    transcript_manifest: str
    transcript_manifest_sha256: str
    expected_media_ids: tuple[str, ...]
    target_languages: tuple[str, ...]
    translations: tuple[TranslationArtifact, ...]

    def __post_init__(self) -> None:
        _digest(self.transcript_manifest_sha256, "transcriptManifestSha256")
        path = Path(self.transcript_manifest).resolve()
        if not path.is_file() or sha256_file(path) != self.transcript_manifest_sha256:
            raise TranslationError("INVALID_TRANSLATION_MANIFEST", "transcript manifest fingerprint mismatch")
        normalized = normalize_target_languages(self.target_languages)
        if normalized != self.target_languages or not self.expected_media_ids:
            raise TranslationError("INVALID_TRANSLATION_MANIFEST", "translation manifest owner fields are invalid")
        expected = [(language, media_id) for language in self.target_languages for media_id in self.expected_media_ids]
        actual = [(row.target_language, row.media_id) for row in self.translations]
        if actual != expected:
            raise TranslationError("INVALID_TRANSLATION_MANIFEST", "translation manifest requires exact translation coverage")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "transcriptManifest": str(Path(self.transcript_manifest).resolve()),
            "transcriptManifestSha256": self.transcript_manifest_sha256,
            "expectedMediaIds": list(self.expected_media_ids),
            "targetLanguages": list(self.target_languages),
            "translations": [row.to_dict() for row in self.translations],
        }
