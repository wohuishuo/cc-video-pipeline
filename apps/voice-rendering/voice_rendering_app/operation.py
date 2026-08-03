"""Serial, resumable voice rendering from a Translation Manifest."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Protocol


class VoiceRenderingError(ValueError):
    pass


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(partial, path)


class VoiceAdapter(Protocol):
    identity: str
    output_suffix: str

    def synthesize(
        self, text: str, language: str, voice: str, output: Path,
        on_log: Callable[[str], None], *, target_duration: float | None = None,
    ) -> float: ...


@dataclass(frozen=True)
class VoiceRenderingResult:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    error: str | None = None


def _load_translation_manifest(path: str | Path) -> tuple[Path, str, list[dict[str, Any]], list[str]]:
    manifest_path = Path(path).resolve()
    if not manifest_path.is_file():
        raise VoiceRenderingError(f"translation manifest missing: {manifest_path}")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise VoiceRenderingError(f"invalid translation manifest: {error}") from error
    languages = value.get("targetLanguages")
    rows = value.get("translations")
    expected_media = value.get("expectedMediaIds")
    if value.get("schemaVersion") != 1 or not isinstance(languages, list) or not languages or not isinstance(rows, list):
        raise VoiceRenderingError("invalid translation manifest contract")
    expected = [(language, media) for language in languages for media in expected_media or []]
    if [(row.get("targetLanguage"), row.get("mediaId")) for row in rows] != expected:
        raise VoiceRenderingError("translation manifest coverage mismatch")
    work: list[dict[str, Any]] = []
    for row in rows:
        document_path = Path(str(row.get("translationPath", ""))).resolve()
        if not document_path.is_file() or sha256_file(document_path) != row.get("translationSha256"):
            raise VoiceRenderingError("translation artifact fingerprint mismatch")
        document = json.loads(document_path.read_text(encoding="utf-8-sig"))
        segments = document.get("segments")
        if (
            document.get("targetLanguage") != row.get("targetLanguage")
            or document.get("source", {}).get("mediaId") != row.get("mediaId")
            or not isinstance(segments, list)
            or len(segments) != row.get("segmentCount")
        ):
            raise VoiceRenderingError("translation document contract mismatch")
        for index, segment in enumerate(segments, 1):
            if segment.get("id") != index or not str(segment.get("translatedText", "")).strip():
                raise VoiceRenderingError("invalid translated segment")
            work.append({
                "targetLanguage": row["targetLanguage"], "mediaId": row["mediaId"],
                "translationPath": str(document_path), "translationSha256": row["translationSha256"],
                "segmentId": index, "text": str(segment["translatedText"]).strip(),
                "start": float(segment["start"]), "end": float(segment["end"]),
            })
    return manifest_path, sha256_file(manifest_path), work, list(languages)


def _valid_clip(value: Any) -> bool:
    try:
        path = Path(value["path"]).resolve()
        return (
            value["duration"] > 0 and path.is_file() and path.stat().st_size > 0
            and sha256_file(path) == value["sha256"]
        )
    except (KeyError, TypeError, ValueError, OSError):
        return False


class VoiceRenderingLoop:
    def execute(self, translation_manifest_path, output_dir, operation_id, *, voices, adapter, on_log=None):
        manifest_path, manifest_sha, work, languages = _load_translation_manifest(translation_manifest_path)
        if not operation_id.strip() or not adapter.identity.strip():
            raise VoiceRenderingError("operation and adapter are required")
        if set(voices) != set(languages) or any(not str(value).strip() for value in voices.values()):
            raise VoiceRenderingError("voice policy must cover every target language exactly")
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        receipt_path = output / "voice-receipt.json"
        voice_manifest_path = output / "voice-manifest.json"
        fingerprint = hashlib.sha256(_canonical({
            "schemaVersion": 1, "translationManifestSha256": manifest_sha,
            "voices": voices, "adapter": adapter.identity,
        }).encode()).hexdigest()
        prior = None
        if receipt_path.is_file():
            try:
                prior = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                pass
        if prior and (prior.get("operationId") != operation_id or prior.get("inputFingerprint") != fingerprint):
            return VoiceRenderingResult("REJECTED_CONFLICT", receipt_path, None, "operation input conflict")
        if prior and prior.get("resultClass") == "COMPLETED" and voice_manifest_path.is_file() and sha256_file(voice_manifest_path) == prior.get("manifestSha256"):
            return VoiceRenderingResult("DUPLICATE_COMPLETED", receipt_path, voice_manifest_path)
        reusable = {}
        for item in (prior or {}).get("items", []):
            key = (item.get("targetLanguage"), item.get("mediaId"), item.get("segmentId"))
            if item.get("status") == "COMPLETED" and _valid_clip(item.get("clip")):
                reusable[key] = item
        log = on_log or (lambda _message: None)
        results: list[dict[str, Any] | None] = [None] * len(work)
        missing: list[tuple[int, dict[str, Any]]] = []
        maximum_active = int((prior or {}).get("maximumActiveSynthesis", 0))
        for index, row in enumerate(work, 1):
            key = (row["targetLanguage"], row["mediaId"], row["segmentId"])
            reused = reusable.get(key)
            text_sha = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
            voice = voices[row["targetLanguage"]]
            if reused and reused.get("textSha256") == text_sha and reused.get("voice") == voice and reused.get("translationSha256") == row["translationSha256"]:
                results[index - 1] = {**reused, "reused": True}
                log(f"[{index}/{len(work)}] reused {row['targetLanguage']}/{row['mediaId']}/{row['segmentId']}")
            else:
                missing.append((index - 1, row))
        self._checkpoint(
            receipt_path, operation_id, fingerprint, adapter.identity, voices,
            [item for item in results if item is not None], maximum_active,
        )

        def render_one(slot: int, row: dict[str, Any]) -> tuple[int, dict[str, Any]]:
            key = (row["targetLanguage"], row["mediaId"], row["segmentId"])
            text_sha = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
            voice = voices[row["targetLanguage"]]
            partial: Path | None = None
            started = time.monotonic()
            log(f"[{slot + 1}/{len(work)}] rendering {row['targetLanguage']}/{row['mediaId']}/{row['segmentId']}")
            try:
                item_key = hashlib.sha256(f"{key}".encode()).hexdigest()[:20]
                suffix = str(getattr(adapter, "output_suffix", ".mp3"))
                if not suffix.startswith(".") or any(value in suffix for value in ("/", "\\")):
                    raise VoiceRenderingError("adapter output suffix is invalid")
                final = output / "clips" / f"{item_key}{suffix}"
                partial = final.with_name(f".{final.name}.partial")
                partial.parent.mkdir(parents=True, exist_ok=True)
                partial.unlink(missing_ok=True)
                duration = float(adapter.synthesize(
                    row["text"], row["targetLanguage"], voice, partial, log,
                    target_duration=row["end"] - row["start"],
                ))
                if duration <= 0 or not partial.is_file() or partial.stat().st_size <= 0:
                    raise VoiceRenderingError("adapter returned invalid audio")
                os.replace(partial, final)
                clip = {"path": str(final), "sha256": sha256_file(final), "duration": duration, "size": final.stat().st_size}
                return slot, {
                    **{field: row[field] for field in ("targetLanguage", "mediaId", "segmentId", "translationSha256", "start", "end")},
                    "text": row["text"], "textSha256": text_sha, "voice": voice,
                    "status": "COMPLETED", "clip": clip, "reused": False,
                    "attempts": int(getattr(adapter, "last_attempts", 1)),
                    "elapsedSeconds": round(time.monotonic() - started, 3),
                }
            except Exception as error:
                if partial is not None:
                    partial.unlink(missing_ok=True)
                return slot, {
                    "targetLanguage": key[0], "mediaId": key[1], "segmentId": key[2],
                    "status": "FAILED", "attempts": int(getattr(adapter, "last_attempts", 1)),
                    "elapsedSeconds": round(time.monotonic() - started, 3),
                    "error": f"{type(error).__name__}: {error}"[-2000:],
                }

        if missing:
            workers = max(1, min(int(getattr(adapter, "max_workers", 1)), len(missing)))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="voice-segment") as executor:
                futures = [executor.submit(render_one, slot, row) for slot, row in missing]
                for future in as_completed(futures):
                    slot, item = future.result()
                    results[slot] = item
                    maximum_active = max(maximum_active, int(getattr(adapter, "maximum_active", 1)))
                    self._checkpoint(
                        receipt_path, operation_id, fingerprint, adapter.identity, voices,
                        [value for value in results if value is not None], maximum_active,
                    )
        items = [item for item in results if item is not None]
        failures = [item for item in items if item.get("status") == "FAILED"]
        if failures:
            self._checkpoint(receipt_path, operation_id, fingerprint, adapter.identity, voices, items, maximum_active, result_class="FAILED", error=f"{len(failures)} clip(s) failed")
            if voice_manifest_path.exists(): voice_manifest_path.unlink()
            return VoiceRenderingResult("FAILED", receipt_path, None, f"{len(failures)} clip(s) failed")
        manifest = {
            "schemaVersion": 1, "translationManifest": str(manifest_path),
            "translationManifestSha256": manifest_sha, "voices": voices,
            "clips": [{key: value for key, value in item.items() if key not in {"status", "reused"}} for item in items],
        }
        _atomic_json(voice_manifest_path, manifest)
        manifest_digest = sha256_file(voice_manifest_path)
        self._checkpoint(receipt_path, operation_id, fingerprint, adapter.identity, voices, items, maximum_active, result_class="COMPLETED", manifest=voice_manifest_path, manifest_sha=manifest_digest)
        return VoiceRenderingResult("COMPLETED", receipt_path, voice_manifest_path)

    @staticmethod
    def _checkpoint(path, operation_id, fingerprint, adapter, voices, items, maximum_active, *, result_class="RUNNING", error=None, manifest=None, manifest_sha=None):
        _atomic_json(path, {
            "schemaVersion": 1, "operationId": operation_id, "inputFingerprint": fingerprint,
            "adapter": adapter, "voices": voices, "resultClass": result_class, "items": items,
            "maximumActiveSynthesis": maximum_active, "manifest": str(manifest) if manifest else None,
            "manifestSha256": manifest_sha, "error": error,
        })
