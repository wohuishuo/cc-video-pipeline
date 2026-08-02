"""Durable strict-serial continuation for Publication child executions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .contracts import BatchExecutionInput, ExecutionItem, canonical_json, sha256_file


@dataclass(frozen=True)
class ChildExecutionFact:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    manifest_sha256: str | None
    external_id: str | None
    error: str | None = None


@dataclass(frozen=True)
class BatchExecutionResult:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    error: str | None = None


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _child_operation_id(operation_id: str, item: ExecutionItem) -> str:
    suffix = hashlib.sha256(f"{operation_id}\0{item.ordinal}\0{item.plan_sha256}".encode("utf-8")).hexdigest()[:16]
    return f"{operation_id}:item:{item.ordinal:04d}:{suffix}"


def _base_row(item: ExecutionItem, child_operation_id: str) -> dict[str, Any]:
    return {**item.to_public_dict(), "childOperationId": child_operation_id}


def _completed_matches(row: dict[str, Any], item: ExecutionItem, child_operation_id: str) -> bool:
    try:
        receipt_path = Path(str(row["publicationReceipt"])).resolve()
        manifest_path = Path(str(row["executionManifest"])).resolve()
        receipt_sha = row["publicationReceiptSha256"]
        manifest_sha = row["executionManifestSha256"]
        external_id = row["externalId"]
        receipt = _read_json(receipt_path)
        manifest = _read_json(manifest_path)
        publication = manifest["publications"][0]
        valid = (
            row.get("status") == "COMPLETED"
            and row.get("ordinal") == item.ordinal
            and row.get("targetLanguage") == item.target_language
            and row.get("mediaId") == item.media_id
            and row.get("publicationPlanSha256") == item.plan_sha256
            and row.get("childOperationId") == child_operation_id
            and isinstance(receipt_sha, str)
            and receipt_path.is_file()
            and sha256_file(receipt_path) == receipt_sha
            and isinstance(manifest_sha, str)
            and manifest_path.is_file()
            and sha256_file(manifest_path) == manifest_sha
            and isinstance(receipt, dict)
            and receipt.get("schemaVersion") == 1
            and receipt.get("operationId") == child_operation_id
            and receipt.get("planSha256") == item.plan_sha256
            and receipt.get("resultClass") == "COMPLETED"
            and Path(str(receipt.get("manifest", ""))).resolve() == manifest_path
            and receipt.get("manifestSha256") == manifest_sha
            and isinstance(manifest, dict)
            and manifest.get("schemaVersion") == 1
            and manifest.get("public") is False
            and Path(str(manifest.get("plan", ""))).resolve() == item.plan_path
            and manifest.get("planSha256") == item.plan_sha256
            and isinstance(manifest.get("publications"), list)
            and len(manifest["publications"]) == 1
            and publication.get("jobId") == item.job_id
            and publication.get("platform") == "youtube"
            and publication.get("status") == "COMPLETED"
            and isinstance(external_id, str)
            and bool(external_id.strip())
            and publication.get("externalId") == external_id
        )
    except (OSError, KeyError, TypeError, ValueError):
        return False
    return bool(valid)


def _unknown_matches(row: dict[str, Any], item: ExecutionItem, child_operation_id: str) -> bool:
    try:
        receipt_path = Path(str(row["publicationReceipt"])).resolve()
        receipt = _read_json(receipt_path)
        return bool(
            row.get("status") == "UNKNOWN"
            and row.get("ordinal") == item.ordinal
            and row.get("publicationPlanSha256") == item.plan_sha256
            and row.get("childOperationId") == child_operation_id
            and receipt_path.is_file()
            and sha256_file(receipt_path) == row.get("publicationReceiptSha256")
            and isinstance(receipt, dict)
            and receipt.get("schemaVersion") == 1
            and receipt.get("operationId") == child_operation_id
            and receipt.get("planSha256") == item.plan_sha256
            and receipt.get("resultClass") in {"UNKNOWN", "REJECTED_UNKNOWN"}
        )
    except (OSError, KeyError, TypeError, ValueError):
        return False


class PublicationBatchExecution:
    """Own only batch continuation; Publication owns every child execution."""

    def execute(
        self,
        batch: BatchExecutionInput,
        output_dir: str | Path,
        operation_id: str,
        executor: Any,
        on_log: Callable[[str], None] | None = None,
    ) -> BatchExecutionResult:
        output = Path(output_dir).resolve(); output.mkdir(parents=True, exist_ok=True)
        receipt_path = output / "publication-batch-execution-receipt.json"
        manifest_path = output / "publication-batch-execution-manifest.json"
        if not isinstance(operation_id, str) or not operation_id.strip() or len(operation_id) > 200:
            return BatchExecutionResult("REJECTED_MALFORMED", receipt_path, None, "operation ID is required")
        executor_identity = str(getattr(executor, "identity", "")).strip()
        if not executor_identity:
            return BatchExecutionResult("REJECTED_MALFORMED", receipt_path, None, "executor identity is required")
        fingerprint = hashlib.sha256(canonical_json(batch.fingerprint_value(executor_identity)).encode("utf-8")).hexdigest()
        prior = _read_json(receipt_path)
        if receipt_path.is_file() and prior is None:
            return BatchExecutionResult("REJECTED_CONFLICT", receipt_path, None, "existing receipt is unreadable")
        if prior and (prior.get("operationId") != operation_id or prior.get("inputFingerprint") != fingerprint):
            return BatchExecutionResult("REJECTED_CONFLICT", receipt_path, None, "operation input conflict")
        prior_items = {
            row.get("identity"): row
            for row in (prior or {}).get("items", [])
            if isinstance(row, dict) and isinstance(row.get("identity"), str)
        }
        state_items: list[dict[str, Any]] = []
        log = on_log or (lambda _line: None)
        changed = False; new_unknown = False
        for item in batch.items:
            child_id = _child_operation_id(operation_id, item)
            previous = prior_items.get(item.identity)
            if isinstance(previous, dict) and _completed_matches(previous, item, child_id):
                state_items.append({**previous, "reused": True})
                continue
            if isinstance(previous, dict) and previous.get("status") == "UNKNOWN":
                preserved = {**previous, "reused": True}
                if not _unknown_matches(previous, item, child_id):
                    preserved["error"] = "unknown publication evidence is stale; automatic replay remains fenced"
                state_items.append(preserved)
                continue
            changed = True
            if manifest_path.exists():
                manifest_path.unlink()
            item_root = output / "items" / f"{item.ordinal:04d}-{item.plan_sha256[:12]}"
            log(f"[{item.ordinal}/{len(batch.items)}] executing {item.identity}")
            try:
                fact = executor.execute(item, item_root, child_id, batch.vault_path, log)
            except Exception as error:
                fact = ChildExecutionFact("FAILED", item_root / "publication-receipt.json", None, None, None, str(error))
            if fact.result_class == "COMPLETED":
                candidate = {
                    **_base_row(item, child_id),
                    "identity": item.identity,
                    "status": "COMPLETED",
                    "publicationReceipt": str(Path(fact.receipt_path).resolve()),
                    "publicationReceiptSha256": sha256_file(fact.receipt_path) if Path(fact.receipt_path).is_file() else None,
                    "executionManifest": str(Path(fact.manifest_path).resolve()) if fact.manifest_path else None,
                    "executionManifestSha256": fact.manifest_sha256,
                    "externalId": fact.external_id,
                    "reused": False,
                }
                if _completed_matches(candidate, item, child_id):
                    state_items.append(candidate)
                else:
                    state_items.append({**_base_row(item, child_id), "identity": item.identity, "status": "FAILED", "error": "Publication completion fact is invalid", "reused": False})
            elif fact.result_class in {"UNKNOWN", "REJECTED_UNKNOWN"}:
                new_unknown = True
                receipt = Path(fact.receipt_path).resolve()
                state_items.append({
                    **_base_row(item, child_id), "identity": item.identity, "status": "UNKNOWN",
                    "publicationReceipt": str(receipt),
                    "publicationReceiptSha256": sha256_file(receipt) if receipt.is_file() else None,
                    "error": "publication outcome is unknown", "reused": False,
                })
            else:
                state_items.append({
                    **_base_row(item, child_id), "identity": item.identity, "status": "FAILED",
                    "error": str(fact.error or "Publication execution failed")[:1000], "reused": False,
                })
            self._write_receipt(receipt_path, operation_id, fingerprint, batch, state_items, "RUNNING", None, None, None)
        failures = [row for row in state_items if row.get("status") == "FAILED"]
        unknowns = [row for row in state_items if row.get("status") == "UNKNOWN"]
        if unknowns:
            if manifest_path.exists():
                manifest_path.unlink()
            result_class = "UNKNOWN" if new_unknown else "REJECTED_UNKNOWN"
            error = f"{len(unknowns)} publication outcome(s) unknown; automatic replay is fenced"
            self._write_receipt(receipt_path, operation_id, fingerprint, batch, state_items, "UNKNOWN", None, None, error)
            return BatchExecutionResult(result_class, receipt_path, None, error)
        if failures or len(state_items) != len(batch.items):
            if manifest_path.exists():
                manifest_path.unlink()
            error = f"{len(failures)} publication child execution(s) failed"
            self._write_receipt(receipt_path, operation_id, fingerprint, batch, state_items, "FAILED", None, None, error)
            return BatchExecutionResult("FAILED", receipt_path, None, error)
        if not changed and prior and prior.get("resultClass") == "COMPLETED":
            if manifest_path.is_file() and sha256_file(manifest_path) == prior.get("manifestSha256"):
                return BatchExecutionResult("DUPLICATE_COMPLETED", receipt_path, manifest_path)
        aggregate_items = [
            {
                **{key: row[key] for key in (
                    "ordinal", "identity", "targetLanguage", "mediaId", "derivativePath",
                    "derivativeSha256", "metadataPath", "metadataSha256", "publicationPlan",
                    "publicationPlanSha256", "publicationReceipt", "publicationReceiptSha256",
                    "executionManifest", "executionManifestSha256", "externalId",
                )},
                "platform": "youtube",
            }
            for row in state_items
        ]
        aggregate = {
            "schemaVersion": 1,
            "batchPlan": str(batch.plan_path),
            "batchPlanSha256": batch.plan_sha256,
            "targetLanguages": list(batch.target_languages),
            "expectedMediaIds": list(batch.expected_media_ids),
            "expectedDerivativeKeys": list(batch.expected_derivative_keys),
            "maximumActiveItems": 1,
            "items": aggregate_items,
            "totalPublicationCount": len(aggregate_items),
        }
        _atomic_json(manifest_path, aggregate); manifest_sha = sha256_file(manifest_path)
        self._write_receipt(receipt_path, operation_id, fingerprint, batch, state_items, "COMPLETED", manifest_path, manifest_sha, None)
        return BatchExecutionResult("COMPLETED", receipt_path, manifest_path)

    @staticmethod
    def _write_receipt(
        receipt_path: Path,
        operation_id: str,
        fingerprint: str,
        batch: BatchExecutionInput,
        items: list[dict[str, Any]],
        result_class: str,
        manifest_path: Path | None,
        manifest_sha256: str | None,
        error: str | None,
    ) -> None:
        _atomic_json(
            receipt_path,
            {
                "schemaVersion": 1,
                "operationId": operation_id,
                "inputFingerprint": fingerprint,
                "batchPlan": str(batch.plan_path),
                "batchPlanSha256": batch.plan_sha256,
                "credentialVaultPath": str(batch.vault_path),
                "resultClass": result_class,
                "maximumActiveItems": 1,
                "itemCount": len(batch.items),
                "completedCount": sum(row.get("status") == "COMPLETED" for row in items),
                "failedCount": sum(row.get("status") == "FAILED" for row in items),
                "unknownCount": sum(row.get("status") == "UNKNOWN" for row in items),
                "items": items,
                "manifest": str(manifest_path) if manifest_path else None,
                "manifestSha256": manifest_sha256,
                "error": error,
            },
        )
