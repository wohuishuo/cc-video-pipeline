"""Durable, strictly serial continuation owner for creator localization."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Protocol
from uuid import uuid4

from .contracts import BatchContractError, BatchPolicy, CreatorItem, CreatorSource


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


@dataclass(frozen=True)
class ItemProcessResult:
    completed: bool
    localization_manifest: Path | None
    derivative_count: int
    error: str | None = None


class ItemProcessor(Protocol):
    def process(
        self,
        item: CreatorItem,
        item_root: Path,
        child_prefix: str,
        batch_policy: BatchPolicy,
        cookies: Path | None,
        on_log: Callable[[str], None],
    ) -> ItemProcessResult: ...


@dataclass(frozen=True)
class BatchResult:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    error: str | None = None


class BatchOperation:
    def execute(
        self,
        source: CreatorSource,
        policy: BatchPolicy,
        output_dir: Path,
        operation_id: str,
        *,
        processor: ItemProcessor,
        cookies: Path | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> BatchResult:
        output = Path(output_dir).resolve()
        receipt_path = output / "creator-batch-receipt.json"
        manifest_path = output / "creator-batch-manifest.json"
        if not isinstance(operation_id, str) or not operation_id.strip():
            return BatchResult("REJECTED_MALFORMED", receipt_path, None, "operation ID is required")
        cookie_path = Path(cookies).resolve() if cookies is not None else None
        if cookie_path is not None and not cookie_path.is_file():
            return BatchResult("REJECTED_MALFORMED", receipt_path, None, "authentication file does not exist")
        cookie_sha = _sha(cookie_path) if cookie_path is not None else None
        fingerprint = hashlib.sha256(
            _canonical(
                {
                    "schemaVersion": 1,
                    "creatorManifestSha256": source.manifest_sha256,
                    "policy": policy.to_public_dict(),
                    "authenticationMaterialSha256": cookie_sha,
                }
            ).encode("utf-8")
        ).hexdigest()
        prior = self._read(receipt_path)
        if prior and (
            prior.get("operationId") != operation_id
            or prior.get("inputFingerprint") != fingerprint
        ):
            return BatchResult("REJECTED_CONFLICT", receipt_path, None, "operation input conflict")
        prior_items = {
            str(row.get("id")): row
            for row in (prior or {}).get("items", [])
            if isinstance(row, dict)
        }
        if (
            prior
            and prior.get("resultClass") == "COMPLETED"
            and manifest_path.is_file()
            and _sha(manifest_path) == prior.get("manifestSha256")
            and all(self._completed_row_valid(prior_items.get(item.id)) for item in source.items)
        ):
            return BatchResult("DUPLICATE_COMPLETED", receipt_path, manifest_path)

        output.mkdir(parents=True, exist_ok=True)
        log = on_log or (lambda _line: None)
        rows: list[dict[str, Any]] = []
        maximum_active = int((prior or {}).get("maximumActiveItems", 0))
        for item in source.items:
            previous = prior_items.get(item.id)
            if self._completed_row_valid(previous):
                rows.append(dict(previous))
                log(f"Skipped verified creator item {item.ordinal}/{len(source.items)}: {item.id}")
                continue
            item_key = hashlib.sha256(item.id.encode("utf-8")).hexdigest()[:12]
            item_root = output / "items" / f"{item.ordinal:04d}-{item_key}"
            child_prefix = f"{operation_id}:item:{item.ordinal}:{item_key}"
            running = {
                "ordinal": item.ordinal,
                "id": item.id,
                "status": "RUNNING",
                "localizationManifest": None,
                "localizationManifestSha256": None,
                "derivativeCount": 0,
                "error": None,
            }
            rows.append(running)
            maximum_active = max(maximum_active, 1)
            self._checkpoint(receipt_path, operation_id, fingerprint, source, policy, rows, maximum_active)
            log(f"Started creator item {item.ordinal}/{len(source.items)}: {item.id}")
            def item_log(line: str) -> None:
                try:
                    event = json.loads(line)
                except (TypeError, json.JSONDecodeError):
                    log(line)
                    return
                if isinstance(event, dict) and event.get("event") == "creator_phase":
                    item_value = event.get("item") if isinstance(event.get("item"), dict) else {}
                    event["item"] = {**item_value, "count": len(source.items)}
                    log(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
                else:
                    log(line)
            try:
                outcome = processor.process(item, item_root, child_prefix, policy, cookie_path, item_log)
            except Exception as error:  # external child boundary
                outcome = ItemProcessResult(False, None, 0, f"{type(error).__name__}: {error}")
            if outcome.completed and outcome.localization_manifest is not None:
                committed = Path(outcome.localization_manifest).resolve()
                if committed.is_file() and int(outcome.derivative_count) > 0:
                    rows[-1] = {
                        **running,
                        "status": "COMPLETED",
                        "localizationManifest": str(committed),
                        "localizationManifestSha256": _sha(committed),
                        "derivativeCount": int(outcome.derivative_count),
                    }
                else:
                    rows[-1] = {**running, "status": "FAILED", "error": "processor did not commit a valid Localization Manifest"}
            else:
                rows[-1] = {**running, "status": "FAILED", "error": self._safe_error(outcome.error, cookie_path)}
            self._checkpoint(receipt_path, operation_id, fingerprint, source, policy, rows, maximum_active)
            log(f"Creator item {item.id}: {rows[-1]['status']}")

        failed = [row for row in rows if row.get("status") != "COMPLETED"]
        if failed:
            if manifest_path.exists():
                manifest_path.unlink()
            detail = f"{len(failed)} creator item(s) incomplete"
            self._checkpoint(
                receipt_path,
                operation_id,
                fingerprint,
                source,
                policy,
                rows,
                maximum_active,
                result_class="FAILED",
                error=detail,
            )
            return BatchResult("FAILED", receipt_path, None, detail)

        manifest = {
            "schemaVersion": 1,
            **source.to_public_dict(),
            **policy.to_public_dict(),
            "expectedItemIds": [item.id for item in source.items],
            "maximumActiveItems": maximum_active,
            "items": [
                {
                    "ordinal": row["ordinal"],
                    "id": row["id"],
                    "localizationManifest": row["localizationManifest"],
                    "localizationManifestSha256": row["localizationManifestSha256"],
                    "derivativeCount": row["derivativeCount"],
                }
                for row in rows
            ],
        }
        _atomic(manifest_path, manifest)
        manifest_sha = _sha(manifest_path)
        self._checkpoint(
            receipt_path,
            operation_id,
            fingerprint,
            source,
            policy,
            rows,
            maximum_active,
            result_class="COMPLETED",
            manifest=manifest_path,
            manifest_sha=manifest_sha,
        )
        return BatchResult("COMPLETED", receipt_path, manifest_path)

    @staticmethod
    def _completed_row_valid(row: dict[str, Any] | None) -> bool:
        if not isinstance(row, dict) or row.get("status") != "COMPLETED":
            return False
        path = Path(str(row.get("localizationManifest", ""))).resolve()
        try:
            return (
                path.is_file()
                and _sha(path) == row.get("localizationManifestSha256")
                and int(row.get("derivativeCount", 0)) > 0
            )
        except (OSError, TypeError, ValueError):
            return False

    @staticmethod
    def _safe_error(value: str | None, cookies: Path | None) -> str:
        text = str(value or "item processor failed")[-4000:]
        if cookies is not None:
            text = text.replace(str(cookies), "<authentication-file>")
            text = text.replace(cookies.name, "<authentication-file>")
        return text

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _checkpoint(
        path: Path,
        operation_id: str,
        fingerprint: str,
        source: CreatorSource,
        policy: BatchPolicy,
        items: list[dict[str, Any]],
        maximum_active: int,
        *,
        result_class: str = "RUNNING",
        manifest: Path | None = None,
        manifest_sha: str | None = None,
        error: str | None = None,
    ) -> None:
        completed = sum(row.get("status") == "COMPLETED" for row in items)
        failed = sum(row.get("status") == "FAILED" for row in items)
        _atomic(
            path,
            {
                "schemaVersion": 1,
                "operationId": operation_id,
                "inputFingerprint": fingerprint,
                "resultClass": result_class,
                "creatorManifest": str(source.manifest_path),
                "creatorManifestSha256": source.manifest_sha256,
                "platform": source.platform,
                "policy": policy.to_public_dict(),
                "itemCount": len(source.items),
                "completedCount": completed,
                "failedCount": failed,
                "maximumActiveItems": maximum_active,
                "items": items,
                "manifest": str(manifest) if manifest is not None else None,
                "manifestSha256": manifest_sha,
                "error": error,
            },
        )
