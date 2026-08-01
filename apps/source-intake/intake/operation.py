"""Idempotent Source Intake operation and atomic artifact publication."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Protocol

from .contracts import IntakeError, MediaEntry, SourceManifest, SourceSpec, canonical_json
from .folder import discover_folder


@dataclass(frozen=True)
class TransportResult:
    completed: bool
    media_paths: tuple[Path, ...]
    platform_receipt: Path | None
    facts: dict[str, Any]
    error: str | None = None


class URLTransport(Protocol):
    def fetch(
        self, spec: SourceSpec, output_dir: Path, on_log: Callable[[str], None]
    ) -> TransportResult: ...


@dataclass(frozen=True)
class IntakeResult:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    error: str | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(partial, path)


class IntakeOperation:
    def execute(
        self,
        spec: SourceSpec,
        output_dir: Path,
        operation_id: str,
        *,
        transport: URLTransport | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> IntakeResult:
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = output_dir / "intake-receipt.json"
        manifest_path = output_dir / "source-manifest.json"
        input_fingerprint = hashlib.sha256(
            canonical_json({"schemaVersion": 1, "source": spec.to_dict()}).encode("utf-8")
        ).hexdigest()
        log = on_log or (lambda _: None)

        prior = self._prior(receipt_path)
        if prior:
            if (
                prior.get("operationId") != operation_id
                or prior.get("inputFingerprint") != input_fingerprint
            ):
                return IntakeResult("REJECTED_CONFLICT", receipt_path, None, "operation input conflict")
            if prior.get("resultClass") == "COMPLETED" and self._published_valid(
                manifest_path, prior.get("manifestSha256")
            ):
                return IntakeResult("DUPLICATE_COMPLETED", receipt_path, manifest_path)

        try:
            if spec.kind == "folder":
                manifest = discover_folder(spec)
                platform_receipt = None
            elif spec.kind == "url":
                if transport is None:
                    raise IntakeError("TRANSPORT_UNAVAILABLE", "URL intake requires a transport adapter")
                transported = transport.fetch(spec, output_dir / "platform", log)
                if not transported.completed:
                    raise IntakeError("TRANSPORT_FAILED", transported.error or "platform transport failed")
                manifest = self._transport_manifest(spec, transported)
                platform_receipt = transported.platform_receipt
            else:
                raise IntakeError("UNSUPPORTED_SOURCE", spec.kind)
            _atomic_json(manifest_path, manifest.to_dict())
            manifest_hash = _sha256(manifest_path)
            receipt = {
                "schemaVersion": 1,
                "operationId": operation_id,
                "inputFingerprint": input_fingerprint,
                "resultClass": "COMPLETED",
                "manifest": str(manifest_path),
                "manifestSha256": manifest_hash,
                "platformReceipt": str(platform_receipt) if platform_receipt else None,
                "mediaCount": len(manifest.media),
            }
            _atomic_json(receipt_path, receipt)
            log(f"Published source manifest with {len(manifest.media)} media file(s)")
            return IntakeResult("COMPLETED", receipt_path, manifest_path)
        except (IntakeError, OSError, ValueError) as error:
            if manifest_path.exists():
                manifest_path.unlink()
            _atomic_json(
                receipt_path,
                {
                    "schemaVersion": 1,
                    "operationId": operation_id,
                    "inputFingerprint": input_fingerprint,
                    "resultClass": "FAILED",
                    "errorCode": error.code if isinstance(error, IntakeError) else "IO_FAILURE",
                    "error": str(error),
                },
            )
            return IntakeResult("FAILED", receipt_path, None, str(error))

    @staticmethod
    def _prior(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _published_valid(path: Path, expected_hash: Any) -> bool:
        if not path.is_file() or not isinstance(expected_hash, str) or _sha256(path) != expected_hash:
            return False
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            media = manifest.get("media", [])
            return bool(media) and all(
                Path(str(row["path"])).is_file()
                and Path(str(row["path"])).stat().st_size == int(row["size"])
                for row in media
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False

    @staticmethod
    def _transport_manifest(spec: SourceSpec, result: TransportResult) -> SourceManifest:
        entries: list[MediaEntry] = []
        for path in sorted((Path(value).resolve() for value in result.media_paths), key=lambda p: p.as_posix().casefold()):
            if not path.is_file():
                raise IntakeError("TRANSPORT_OUTPUT_MISSING", f"downloaded media missing: {path}")
            stat = path.stat()
            identity = hashlib.sha256(
                f"{path.as_posix().casefold()}\0{stat.st_size}\0{stat.st_mtime_ns}".encode("utf-8")
            ).hexdigest()
            entries.append(MediaEntry(identity, str(path), stat.st_size, path.suffix.lower()))
        if not entries:
            raise IntakeError("EMPTY_SOURCE", "transport returned no media")
        return SourceManifest(
            "url",
            {
                "url": spec.value,
                "platform": spec.platform,
                "platformFacts": result.facts,
            },
            tuple(entries),
        )

