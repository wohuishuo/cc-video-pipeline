"""Idempotent public operation for one private YouTube upload."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from .client import UploadOutcome, YouTubeResumableClient
from .contracts import CredentialError, MetadataError, YouTubeCredential, load_metadata


@dataclass(frozen=True)
class PublishResult:
    result_class: str
    receipt_path: Path
    external_id: str | None = None
    error: str | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)


class YouTubePublishOperation:
    def __init__(self, publisher: YouTubeResumableClient | Any | None = None):
        self.publisher = publisher or YouTubeResumableClient()

    def execute(self, video: Path, metadata_path: Path, output_dir: Path, operation_id: str, credential_json: str) -> PublishResult:
        video = Path(video).resolve(); metadata_path = Path(metadata_path).resolve(); output = Path(output_dir).resolve()
        receipt = output / "youtube-upload-receipt.json"
        if not operation_id.strip() or len(operation_id) > 200:
            return PublishResult("REJECTED_MALFORMED", receipt, error="operation ID is required")
        if not video.is_file() or not metadata_path.is_file():
            return PublishResult("REJECTED_MALFORMED", receipt, error="video and metadata files are required")
        video_sha = _sha256(video); metadata_sha = _sha256(metadata_path)
        fingerprint = hashlib.sha256(f"{video_sha}\0{metadata_sha}\0private\0youtube-publisher@1".encode()).hexdigest()
        prior = self._read(receipt)
        if receipt.is_file() and prior is None:
            return PublishResult("REJECTED_CONFLICT", receipt, error="existing upload receipt is unreadable; automatic replay is fenced")
        if prior:
            if prior.get("operationId") != operation_id or prior.get("inputFingerprint") != fingerprint:
                return PublishResult("REJECTED_CONFLICT", receipt, error="operation input conflicts with the existing receipt")
            if prior.get("resultClass") == "COMPLETED" and isinstance(prior.get("externalId"), str) and prior["externalId"]:
                return PublishResult("DUPLICATE_COMPLETED", receipt, prior["externalId"])
            if prior.get("resultClass") == "COMPLETED":
                return PublishResult("REJECTED_CONFLICT", receipt, error="completed receipt lacks external identity; automatic replay is fenced")
            if prior.get("resultClass") == "UNKNOWN":
                return PublishResult("REJECTED_UNKNOWN", receipt, error="previous upload outcome is unknown; automatic replay is fenced")
        try:
            credential = YouTubeCredential.parse(credential_json)
            metadata = load_metadata(metadata_path)
        except (CredentialError, MetadataError) as error:
            return PublishResult("REJECTED_MALFORMED", receipt, error=str(error))
        outcome: UploadOutcome = self.publisher.upload(video, metadata, credential)
        payload = {
            "schemaVersion": 1,
            "operationId": operation_id,
            "inputFingerprint": fingerprint,
            "videoSha256": video_sha,
            "metadataSha256": metadata_sha,
            "resultClass": outcome.result_class,
            "externalId": outcome.external_id,
            "facts": outcome.facts,
            "error": outcome.error,
        }
        _atomic(receipt, payload)
        return PublishResult(outcome.result_class, receipt, outcome.external_id, outcome.error)

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None
