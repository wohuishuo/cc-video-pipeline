"""Immutable public contracts for Publication Batch planning."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


PLATFORMS = ("youtube", "bilibili", "douyin", "tiktok")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TOKENS = ("{media_id}", "{language}", "{filename}")
LOCALIZATION_FIELDS = {
    "schemaVersion",
    "sourceManifest",
    "sourceManifestSha256",
    "translationManifest",
    "translationManifestSha256",
    "voiceManifest",
    "voiceManifestSha256",
    "sourceVolume",
    "targetLanguages",
    "expectedMediaIds",
    "derivatives",
}
DERIVATIVE_FIELDS = {
    "targetLanguage",
    "mediaId",
    "path",
    "sha256",
    "size",
    "duration",
    "width",
    "height",
    "videoCodec",
    "audioCodec",
}


class BatchContractError(ValueError):
    """The supplied batch input does not satisfy the public contract."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path, label: str) -> tuple[Path, dict[str, Any]]:
    resolved = Path(path).resolve()
    try:
        value = json.loads(resolved.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise BatchContractError(f"{label} must be readable JSON") from error
    if not isinstance(value, dict):
        raise BatchContractError(f"{label} must be a JSON object")
    return resolved, value


def _verify_lineage(path_value: Any, sha_value: Any, label: str) -> tuple[Path, str]:
    if not isinstance(path_value, str) or not isinstance(sha_value, str) or SHA256.fullmatch(sha_value) is None:
        raise BatchContractError(f"{label} lineage is invalid")
    path = Path(path_value).resolve()
    if not path.is_file() or sha256_file(path) != sha_value:
        raise BatchContractError(f"{label} fingerprint conflict")
    return path, sha_value


@dataclass(frozen=True)
class Derivative:
    ordinal: int
    target_language: str
    media_id: str
    path: Path
    sha256: str
    size: int
    duration: float
    width: int
    height: int
    video_codec: str
    audio_codec: str

    @property
    def identity(self) -> str:
        return f"{self.target_language}:{self.media_id}"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "targetLanguage": self.target_language,
            "mediaId": self.media_id,
            "path": str(self.path),
            "sha256": self.sha256,
            "size": self.size,
        }


@dataclass(frozen=True, repr=False)
class LocalizationInput:
    manifest_path: Path
    manifest_sha256: str
    source_manifest: Path
    source_manifest_sha256: str
    translation_manifest: Path
    translation_manifest_sha256: str
    voice_manifest: Path
    voice_manifest_sha256: str
    target_languages: tuple[str, ...]
    expected_media_ids: tuple[str, ...]
    derivatives: tuple[Derivative, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "localizationManifest": str(self.manifest_path),
            "localizationManifestSha256": self.manifest_sha256,
            "sourceManifestSha256": self.source_manifest_sha256,
            "translationManifestSha256": self.translation_manifest_sha256,
            "voiceManifestSha256": self.voice_manifest_sha256,
            "targetLanguages": list(self.target_languages),
            "expectedMediaIds": list(self.expected_media_ids),
        }

    def __repr__(self) -> str:
        return f"LocalizationInput(derivative_count={len(self.derivatives)})"


def load_localization_manifest(path: str | Path) -> LocalizationInput:
    manifest_path, value = _load_json(Path(path), "Localization Manifest")
    if set(value) != LOCALIZATION_FIELDS or value.get("schemaVersion") != 1:
        raise BatchContractError("unsupported or malformed Localization Manifest schema")
    source_path, source_sha = _verify_lineage(value["sourceManifest"], value["sourceManifestSha256"], "Source Manifest")
    translation_path, translation_sha = _verify_lineage(
        value["translationManifest"], value["translationManifestSha256"], "Translation Manifest"
    )
    voice_path, voice_sha = _verify_lineage(value["voiceManifest"], value["voiceManifestSha256"], "Voice Manifest")
    languages = value.get("targetLanguages")
    media_ids = value.get("expectedMediaIds")
    rows = value.get("derivatives")
    if (
        not isinstance(languages, list)
        or not languages
        or len(set(languages)) != len(languages)
        or not all(isinstance(item, str) and item.strip() for item in languages)
        or not isinstance(media_ids, list)
        or not media_ids
        or len(set(media_ids)) != len(media_ids)
        or not all(isinstance(item, str) and item.strip() for item in media_ids)
        or not isinstance(rows, list)
        or not rows
    ):
        raise BatchContractError("Localization Manifest coverage is invalid")
    expected = [(language, media_id) for language in languages for media_id in media_ids]
    derivatives: list[Derivative] = []
    try:
        for ordinal, row in enumerate(rows, 1):
            if not isinstance(row, dict) or set(row) != DERIVATIVE_FIELDS:
                raise BatchContractError("localized derivative schema is invalid")
            language = row["targetLanguage"]
            media_id = row["mediaId"]
            derivative_path = Path(row["path"]).resolve()
            derivative_sha = row["sha256"]
            size = row["size"]
            duration = row["duration"]
            width = row["width"]
            height = row["height"]
            if (
                not isinstance(language, str)
                or not isinstance(media_id, str)
                or not isinstance(derivative_sha, str)
                or SHA256.fullmatch(derivative_sha) is None
                or isinstance(size, bool)
                or not isinstance(size, int)
                or size <= 0
                or isinstance(duration, bool)
                or not isinstance(duration, (int, float))
                or float(duration) <= 0
                or isinstance(width, bool)
                or not isinstance(width, int)
                or width <= 0
                or isinstance(height, bool)
                or not isinstance(height, int)
                or height <= 0
                or not isinstance(row["videoCodec"], str)
                or not row["videoCodec"].strip()
                or not isinstance(row["audioCodec"], str)
                or not row["audioCodec"].strip()
            ):
                raise BatchContractError("localized derivative fields are invalid")
            if not derivative_path.is_file() or derivative_path.stat().st_size != size or sha256_file(derivative_path) != derivative_sha:
                raise BatchContractError("localized derivative fingerprint conflict")
            derivatives.append(
                Derivative(
                    ordinal,
                    language,
                    media_id,
                    derivative_path,
                    derivative_sha,
                    size,
                    float(duration),
                    width,
                    height,
                    row["videoCodec"].strip(),
                    row["audioCodec"].strip(),
                )
            )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, BatchContractError):
            raise
        raise BatchContractError("localized derivative is malformed") from error
    actual = [(row.target_language, row.media_id) for row in derivatives]
    if actual != expected:
        raise BatchContractError("localized derivative coverage or order is invalid")
    return LocalizationInput(
        manifest_path,
        sha256_file(manifest_path),
        source_path,
        source_sha,
        translation_path,
        translation_sha,
        voice_path,
        voice_sha,
        tuple(languages),
        tuple(media_ids),
        tuple(derivatives),
    )


def _validate_template_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BatchContractError(f"metadata {field} must be a non-empty string")
    remainder = value
    for token in TOKENS:
        remainder = remainder.replace(token, "")
    if "{" in remainder or "}" in remainder:
        raise BatchContractError(f"unsupported metadata token in {field}")
    return value.strip()


@dataclass(frozen=True, repr=False)
class MetadataTemplate:
    path: Path
    sha256: str
    title: str
    description: str | None
    tags: tuple[str, ...]

    def __repr__(self) -> str:
        return f"MetadataTemplate(path={str(self.path)!r}, tag_count={len(self.tags)})"


def load_metadata_template(path: str | Path) -> MetadataTemplate:
    resolved, value = _load_json(Path(path), "Metadata template")
    if not set(value).issubset({"title", "description", "tags"}) or "title" not in value:
        raise BatchContractError("metadata template contains unsupported fields")
    title = _validate_template_text(value["title"], "title")
    description_value = value.get("description")
    description = None if description_value is None else _validate_template_text(description_value, "description")
    tags_value = value.get("tags", [])
    if not isinstance(tags_value, list) or not all(isinstance(item, str) and item.strip() for item in tags_value):
        raise BatchContractError("metadata tags must be a list of non-empty strings")
    tags = tuple(_validate_template_text(item, "tag") for item in tags_value)
    return MetadataTemplate(resolved, sha256_file(resolved), title, description, tags)


def _render_text(value: str, derivative: Derivative) -> str:
    replacements = {
        "{media_id}": derivative.media_id,
        "{language}": derivative.target_language,
        "{filename}": derivative.path.stem,
    }
    rendered = value
    for token, replacement in replacements.items():
        rendered = rendered.replace(token, replacement)
    return rendered


def render_metadata(template: MetadataTemplate, derivative: Derivative) -> dict[str, Any]:
    value: dict[str, Any] = {"title": _render_text(template.title, derivative)}
    if template.description is not None:
        value["description"] = _render_text(template.description, derivative)
    if template.tags:
        value["tags"] = [_render_text(item, derivative) for item in template.tags]
    return value


@dataclass(frozen=True, repr=False)
class BatchPolicy:
    targets: tuple[tuple[str, str], ...]
    credentials: tuple[tuple[str, str], ...]

    @classmethod
    def create(
        cls,
        targets: Sequence[tuple[str, str]],
        credentials: Mapping[str, str] | None = None,
    ) -> "BatchPolicy":
        rows: list[tuple[str, str]] = []
        for row in targets:
            if not isinstance(row, (tuple, list)) or len(row) != 2:
                raise BatchContractError("publication targets must contain platform/account pairs")
            platform, account = row
            if platform not in PLATFORMS or not isinstance(account, str) or not account.strip() or len(account.strip()) > 128:
                raise BatchContractError("publication target is invalid")
            rows.append((platform, account.strip()))
        if not rows or len({platform for platform, _account in rows}) != len(rows):
            raise BatchContractError("publication targets must be non-empty and unique by platform")
        if credentials is not None and not isinstance(credentials, Mapping):
            raise BatchContractError("credentials must map platform to credential ID")
        credential_rows: list[tuple[str, str]] = []
        target_platforms = {platform for platform, _account in rows}
        for platform, credential_id in (credentials or {}).items():
            if platform not in target_platforms or not isinstance(credential_id, str) or IDENTIFIER.fullmatch(credential_id) is None:
                raise BatchContractError("credential reference is invalid or has no matching target")
            credential_rows.append((platform, credential_id))
        credential_rows.sort(key=lambda row: next(index for index, target in enumerate(rows) if target[0] == row[0]))
        return cls(tuple(rows), tuple(credential_rows))

    def to_public_dict(self) -> dict[str, Any]:
        credentials = dict(self.credentials)
        targets = []
        for platform, account in self.targets:
            row = {"platform": platform, "account": account}
            if platform in credentials:
                row["credentialId"] = credentials[platform]
            targets.append(row)
        return {"targets": targets, "public": False}

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(self.to_public_dict()).encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return f"BatchPolicy(platforms={tuple(platform for platform, _account in self.targets)!r})"
