"""Strictly serial, resumable transcript loop."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Protocol

from .contracts import (
    Segment,
    SourceMedia,
    TranscriptArtifact,
    TranscriptDocument,
    TranscriptManifest,
    TranscriptionError,
    canonical_json,
    load_source_manifest,
    sha256_file,
)


@dataclass(frozen=True)
class AdapterTranscript:
    detected_language: str
    segments: tuple[Segment, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.detected_language, str) or not self.detected_language.strip():
            raise TranscriptionError("INVALID_ADAPTER_OUTPUT", "adapter language is required")
        if not self.segments:
            raise TranscriptionError("INVALID_ADAPTER_OUTPUT", "adapter returned no transcript segments")


class TranscriptAdapter(Protocol):
    identity: str

    def transcribe(
        self, media: SourceMedia, language: str, on_log: Callable[[str], None]
    ) -> AdapterTranscript: ...


@dataclass(frozen=True)
class TranscriptLoopResult:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    error: str | None = None


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial")
    partial.write_text(value, encoding="utf-8")
    os.replace(partial, path)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def _srt_time(seconds: float) -> str:
    milliseconds = round(float(seconds) * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole:02},{milliseconds:03}"


def _srt(segments: tuple[Segment, ...]) -> str:
    return "".join(
        f"{row.id}\n{_srt_time(row.start)} --> {_srt_time(row.end)}\n{row.text}\n\n"
        for row in segments
    )


def _artifact_from_dict(value: Any) -> TranscriptArtifact | None:
    if not isinstance(value, dict):
        return None
    try:
        return TranscriptArtifact(
            str(value["mediaId"]),
            str(value["sourcePath"]),
            str(value["sourceSha256"]),
            str(value["transcriptPath"]),
            str(value["transcriptSha256"]),
            str(value["srtPath"]),
            str(value["srtSha256"]),
            str(value["detectedLanguage"]),
            int(value["segmentCount"]),
        )
    except (KeyError, TypeError, ValueError, OSError, TranscriptionError):
        return None


class TranscriptLoop:
    def execute(
        self,
        source_manifest_path: str | Path,
        output_dir: str | Path,
        operation_id: str,
        *,
        language: str,
        adapter: TranscriptAdapter,
        on_log: Callable[[str], None] | None = None,
    ) -> TranscriptLoopResult:
        if not operation_id.strip() or not language.strip() or not adapter.identity.strip():
            raise TranscriptionError("INVALID_COMMAND", "operation, language and adapter are required")
        source = load_source_manifest(source_manifest_path)
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        receipt_path = output / "transcription-receipt.json"
        manifest_path = output / "transcript-manifest.json"
        input_fingerprint = hashlib.sha256(
            canonical_json(
                {
                    "schemaVersion": 1,
                    "sourceManifestSha256": source.sha256,
                    "language": language,
                    "adapter": adapter.identity,
                }
            ).encode("utf-8")
        ).hexdigest()
        log = on_log or (lambda _message: None)
        prior = self._read_receipt(receipt_path)
        if prior and (
            prior.get("operationId") != operation_id
            or prior.get("inputFingerprint") != input_fingerprint
        ):
            return TranscriptLoopResult("REJECTED_CONFLICT", receipt_path, None, "operation input conflict")

        reusable: dict[str, TranscriptArtifact] = {}
        if prior:
            for item in prior.get("items", []):
                if isinstance(item, dict) and item.get("status") == "COMPLETED":
                    artifact = _artifact_from_dict(item.get("artifact"))
                    if artifact is not None:
                        reusable[artifact.media_id] = artifact
            if prior.get("resultClass") == "COMPLETED" and self._manifest_valid(
                manifest_path, prior.get("manifestSha256"), source.sha256
            ):
                return TranscriptLoopResult("DUPLICATE_COMPLETED", receipt_path, manifest_path)

        items: list[dict[str, Any]] = []
        artifacts: list[TranscriptArtifact] = []
        failures: list[str] = []
        for index, media in enumerate(source.media, 1):
            reused = reusable.get(media.id)
            if reused is not None and reused.source_path == media.path:
                artifacts.append(reused)
                items.append({"mediaId": media.id, "status": "COMPLETED", "artifact": reused.to_dict(), "reused": True})
                log(f"[{index}/{len(source.media)}] reused {media.id}")
                self._checkpoint(receipt_path, operation_id, input_fingerprint, adapter.identity, language, items)
                continue
            log(f"[{index}/{len(source.media)}] transcribing {media.id}")
            try:
                source_sha256 = sha256_file(media.path)
                adapted = adapter.transcribe(media, language, log)
                if sha256_file(media.path) != source_sha256:
                    raise TranscriptionError("SOURCE_MEDIA_CHANGED", f"source changed during transcription: {media.path}")
                document = TranscriptDocument(
                    media.id,
                    media.path,
                    source_sha256,
                    adapted.detected_language,
                    adapted.segments,
                )
                item_key = hashlib.sha256(media.id.encode("utf-8")).hexdigest()[:20]
                item_dir = output / "items" / item_key
                transcript_path = item_dir / "transcript.json"
                srt_path = item_dir / "transcript.srt"
                _atomic_json(transcript_path, document.to_dict())
                _atomic_text(srt_path, _srt(document.segments))
                artifact = TranscriptArtifact(
                    media.id,
                    media.path,
                    source_sha256,
                    str(transcript_path),
                    sha256_file(transcript_path),
                    str(srt_path),
                    sha256_file(srt_path),
                    adapted.detected_language,
                    len(adapted.segments),
                )
                artifacts.append(artifact)
                items.append({"mediaId": media.id, "status": "COMPLETED", "artifact": artifact.to_dict(), "reused": False})
            except Exception as error:
                message = f"{type(error).__name__}: {error}"[-2000:]
                failures.append(media.id)
                items.append({"mediaId": media.id, "status": "FAILED", "error": message})
                log(f"[{index}/{len(source.media)}] failed {media.id}: {message}")
            self._checkpoint(receipt_path, operation_id, input_fingerprint, adapter.identity, language, items)

        if failures:
            self._checkpoint(
                receipt_path,
                operation_id,
                input_fingerprint,
                adapter.identity,
                language,
                items,
                result_class="FAILED",
                error=f"{len(failures)} media item(s) failed",
            )
            if manifest_path.exists():
                manifest_path.unlink()
            return TranscriptLoopResult("FAILED", receipt_path, None, f"{len(failures)} media item(s) failed")

        manifest = TranscriptManifest(
            str(source.path),
            source.sha256,
            tuple(media.id for media in source.media),
            tuple(artifacts),
        )
        _atomic_json(manifest_path, manifest.to_dict())
        manifest_sha256 = sha256_file(manifest_path)
        self._checkpoint(
            receipt_path,
            operation_id,
            input_fingerprint,
            adapter.identity,
            language,
            items,
            result_class="COMPLETED",
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
        )
        return TranscriptLoopResult("COMPLETED", receipt_path, manifest_path)

    @staticmethod
    def _read_receipt(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _checkpoint(
        path: Path,
        operation_id: str,
        input_fingerprint: str,
        adapter: str,
        language: str,
        items: list[dict[str, Any]],
        *,
        result_class: str = "RUNNING",
        error: str | None = None,
        manifest_path: Path | None = None,
        manifest_sha256: str | None = None,
    ) -> None:
        _atomic_json(
            path,
            {
                "schemaVersion": 1,
                "operationId": operation_id,
                "inputFingerprint": input_fingerprint,
                "adapter": adapter,
                "language": language,
                "resultClass": result_class,
                "items": items,
                "manifest": str(manifest_path) if manifest_path else None,
                "manifestSha256": manifest_sha256,
                "error": error,
            },
        )

    @staticmethod
    def _manifest_valid(path: Path, expected_sha256: Any, source_sha256: str) -> bool:
        if not path.is_file() or not isinstance(expected_sha256, str) or sha256_file(path) != expected_sha256:
            return False
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("schemaVersion") != 1 or value.get("sourceManifestSha256") != source_sha256:
                return False
            return bool(value.get("transcripts")) and all(
                _artifact_from_dict(row) is not None for row in value["transcripts"]
            )
        except (OSError, TypeError, json.JSONDecodeError):
            return False
