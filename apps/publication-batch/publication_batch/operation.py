"""Durable strict-serial continuation over one-video Publication planning."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Protocol

from .contracts import BatchPolicy, Derivative, LocalizationInput, MetadataTemplate, canonical_json, render_metadata, sha256_file


@dataclass(frozen=True)
class ChildPlanFact:
    plan_path: Path
    plan_sha256: str
    job_count: int


class PlanItemProcessor(Protocol):
    def plan(
        self,
        derivative: Derivative,
        metadata_path: Path,
        output_dir: Path,
        operation_id: str,
        policy: BatchPolicy,
        on_log: Callable[[str], None],
    ) -> ChildPlanFact: ...


@dataclass(frozen=True)
class BatchResult:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    error: str | None = None


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(_json_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _metadata_sha(value: dict[str, Any]) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _child_id(parent: str, derivative: Derivative) -> str:
    return (
        f"{parent}:plan:{derivative.ordinal}:"
        f"{derivative.target_language}:{derivative.media_id}:{derivative.sha256[:12]}"
    )


def _plan_matches(
    plan_path: Path,
    plan_sha: str,
    derivative: Derivative,
    metadata_path: Path,
    metadata_sha: str,
    policy: BatchPolicy,
) -> bool:
    if not plan_path.is_file() or sha256_file(plan_path) != plan_sha:
        return False
    value = _read_json(plan_path)
    if value is None or set(value) != {"schemaVersion", "video", "metadata", "public", "jobs"}:
        return False
    try:
        video = value["video"]
        metadata = value["metadata"]
        jobs = value["jobs"]
        expected_credentials = dict(policy.credentials)
        expected_jobs = []
        for ordinal, (platform, account) in enumerate(policy.targets, 1):
            row = {
                "ordinal": ordinal,
                "platform": platform,
                "account": account,
                "visibility": "private-or-draft",
            }
            if platform in expected_credentials:
                row["credentialId"] = expected_credentials[platform]
            expected_jobs.append(row)
        actual_jobs = [
            {
                key: row[key]
                for key in ("ordinal", "platform", "account", "visibility", "credentialId")
                if key in row
            }
            for row in jobs
        ]
        return (
            value["schemaVersion"] == 1
            and value["public"] is False
            and isinstance(video, dict)
            and Path(str(video["path"])).resolve() == derivative.path
            and video["sha256"] == derivative.sha256
            and int(video["size"]) == derivative.size
            and isinstance(metadata, dict)
            and Path(str(metadata["path"])).resolve() == metadata_path
            and metadata["sha256"] == metadata_sha
            and isinstance(jobs, list)
            and len(jobs) == len(policy.targets)
            and all(isinstance(row, dict) and isinstance(row.get("id"), str) and len(row["id"]) == 64 for row in jobs)
            and actual_jobs == expected_jobs
        )
    except (KeyError, TypeError, ValueError):
        return False


def _item_matches(
    item: dict[str, Any] | None,
    derivative: Derivative,
    metadata_path: Path,
    expected_metadata_sha: str,
    child_operation_id: str,
    policy: BatchPolicy,
) -> bool:
    if not isinstance(item, dict) or item.get("status") != "COMPLETED":
        return False
    try:
        stored_metadata = Path(str(item["metadataPath"])).resolve()
        plan_path = Path(str(item["publicationPlan"])).resolve()
        return (
            item["ordinal"] == derivative.ordinal
            and item["targetLanguage"] == derivative.target_language
            and item["mediaId"] == derivative.media_id
            and Path(str(item["derivativePath"])).resolve() == derivative.path
            and item["derivativeSha256"] == derivative.sha256
            and item["childOperationId"] == child_operation_id
            and stored_metadata == metadata_path
            and stored_metadata.is_file()
            and item["metadataSha256"] == expected_metadata_sha
            and sha256_file(stored_metadata) == expected_metadata_sha
            and int(item["jobCount"]) == len(policy.targets)
            and _plan_matches(
                plan_path,
                str(item["publicationPlanSha256"]),
                derivative,
                metadata_path,
                expected_metadata_sha,
                policy,
            )
        )
    except (KeyError, OSError, TypeError, ValueError):
        return False


class PublicationBatchOperation:
    """Own only aggregate planning checkpoints; child Publication owns plans."""

    maximum_active_items = 1

    def execute(
        self,
        localization: LocalizationInput,
        metadata_template: MetadataTemplate,
        policy: BatchPolicy,
        output_dir: str | Path,
        operation_id: str,
        processor: PlanItemProcessor,
        on_log: Callable[[str], None] | None = None,
    ) -> BatchResult:
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        receipt_path = output / "publication-batch-receipt.json"
        manifest_path = output / "publication-batch-plan.json"
        log = on_log or (lambda _message: None)
        input_value = {
            "localization": localization.to_public_dict(),
            "metadataTemplate": str(metadata_template.path),
            "metadataTemplateSha256": metadata_template.sha256,
            "policy": policy.to_public_dict(),
        }
        fingerprint = hashlib.sha256(canonical_json(input_value).encode("utf-8")).hexdigest()
        prior = _read_json(receipt_path)
        if receipt_path.exists() and prior is None:
            return BatchResult("REJECTED_STALE", receipt_path, None, "batch receipt is unreadable")
        if prior and (prior.get("operationId") != operation_id or prior.get("inputFingerprint") != fingerprint):
            return BatchResult("REJECTED_CONFLICT", receipt_path, None, "operation input conflict")
        prior_items = {
            (row.get("targetLanguage"), row.get("mediaId")): row
            for row in (prior.get("items", []) if prior else [])
            if isinstance(row, dict)
        }
        state_items = dict(prior_items)
        changed = False
        failures: list[str] = []
        for derivative in localization.derivatives:
            item_root = output / "items" / f"{derivative.ordinal:04d}-{derivative.sha256[:12]}"
            metadata_path = (item_root / "metadata.json").resolve()
            rendered_metadata = render_metadata(metadata_template, derivative)
            expected_metadata_sha = _metadata_sha(rendered_metadata)
            child_operation_id = _child_id(operation_id, derivative)
            key = (derivative.target_language, derivative.media_id)
            existing = state_items.get(key)
            if _item_matches(
                existing,
                derivative,
                metadata_path,
                expected_metadata_sha,
                child_operation_id,
                policy,
            ):
                log(f"[{derivative.ordinal}/{len(localization.derivatives)}] reused {derivative.identity}")
                continue
            changed = True
            _atomic_json(metadata_path, rendered_metadata)
            log(f"[{derivative.ordinal}/{len(localization.derivatives)}] planning {derivative.identity}")
            try:
                fact = processor.plan(
                    derivative,
                    metadata_path,
                    item_root / "publication",
                    child_operation_id,
                    policy,
                    log,
                )
                plan_path = Path(fact.plan_path).resolve()
                if fact.job_count != len(policy.targets) or not _plan_matches(
                    plan_path,
                    fact.plan_sha256,
                    derivative,
                    metadata_path,
                    expected_metadata_sha,
                    policy,
                ):
                    raise ValueError("child Publication Plan verification failed")
                state_items[key] = {
                    "ordinal": derivative.ordinal,
                    "targetLanguage": derivative.target_language,
                    "mediaId": derivative.media_id,
                    "derivativePath": str(derivative.path),
                    "derivativeSha256": derivative.sha256,
                    "childOperationId": child_operation_id,
                    "metadataPath": str(metadata_path),
                    "metadataSha256": expected_metadata_sha,
                    "publicationPlan": str(plan_path),
                    "publicationPlanSha256": fact.plan_sha256,
                    "jobCount": fact.job_count,
                    "status": "COMPLETED",
                    "error": None,
                }
            except Exception as error:
                message = str(error).strip() or type(error).__name__
                failures.append(derivative.identity)
                state_items[key] = {
                    "ordinal": derivative.ordinal,
                    "targetLanguage": derivative.target_language,
                    "mediaId": derivative.media_id,
                    "derivativePath": str(derivative.path),
                    "derivativeSha256": derivative.sha256,
                    "childOperationId": child_operation_id,
                    "metadataPath": str(metadata_path),
                    "metadataSha256": expected_metadata_sha,
                    "publicationPlan": None,
                    "publicationPlanSha256": None,
                    "jobCount": 0,
                    "status": "FAILED",
                    "error": message[:1000],
                }
                log(f"[{derivative.ordinal}/{len(localization.derivatives)}] failed {derivative.identity}: {message}")
            self._write_receipt(
                receipt_path,
                operation_id,
                fingerprint,
                localization,
                metadata_template,
                policy,
                state_items,
                "RUNNING",
                None,
                None,
                None,
            )
        ordered_items = [
            state_items[(derivative.target_language, derivative.media_id)]
            for derivative in localization.derivatives
            if (derivative.target_language, derivative.media_id) in state_items
        ]
        failures = [row["targetLanguage"] + ":" + row["mediaId"] for row in ordered_items if row.get("status") != "COMPLETED"]
        if failures or len(ordered_items) != len(localization.derivatives):
            if manifest_path.exists():
                manifest_path.unlink()
            error = f"{len(failures)} derivative plan(s) failed"
            self._write_receipt(
                receipt_path,
                operation_id,
                fingerprint,
                localization,
                metadata_template,
                policy,
                state_items,
                "FAILED",
                None,
                None,
                error,
            )
            return BatchResult("FAILED", receipt_path, None, error)
        if not changed and prior and prior.get("resultClass") == "COMPLETED":
            prior_manifest = Path(str(prior.get("manifest", ""))).resolve()
            if (
                prior_manifest == manifest_path
                and manifest_path.is_file()
                and sha256_file(manifest_path) == prior.get("manifestSha256")
            ):
                return BatchResult("DUPLICATE_COMPLETED", receipt_path, manifest_path)
        aggregate_items = [
            {
                "ordinal": row["ordinal"],
                "targetLanguage": row["targetLanguage"],
                "mediaId": row["mediaId"],
                "derivativePath": row["derivativePath"],
                "derivativeSha256": row["derivativeSha256"],
                "metadataPath": row["metadataPath"],
                "metadataSha256": row["metadataSha256"],
                "publicationPlan": row["publicationPlan"],
                "publicationPlanSha256": row["publicationPlanSha256"],
                "jobCount": row["jobCount"],
            }
            for row in ordered_items
        ]
        aggregate = {
            "schemaVersion": 1,
            "localizationManifest": str(localization.manifest_path),
            "localizationManifestSha256": localization.manifest_sha256,
            "metadataTemplate": str(metadata_template.path),
            "metadataTemplateSha256": metadata_template.sha256,
            "targetLanguages": list(localization.target_languages),
            "expectedMediaIds": list(localization.expected_media_ids),
            "targets": policy.to_public_dict()["targets"],
            "public": False,
            "maximumActiveItems": 1,
            "expectedDerivativeKeys": [row.identity for row in localization.derivatives],
            "items": aggregate_items,
            "totalJobCount": sum(int(row["jobCount"]) for row in ordered_items),
        }
        _atomic_json(manifest_path, aggregate)
        manifest_sha = sha256_file(manifest_path)
        self._write_receipt(
            receipt_path,
            operation_id,
            fingerprint,
            localization,
            metadata_template,
            policy,
            state_items,
            "COMPLETED",
            manifest_path,
            manifest_sha,
            None,
        )
        return BatchResult("COMPLETED", receipt_path, manifest_path)

    @staticmethod
    def _write_receipt(
        receipt_path: Path,
        operation_id: str,
        fingerprint: str,
        localization: LocalizationInput,
        metadata_template: MetadataTemplate,
        policy: BatchPolicy,
        state_items: dict[tuple[str, str], dict[str, Any]],
        result_class: str,
        manifest_path: Path | None,
        manifest_sha: str | None,
        error: str | None,
    ) -> None:
        ordered = [
            state_items[(row.target_language, row.media_id)]
            for row in localization.derivatives
            if (row.target_language, row.media_id) in state_items
        ]
        _atomic_json(
            receipt_path,
            {
                "schemaVersion": 1,
                "operationId": operation_id,
                "inputFingerprint": fingerprint,
                "resultClass": result_class,
                "localizationManifest": str(localization.manifest_path),
                "localizationManifestSha256": localization.manifest_sha256,
                "metadataTemplate": str(metadata_template.path),
                "metadataTemplateSha256": metadata_template.sha256,
                "policy": policy.to_public_dict(),
                "maximumActiveItems": 1,
                "itemCount": len(localization.derivatives),
                "completedCount": sum(row.get("status") == "COMPLETED" for row in ordered),
                "failedCount": sum(row.get("status") == "FAILED" for row in ordered),
                "items": ordered,
                "manifest": str(manifest_path) if manifest_path is not None else None,
                "manifestSha256": manifest_sha,
                "error": error,
            },
        )
