"""Strictly serial, resumable multilingual translation loop."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from .contracts import (
    TranslationArtifact,
    TranslationDocument,
    TranslationError,
    TranslationManifest,
    TranslationSegment,
    canonical_json,
    load_transcript_manifest,
    normalize_target_languages,
    sha256_file,
)


class TranslationAdapter(Protocol):
    identity: str

    def translate(
        self,
        texts: tuple[str, ...],
        source_language: str,
        target_language: str,
        on_log: Callable[[str], None],
    ) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class TranslationLoopResult:
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


def _srt(segments: tuple[TranslationSegment, ...]) -> str:
    return "".join(
        f"{row.id}\n{_srt_time(row.start)} --> {_srt_time(row.end)}\n{row.translated_text}\n\n"
        for row in segments
    )


def _artifact_from_dict(value: Any) -> TranslationArtifact | None:
    if not isinstance(value, dict):
        return None
    try:
        return TranslationArtifact(
            str(value["mediaId"]), str(value["targetLanguage"]),
            str(value["translationPath"]), str(value["translationSha256"]),
            str(value["srtPath"]), str(value["srtSha256"]),
            str(value["reviewStatus"]), int(value["segmentCount"]),
        )
    except (KeyError, TypeError, ValueError, OSError, TranslationError):
        return None


class TranslationLoop:
    def execute(
        self,
        transcript_manifest_path: str | Path,
        output_dir: str | Path,
        operation_id: str,
        *,
        target_languages: Sequence[str],
        adapter: TranslationAdapter,
        on_log: Callable[[str], None] | None = None,
    ) -> TranslationLoopResult:
        if not operation_id.strip() or not adapter.identity.strip():
            raise TranslationError("INVALID_COMMAND", "operation and adapter are required")
        languages = normalize_target_languages(target_languages)
        source = load_transcript_manifest(transcript_manifest_path)
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        receipt_path = output / "translation-receipt.json"
        manifest_path = output / "translation-manifest.json"
        input_fingerprint = hashlib.sha256(
            canonical_json(
                {
                    "schemaVersion": 1,
                    "transcriptManifestSha256": source.sha256,
                    "targetLanguages": languages,
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
            return TranslationLoopResult("REJECTED_CONFLICT", receipt_path, None, "operation input conflict")

        reusable: dict[tuple[str, str], TranslationArtifact] = {}
        if prior:
            for item in prior.get("items", []):
                if isinstance(item, dict) and item.get("status") == "COMPLETED":
                    artifact = _artifact_from_dict(item.get("artifact"))
                    if artifact is not None:
                        reusable[(artifact.target_language, artifact.media_id)] = artifact
            if prior.get("resultClass") == "COMPLETED" and self._manifest_valid(
                manifest_path, prior.get("manifestSha256"), source.sha256
            ):
                return TranslationLoopResult("DUPLICATE_COMPLETED", receipt_path, manifest_path)

        work = [(language, transcript) for language in languages for transcript in source.transcripts]
        items: list[dict[str, Any]] = []
        artifacts: list[TranslationArtifact] = []
        failures: list[tuple[str, str]] = []
        for index, (language, transcript) in enumerate(work, 1):
            key = (language, transcript.media_id)
            reused = reusable.get(key)
            if reused is not None:
                artifacts.append(reused)
                items.append(
                    {"targetLanguage": language, "mediaId": transcript.media_id, "status": "COMPLETED", "artifact": reused.to_dict(), "reused": True}
                )
                log(f"[{index}/{len(work)}] reused {language}/{transcript.media_id}")
                self._checkpoint(receipt_path, operation_id, input_fingerprint, adapter.identity, languages, items)
                continue
            log(f"[{index}/{len(work)}] translating {language}/{transcript.media_id}")
            try:
                source_texts = tuple(row.text for row in transcript.segments)
                translated = adapter.translate(source_texts, transcript.detected_language, language, log)
                if len(translated) != len(source_texts) or any(not isinstance(text, str) or not text.strip() for text in translated):
                    raise TranslationError("INVALID_ADAPTER_OUTPUT", "adapter must return one non-empty translation per segment")
                if sha256_file(transcript.transcript_path) != transcript.transcript_sha256:
                    raise TranslationError("TRANSCRIPT_CHANGED", f"transcript changed during translation: {transcript.transcript_path}")
                segments = tuple(
                    TranslationSegment(row.id, row.start, row.end, row.text, text.strip())
                    for row, text in zip(transcript.segments, translated, strict=True)
                )
                document = TranslationDocument(
                    transcript.media_id,
                    transcript.transcript_path,
                    transcript.transcript_sha256,
                    transcript.detected_language,
                    language,
                    "MACHINE",
                    segments,
                )
                item_key = hashlib.sha256(f"{language}\0{transcript.media_id}".encode("utf-8")).hexdigest()[:20]
                item_dir = output / "items" / item_key
                translation_path = item_dir / "translation.json"
                srt_path = item_dir / "translation.srt"
                _atomic_json(translation_path, document.to_dict())
                _atomic_text(srt_path, _srt(segments))
                artifact = TranslationArtifact(
                    transcript.media_id, language,
                    str(translation_path), sha256_file(translation_path),
                    str(srt_path), sha256_file(srt_path),
                    "MACHINE", len(segments),
                )
                artifacts.append(artifact)
                items.append(
                    {"targetLanguage": language, "mediaId": transcript.media_id, "status": "COMPLETED", "artifact": artifact.to_dict(), "reused": False}
                )
            except Exception as error:
                message = f"{type(error).__name__}: {error}"[-2000:]
                failures.append(key)
                items.append({"targetLanguage": language, "mediaId": transcript.media_id, "status": "FAILED", "error": message})
                log(f"[{index}/{len(work)}] failed {language}/{transcript.media_id}: {message}")
            self._checkpoint(receipt_path, operation_id, input_fingerprint, adapter.identity, languages, items)

        if failures:
            self._checkpoint(
                receipt_path, operation_id, input_fingerprint, adapter.identity, languages, items,
                result_class="FAILED", error=f"{len(failures)} translation item(s) failed",
            )
            if manifest_path.exists():
                manifest_path.unlink()
            return TranslationLoopResult("FAILED", receipt_path, None, f"{len(failures)} translation item(s) failed")

        manifest = TranslationManifest(
            str(source.path), source.sha256, source.expected_media_ids, languages, tuple(artifacts)
        )
        _atomic_json(manifest_path, manifest.to_dict())
        manifest_sha256 = sha256_file(manifest_path)
        self._checkpoint(
            receipt_path, operation_id, input_fingerprint, adapter.identity, languages, items,
            result_class="COMPLETED", manifest_path=manifest_path, manifest_sha256=manifest_sha256,
        )
        return TranslationLoopResult("COMPLETED", receipt_path, manifest_path)

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
        languages: tuple[str, ...],
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
                "targetLanguages": list(languages),
                "resultClass": result_class,
                "items": items,
                "manifest": str(manifest_path) if manifest_path else None,
                "manifestSha256": manifest_sha256,
                "error": error,
            },
        )

    @staticmethod
    def _manifest_valid(path: Path, expected_sha256: Any, transcript_sha256: str) -> bool:
        if not path.is_file() or not isinstance(expected_sha256, str) or sha256_file(path) != expected_sha256:
            return False
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("schemaVersion") != 1 or value.get("transcriptManifestSha256") != transcript_sha256:
                return False
            return bool(value.get("translations")) and all(
                _artifact_from_dict(row) is not None for row in value["translations"]
            )
        except (OSError, TypeError, json.JSONDecodeError):
            return False
