"""Atomic idempotent Creator Selection operation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from .contracts import SelectionError, SelectionSpec, sha256_file


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(partial, path)


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


@dataclass(frozen=True)
class SelectionResult:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    error: str | None = None


class SelectionOperation:
    def execute(
        self, spec: SelectionSpec, output_dir: Path, operation_id: str
    ) -> SelectionResult:
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise SelectionError("INVALID_OPERATION", "operation ID is required")
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        receipt_path = output / "creator-selection-receipt.json"
        manifest_path = output / "creator-selection-manifest.json"
        prior = _read(receipt_path)
        if prior and (
            prior.get("operationId") != operation_id
            or prior.get("inputFingerprint") != spec.fingerprint
        ):
            return SelectionResult(
                "REJECTED_CONFLICT", receipt_path, None, "operation input conflict"
            )
        if (
            prior
            and prior.get("resultClass") == "COMPLETED"
            and manifest_path.is_file()
            and sha256_file(manifest_path) == prior.get("manifestSha256")
        ):
            return SelectionResult("DUPLICATE_COMPLETED", receipt_path, manifest_path)
        try:
            _atomic(manifest_path, spec.to_manifest())
            digest = sha256_file(manifest_path)
            _atomic(
                receipt_path,
                {
                    "schemaVersion": 1,
                    "operationId": operation_id,
                    "inputFingerprint": spec.fingerprint,
                    "resultClass": "COMPLETED",
                    "manifest": str(manifest_path),
                    "manifestSha256": digest,
                    "selectedItemCount": len(spec.items),
                    "selectedItemIds": list(spec.selected_item_ids),
                    "error": None,
                },
            )
            return SelectionResult("COMPLETED", receipt_path, manifest_path)
        except OSError as error:
            if manifest_path.exists():
                manifest_path.unlink()
            _atomic(
                receipt_path,
                {
                    "schemaVersion": 1,
                    "operationId": operation_id,
                    "inputFingerprint": spec.fingerprint,
                    "resultClass": "FAILED",
                    "manifest": None,
                    "manifestSha256": None,
                    "selectedItemCount": 0,
                    "selectedItemIds": [],
                    "error": str(error)[-4000:],
                },
            )
            return SelectionResult("FAILED", receipt_path, None, str(error))
