"""Immutable job records and durable stage receipts for localization work."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from types import MappingProxyType
from typing import Any, Literal, Mapping


StageStatus = Literal["pending", "running", "completed", "failed"]
_SCHEMA_VERSION = 1
_BATCH_SCHEMA_VERSION = 2
_SOURCE_ID = re.compile(r"^\[([^\]]+)\]")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_schema(
    value: dict[str, Any],
    expected_keys: set[str],
    *,
    schema_version: int = _SCHEMA_VERSION,
    schema_name: str = "",
) -> None:
    if value.get("schema_version") != schema_version:
        prefix = f"unsupported {schema_name} schema version" if schema_name else "unsupported schema version"
        raise ValueError(f"{prefix}: {value.get('schema_version')}")
    actual_keys = set(value)
    missing = expected_keys - actual_keys
    unexpected = actual_keys - expected_keys
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing fields: {', '.join(sorted(missing))}")
        if unexpected:
            details.append(f"unexpected fields: {', '.join(sorted(unexpected))}")
        raise ValueError("invalid receipt schema: " + "; ".join(details))


def _is_utc_iso_timestamp(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).tzinfo == timezone.utc
    except ValueError:
        return False


def _string_map(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise ValueError(f"{name} must be a mapping of strings")
    return dict(value)


def _validate_stage_lifecycle(
    status: object,
    adapter: object,
    inputs: object,
    outputs: object,
    started_at: str | None,
    completed_at: str | None,
    error: object,
) -> None:
    if status not in {"pending", "running", "completed", "failed"}:
        raise ValueError(f"invalid stage status: {status}")
    if not isinstance(adapter, str) or not adapter:
        raise ValueError("adapter must be a non-empty string")
    _string_map(inputs, "inputs")
    _string_map(outputs, "outputs")
    if status == "pending":
        if started_at is not None or completed_at is not None or error is not None:
            raise ValueError("pending stage cannot have timestamps or an error")
    elif status == "running":
        if not _is_utc_iso_timestamp(started_at) or completed_at is not None or error is not None:
            raise ValueError("running stage requires a start timestamp only")
    elif status == "completed":
        if not _is_utc_iso_timestamp(started_at) or not _is_utc_iso_timestamp(completed_at):
            raise ValueError("completed stage requires timestamps")
        if error is not None:
            raise ValueError("completed stage cannot have an error")
        if not outputs:
            raise ValueError("completed stage requires at least one output")
    else:
        if not _is_utc_iso_timestamp(started_at) or not _is_utc_iso_timestamp(completed_at):
            raise ValueError("failed stage requires timestamps")
        if not _string_map(error, "error"):
            raise ValueError("failed stage requires an error")


def _validate_job_identity(id: object, source: object, source_sha256: object) -> None:
    if not isinstance(id, str) or not id.strip():
        raise ValueError("job ID must be a non-empty string")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source path must be a non-empty string")
    if not isinstance(source_sha256, str) or _SHA256.fullmatch(source_sha256) is None:
        raise ValueError("source SHA-256 must be 64 lowercase hexadecimal characters")
    source_id = _SOURCE_ID.match(Path(source).name)
    if source_id is None:
        raise ValueError("source path filename must begin with a source ID")
    if source_id.group(1) != id:
        raise ValueError(f"source ID {source_id.group(1)} does not match job ID {id}")


@dataclass(frozen=True)
class Segment:
    """A timestamped transcript segment whose identity belongs to ASR."""

    id: int
    start: float
    end: float
    text: str
    words: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Segment":
        return cls(
            id=int(value["id"]),
            start=float(value["start"]),
            end=float(value["end"]),
            text=str(value["text"]),
            words=list(value["words"]),
        )


@dataclass(frozen=True)
class StageRecord:
    """The sole mutable receipt for a single adapter stage."""

    status: StageStatus
    adapter: str
    inputs: Mapping[str, str]
    outputs: Mapping[str, str]
    started_at: str | None = None
    completed_at: str | None = None
    error: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        _validate_stage_lifecycle(
            self.status,
            self.adapter,
            self.inputs,
            self.outputs,
            self.started_at,
            self.completed_at,
            self.error,
        )
        object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))
        if self.error is not None:
            object.__setattr__(self, "error", MappingProxyType(dict(self.error)))

    @classmethod
    def pending(cls, adapter: str) -> "StageRecord":
        return cls(status="pending", adapter=adapter, inputs={}, outputs={})

    @classmethod
    def running(
        cls, adapter: str, inputs: dict[str, str], outputs: dict[str, str] | None = None
    ) -> "StageRecord":
        return cls(
            status="running",
            adapter=adapter,
            inputs=dict(inputs),
            outputs=dict(outputs or {}),
            started_at=_utc_now(),
        )

    @classmethod
    def completed(
        cls, adapter: str, inputs: dict[str, str], outputs: dict[str, str]
    ) -> "StageRecord":
        now = _utc_now()
        return cls(
            status="completed",
            adapter=adapter,
            inputs=dict(inputs),
            outputs=dict(outputs),
            started_at=now,
            completed_at=now,
        )

    @classmethod
    def failed(
        cls,
        adapter: str,
        inputs: dict[str, str],
        outputs: dict[str, str],
        error: dict[str, str],
    ) -> "StageRecord":
        now = _utc_now()
        return cls(
            status="failed",
            adapter=adapter,
            inputs=dict(inputs),
            outputs=dict(outputs),
            started_at=now,
            completed_at=now,
            error=dict(error),
        )

    def is_reusable(
        self, current_inputs: dict[str, str], *, adapter: str
    ) -> bool:
        return (
            self.status == "completed"
            and self.inputs == current_inputs
            and self.adapter == adapter
            and bool(self.outputs)
            and all(
                Path(path).is_file() and Path(path).stat().st_size > 0
                for path in self.outputs.values()
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "status": self.status,
            "adapter": self.adapter,
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": None if self.error is None else dict(self.error),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StageRecord":
        expected_keys = {
            "schema_version",
            "status",
            "adapter",
            "inputs",
            "outputs",
            "started_at",
            "completed_at",
            "error",
        }
        _require_schema(value, expected_keys)
        status = value["status"]
        adapter = value["adapter"]
        started_at = value["started_at"]
        completed_at = value["completed_at"]
        error = value["error"]
        return cls(
            status=status,
            adapter=adapter,
            inputs=_string_map(value["inputs"], "inputs"),
            outputs=_string_map(value["outputs"], "outputs"),
            started_at=started_at,
            completed_at=completed_at,
            error=error,
        )


@dataclass(frozen=True)
class JobRecord:
    """One immutable source video and its independently recoverable stages."""

    id: str
    source: str
    source_sha256: str
    stages: dict[str, StageRecord] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_job_identity(self.id, self.source, self.source_sha256)
        if not isinstance(self.stages, dict):
            raise ValueError("stages must be a mapping")
        if not all(
            isinstance(name, str) and name and isinstance(stage, StageRecord)
            for name, stage in self.stages.items()
        ):
            raise ValueError("stages must map non-empty names to StageRecord values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "id": self.id,
            "source": self.source,
            "source_sha256": self.source_sha256,
            "stages": {name: stage.to_dict() for name, stage in self.stages.items()},
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "JobRecord":
        _require_schema(
            value, {"schema_version", "id", "source", "source_sha256", "stages"}
        )
        stages = value["stages"]
        if not isinstance(stages, dict):
            raise ValueError("stages must be a mapping")
        return cls(
            id=value["id"],
            source=value["source"],
            source_sha256=value["source_sha256"],
            stages={
                str(name): StageRecord.from_dict(stage)
                for name, stage in stages.items()
            },
        )


@dataclass(frozen=True)
class BatchManifest:
    """The exact source set resolved from a corrected URL manifest."""

    manifest: str
    expected_ids: tuple[str, ...]
    jobs: tuple[JobRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, str) or not self.manifest.strip():
            raise ValueError("manifest path must be a non-empty string")
        if not isinstance(self.expected_ids, (list, tuple)) or not self.expected_ids:
            raise ValueError("batch manifest requires at least one expected ID")
        expected_ids = tuple(self.expected_ids)
        if not all(isinstance(video_id, str) and video_id for video_id in expected_ids):
            raise ValueError("expected IDs must be non-empty strings")
        duplicate_expected_ids = sorted(
            {video_id for video_id in expected_ids if expected_ids.count(video_id) > 1}
        )
        if duplicate_expected_ids:
            raise ValueError(
                f"duplicate expected ID: {', '.join(duplicate_expected_ids)}"
            )
        if not isinstance(self.jobs, (list, tuple)) or not self.jobs:
            raise ValueError("batch manifest requires at least one job")
        jobs = tuple(self.jobs)
        if not all(isinstance(job, JobRecord) for job in jobs):
            raise ValueError("jobs must contain JobRecord values")
        ids = [job.id for job in jobs]
        sources = [os.path.normcase(os.path.normpath(job.source)) for job in jobs]
        duplicate_ids = sorted({job_id for job_id in ids if ids.count(job_id) > 1})
        duplicate_sources = sorted(
            {source for source in sources if sources.count(source) > 1}
        )
        if duplicate_ids:
            raise ValueError(f"duplicate job ID: {', '.join(duplicate_ids)}")
        if duplicate_sources:
            raise ValueError(f"duplicate source identity: {', '.join(duplicate_sources)}")
        missing_ids = sorted(set(expected_ids) - set(ids))
        unexpected_ids = sorted(set(ids) - set(expected_ids))
        if missing_ids or unexpected_ids:
            details: list[str] = []
            if missing_ids:
                details.append(f"missing job IDs: {', '.join(missing_ids)}")
            if unexpected_ids:
                details.append(f"unexpected job IDs: {', '.join(unexpected_ids)}")
            raise ValueError("; ".join(details))
        object.__setattr__(self, "expected_ids", expected_ids)
        object.__setattr__(self, "jobs", jobs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _BATCH_SCHEMA_VERSION,
            "manifest": self.manifest,
            "expected_ids": list(self.expected_ids),
            "jobs": [job.to_dict() for job in self.jobs],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BatchManifest":
        _require_schema(
            value,
            {"schema_version", "manifest", "expected_ids", "jobs"},
            schema_version=_BATCH_SCHEMA_VERSION,
            schema_name="batch",
        )
        if not isinstance(value["jobs"], list):
            raise ValueError("jobs must be a list")
        return cls(
            manifest=value["manifest"],
            expected_ids=value["expected_ids"],
            jobs=[JobRecord.from_dict(job) for job in value["jobs"]],
        )


def sha256_file(path: str | Path) -> str:
    """Return the content fingerprint of a file without loading it all at once."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: str | Path, value: Any) -> None:
    """Durably replace a JSON receipt, leaving no temporary file after failure."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
