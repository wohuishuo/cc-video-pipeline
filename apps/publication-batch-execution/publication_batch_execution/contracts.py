"""Immutable input contracts for guarded Publication Batch execution."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SHA256 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
AGGREGATE_FIELDS = {
    "schemaVersion", "localizationManifest", "localizationManifestSha256",
    "metadataTemplate", "metadataTemplateSha256", "targetLanguages",
    "expectedMediaIds", "targets", "public", "maximumActiveItems",
    "expectedDerivativeKeys", "items", "totalJobCount",
}
ITEM_FIELDS = {
    "ordinal", "targetLanguage", "mediaId", "derivativePath", "derivativeSha256",
    "metadataPath", "metadataSha256", "publicationPlan", "publicationPlanSha256", "jobCount",
}
PLAN_FIELDS = {"schemaVersion", "video", "metadata", "public", "jobs"}
VIDEO_FIELDS = {"path", "sha256", "size"}
METADATA_FIELDS = {"path", "sha256", "title"}
JOB_FIELDS = {"ordinal", "id", "platform", "account", "visibility", "credentialId"}


class BatchExecutionContractError(ValueError):
    """The batch cannot be executed without violating its public policy."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json(path: Path, label: str, code: str = "REJECTED_MALFORMED") -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise BatchExecutionContractError(code, f"{label} must be readable JSON") from error
    if not isinstance(value, dict):
        raise BatchExecutionContractError(code, f"{label} must be a JSON object")
    return value


def _verified_file(path_value: Any, sha_value: Any, label: str) -> tuple[Path, str]:
    if not isinstance(path_value, str) or not isinstance(sha_value, str) or SHA256.fullmatch(sha_value) is None:
        raise BatchExecutionContractError("REJECTED_MALFORMED", f"{label} lineage is malformed")
    path = Path(path_value).resolve()
    try:
        matches = path.is_file() and sha256_file(path) == sha_value
    except OSError:
        matches = False
    if not matches:
        raise BatchExecutionContractError("REJECTED_STALE", f"{label} fingerprint is stale")
    return path, sha_value


def _nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and len(set(value)) == len(value)
        and all(isinstance(row, str) and bool(row.strip()) for row in value)
    )


@dataclass(frozen=True, repr=False)
class ExecutionItem:
    ordinal: int
    target_language: str
    media_id: str
    derivative_path: Path
    derivative_sha256: str
    metadata_path: Path
    metadata_sha256: str
    plan_path: Path
    plan_sha256: str
    account: str
    credential_id: str
    job_id: str

    @property
    def identity(self) -> str:
        return f"{self.target_language}:{self.media_id}"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "targetLanguage": self.target_language,
            "mediaId": self.media_id,
            "derivativePath": str(self.derivative_path),
            "derivativeSha256": self.derivative_sha256,
            "metadataPath": str(self.metadata_path),
            "metadataSha256": self.metadata_sha256,
            "publicationPlan": str(self.plan_path),
            "publicationPlanSha256": self.plan_sha256,
            "platform": "youtube",
            "account": self.account,
            "credentialId": self.credential_id,
            "jobId": self.job_id,
        }

    def __repr__(self) -> str:
        return f"ExecutionItem(ordinal={self.ordinal}, identity={self.identity!r})"


@dataclass(frozen=True, repr=False)
class BatchExecutionInput:
    plan_path: Path
    plan_sha256: str
    vault_path: Path
    localization_manifest: Path
    localization_manifest_sha256: str
    metadata_template: Path
    metadata_template_sha256: str
    target_languages: tuple[str, ...]
    expected_media_ids: tuple[str, ...]
    expected_derivative_keys: tuple[str, ...]
    items: tuple[ExecutionItem, ...]
    total_job_count: int
    maximum_active_items: int = 1

    def fingerprint_value(self, executor_identity: str) -> dict[str, Any]:
        return {
            "batchPlanSha256": self.plan_sha256,
            "credentialVaultPath": str(self.vault_path),
            "executor": executor_identity,
        }

    def __repr__(self) -> str:
        return f"BatchExecutionInput(item_count={len(self.items)}, platform='youtube')"


def _validate_plan(item: dict[str, Any], target: dict[str, str]) -> ExecutionItem:
    try:
        ordinal = item["ordinal"]
        language = item["targetLanguage"]
        media_id = item["mediaId"]
        job_count = item["jobCount"]
    except KeyError as error:
        raise BatchExecutionContractError("REJECTED_MALFORMED", "batch item is incomplete") from error
    if (
        not isinstance(item, dict)
        or set(item) != ITEM_FIELDS
        or isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(language, str)
        or not language.strip()
        or not isinstance(media_id, str)
        or not media_id.strip()
        or job_count != 1
    ):
        raise BatchExecutionContractError("REJECTED_MALFORMED", "batch item schema is invalid")
    derivative, derivative_sha = _verified_file(item["derivativePath"], item["derivativeSha256"], "derivative")
    metadata, metadata_sha = _verified_file(item["metadataPath"], item["metadataSha256"], "rendered metadata")
    plan, plan_sha = _verified_file(item["publicationPlan"], item["publicationPlanSha256"], "Publication Plan")
    value = _json(plan, "Publication Plan", "REJECTED_STALE")
    if set(value) != PLAN_FIELDS or value.get("schemaVersion") != 1 or value.get("public") is not False:
        raise BatchExecutionContractError("REJECTED_POLICY", "Publication Plan must be private and supported")
    video = value.get("video"); metadata_fact = value.get("metadata"); jobs = value.get("jobs")
    if (
        not isinstance(video, dict)
        or set(video) != VIDEO_FIELDS
        or not isinstance(metadata_fact, dict)
        or set(metadata_fact) != METADATA_FIELDS
        or not isinstance(jobs, list)
        or len(jobs) != 1
    ):
        raise BatchExecutionContractError("REJECTED_MALFORMED", "Publication Plan schema is invalid")
    job = jobs[0]
    if not isinstance(job, dict) or set(job) != JOB_FIELDS:
        raise BatchExecutionContractError("REJECTED_POLICY", "Publication job policy is unsupported")
    try:
        video_path = Path(str(video["path"])).resolve()
        metadata_path = Path(str(metadata_fact["path"])).resolve()
        video_size = video["size"]
        title = metadata_fact["title"]
        account = job["account"]
        credential_id = job["credentialId"]
        job_id = job["id"]
    except (KeyError, TypeError, ValueError) as error:
        raise BatchExecutionContractError("REJECTED_MALFORMED", "Publication Plan fields are invalid") from error
    policy_valid = (
        job.get("ordinal") == 1
        and job.get("platform") == "youtube"
        and job.get("visibility") == "private-or-draft"
        and isinstance(account, str)
        and 0 < len(account.strip()) <= 128
        and isinstance(credential_id, str)
        and IDENTIFIER.fullmatch(credential_id) is not None
        and account == target["account"]
        and credential_id == target["credentialId"]
    )
    if not policy_valid:
        raise BatchExecutionContractError("REJECTED_POLICY", "only credential-backed private YouTube jobs may execute")
    if (
        video_path != derivative
        or video.get("sha256") != derivative_sha
        or isinstance(video_size, bool)
        or not isinstance(video_size, int)
        or video_size != derivative.stat().st_size
        or metadata_path != metadata
        or metadata_fact.get("sha256") != metadata_sha
    ):
        raise BatchExecutionContractError("REJECTED_STALE", "Publication Plan lineage is stale")
    metadata_value = _json(metadata, "rendered metadata", "REJECTED_STALE")
    if not isinstance(title, str) or not title.strip() or metadata_value.get("title") != title:
        raise BatchExecutionContractError("REJECTED_STALE", "Publication metadata title is stale")
    expected_job_id = hashlib.sha256(
        f"{derivative_sha}\0{metadata_sha}\0youtube\0{account.strip()}\0private-or-draft\0{credential_id}".encode("utf-8")
    ).hexdigest()
    if not isinstance(job_id, str) or job_id != expected_job_id:
        raise BatchExecutionContractError("REJECTED_STALE", "Publication job identity is stale")
    return ExecutionItem(
        ordinal, language.strip(), media_id.strip(), derivative, derivative_sha,
        metadata, metadata_sha, plan, plan_sha, account.strip(), credential_id, job_id,
    )


def load_batch_plan(
    path: str | Path,
    confirmation: str,
    credential_vault_path: str | Path,
) -> BatchExecutionInput:
    plan_path = Path(path).resolve()
    if not isinstance(confirmation, str) or SHA256.fullmatch(confirmation) is None:
        raise BatchExecutionContractError("REJECTED_CONFIRMATION", "confirmation must be a SHA-256")
    if not plan_path.is_file():
        raise BatchExecutionContractError("REJECTED_MALFORMED", "Publication Batch Plan does not exist")
    try:
        actual_sha = sha256_file(plan_path)
    except OSError as error:
        raise BatchExecutionContractError("REJECTED_MALFORMED", "Publication Batch Plan is unreadable") from error
    if actual_sha != confirmation:
        raise BatchExecutionContractError("REJECTED_CONFIRMATION", "confirmation must equal Publication Batch Plan SHA-256")
    vault_path = Path(credential_vault_path).resolve()
    if not vault_path.is_file():
        raise BatchExecutionContractError("REJECTED_MALFORMED", "Credential Vault does not exist")
    value = _json(plan_path, "Publication Batch Plan")
    if set(value) != AGGREGATE_FIELDS or value.get("schemaVersion") != 1:
        raise BatchExecutionContractError("REJECTED_MALFORMED", "Publication Batch Plan schema is invalid")
    if value.get("public") is not False or value.get("maximumActiveItems") != 1:
        raise BatchExecutionContractError("REJECTED_POLICY", "Publication Batch Plan is not private and serial")
    targets = value.get("targets")
    if (
        not isinstance(targets, list)
        or len(targets) != 1
        or not isinstance(targets[0], dict)
        or set(targets[0]) != {"platform", "account", "credentialId"}
        or targets[0].get("platform") != "youtube"
        or not isinstance(targets[0].get("account"), str)
        or not targets[0]["account"].strip()
        or not isinstance(targets[0].get("credentialId"), str)
        or IDENTIFIER.fullmatch(targets[0]["credentialId"]) is None
    ):
        raise BatchExecutionContractError("REJECTED_POLICY", "batch execution requires one credential-backed YouTube target")
    localization, localization_sha = _verified_file(
        value.get("localizationManifest"), value.get("localizationManifestSha256"), "Localization Manifest"
    )
    template, template_sha = _verified_file(
        value.get("metadataTemplate"), value.get("metadataTemplateSha256"), "metadata template"
    )
    languages = value.get("targetLanguages"); media_ids = value.get("expectedMediaIds")
    expected_keys = value.get("expectedDerivativeKeys"); rows = value.get("items")
    if not _nonempty_strings(languages) or not _nonempty_strings(media_ids):
        raise BatchExecutionContractError("REJECTED_MALFORMED", "batch language or media coverage is invalid")
    derived_keys = [f"{language}:{media_id}" for language in languages for media_id in media_ids]
    if expected_keys != derived_keys or not isinstance(rows, list) or len(rows) != len(derived_keys):
        raise BatchExecutionContractError("REJECTED_MALFORMED", "batch derivative coverage is invalid")
    items: list[ExecutionItem] = []
    for expected_ordinal, row in enumerate(rows, 1):
        item = _validate_plan(row, targets[0])
        if item.ordinal != expected_ordinal or item.identity != derived_keys[expected_ordinal - 1]:
            raise BatchExecutionContractError("REJECTED_MALFORMED", "batch derivative order is invalid")
        items.append(item)
    total_job_count = value.get("totalJobCount")
    if isinstance(total_job_count, bool) or not isinstance(total_job_count, int) or total_job_count != len(items):
        raise BatchExecutionContractError("REJECTED_MALFORMED", "batch job coverage is invalid")
    return BatchExecutionInput(
        plan_path, actual_sha, vault_path, localization, localization_sha, template,
        template_sha, tuple(languages), tuple(media_ids), tuple(expected_keys), tuple(items),
        total_job_count,
    )
