"""Public immutable contracts for creator localization batches."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit


SUPPORTED_LANGUAGES = ("ru-RU", "en-US", "kk-KZ")
PLATFORM_HOSTS = {
    "youtube": ("youtube.com", "youtu.be"),
    "bilibili": ("bilibili.com", "b23.tv"),
    "douyin": ("douyin.com",),
    "tiktok": ("tiktok.com",),
}


class BatchContractError(ValueError):
    """The supplied batch input does not satisfy the public contract."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _platform_for_url(value: str) -> str | None:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        return None
    for platform, suffixes in PLATFORM_HOSTS.items():
        if any(host == suffix or host.endswith("." + suffix) for suffix in suffixes):
            return platform
    return None


@dataclass(frozen=True)
class CreatorItem:
    ordinal: int
    id: str
    url: str
    title: str
    published_at: int | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "publishedAt": self.published_at,
        }


@dataclass(frozen=True, repr=False)
class CreatorSource:
    manifest_path: Path
    manifest_sha256: str
    platform: str
    creator_id: str | None
    creator_name: str | None
    items: tuple[CreatorItem, ...]

    @classmethod
    def load(cls, path: Path) -> "CreatorSource":
        resolved = Path(path).resolve()
        try:
            value = json.loads(resolved.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            raise BatchContractError("Creator Manifest must be readable JSON") from error
        if not isinstance(value, dict) or value.get("schemaVersion") != 1:
            raise BatchContractError("unsupported Creator Manifest schema")
        platform = value.get("platform")
        rows = value.get("items")
        if platform not in PLATFORM_HOSTS or not isinstance(rows, list) or not rows:
            raise BatchContractError("Creator Manifest requires a supported platform and items")
        items: list[CreatorItem] = []
        try:
            for expected_ordinal, row in enumerate(rows, 1):
                ordinal = int(row["ordinal"])
                item_id = str(row["id"]).strip()
                url = str(row["url"]).strip()
                title = str(row["title"]).strip()
                published = row.get("publishedAt")
                if ordinal != expected_ordinal or not item_id or not title:
                    raise BatchContractError("creator items must have contiguous order and identity")
                if _platform_for_url(url) != platform:
                    raise BatchContractError("creator item URL does not match the manifest platform")
                if published is not None and (isinstance(published, bool) or not isinstance(published, int)):
                    raise BatchContractError("creator item publishedAt must be an integer or null")
                items.append(CreatorItem(ordinal, item_id, url, title, published))
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, BatchContractError):
                raise
            raise BatchContractError("creator item is malformed") from error
        if len({item.id for item in items}) != len(items):
            raise BatchContractError("creator item IDs must be unique")
        creator = value.get("creator") if isinstance(value.get("creator"), dict) else {}
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        return cls(
            resolved,
            digest,
            platform,
            str(creator.get("id")).strip() if creator.get("id") is not None else None,
            str(creator.get("name")).strip() if creator.get("name") is not None else None,
            tuple(items),
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "creatorManifest": str(self.manifest_path),
            "creatorManifestSha256": self.manifest_sha256,
            "platform": self.platform,
            "creator": {"id": self.creator_id, "name": self.creator_name},
            "expectedItemIds": [item.id for item in self.items],
        }

    def __repr__(self) -> str:
        return f"CreatorSource(platform={self.platform!r}, item_count={len(self.items)})"


@dataclass(frozen=True, repr=False)
class BatchPolicy:
    target_languages: tuple[str, ...]
    target_voices: Mapping[str, str]
    source_language: str
    asr_model: str
    asr_device: str
    asr_compute_type: str
    translation_model: str
    translation_device: str
    translation_batch_size: int
    source_volume: float
    max_height: int

    @classmethod
    def create(
        cls,
        target_languages: Sequence[str],
        target_voices: Mapping[str, str],
        *,
        source_language: str = "auto",
        asr_model: str = "small",
        asr_device: str = "auto",
        asr_compute_type: str = "default",
        translation_model: str = "facebook/nllb-200-distilled-600M",
        translation_device: str = "auto",
        translation_batch_size: int = 8,
        source_volume: float = 0.12,
        max_height: int = 1080,
    ) -> "BatchPolicy":
        languages = tuple(str(value).strip() for value in target_languages)
        voices = {str(key).strip(): str(value).strip() for key, value in target_voices.items()}
        if not languages or len(set(languages)) != len(languages) or any(value not in SUPPORTED_LANGUAGES for value in languages):
            raise BatchContractError("target languages must be a unique supported list")
        if set(voices) != set(languages) or any(not value for value in voices.values()):
            raise BatchContractError("target voices must exactly cover target languages")
        if isinstance(source_volume, bool) or not 0 <= float(source_volume) <= 1:
            raise BatchContractError("source volume must be between zero and one")
        if isinstance(translation_batch_size, bool) or not 1 <= int(translation_batch_size) <= 64:
            raise BatchContractError("translation batch size must be between 1 and 64")
        if int(max_height) != 1080:
            raise BatchContractError("creator batch downloads are fixed at 1080p maximum")
        if asr_device not in {"auto", "cpu", "cuda"} or translation_device not in {"auto", "cpu", "cuda"}:
            raise BatchContractError("device policy is invalid")
        text_values = (source_language, asr_model, asr_compute_type, translation_model)
        if any(not isinstance(value, str) or not value.strip() for value in text_values):
            raise BatchContractError("model and language policies must not be empty")
        return cls(
            languages,
            voices,
            source_language.strip(),
            asr_model.strip(),
            asr_device,
            asr_compute_type.strip(),
            translation_model.strip(),
            translation_device,
            int(translation_batch_size),
            float(source_volume),
            1080,
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "targetLanguages": list(self.target_languages),
            "targetVoices": {language: self.target_voices[language] for language in self.target_languages},
            "sourceLanguage": self.source_language,
            "asrModel": self.asr_model,
            "asrDevice": self.asr_device,
            "asrComputeType": self.asr_compute_type,
            "translationModel": self.translation_model,
            "translationDevice": self.translation_device,
            "translationBatchSize": self.translation_batch_size,
            "sourceVolume": self.source_volume,
            "maxHeight": self.max_height,
        }

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(_canonical(self.to_public_dict()).encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return f"BatchPolicy(languages={self.target_languages!r}, source_volume={self.source_volume!r})"
