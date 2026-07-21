from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from hashlib import sha256
import json
from urllib.parse import urlsplit


class JobStatus(StrEnum):
    PENDING = "pending"
    COLLECTING = "collecting"
    COMPLETE = "complete"
    COMPLETE_WITH_GAPS = "complete_with_gaps"
    FAILED = "failed"


@dataclass(frozen=True)
class SourceRef:
    platform: str
    source_id: str
    canonical_url: str

    def __post_init__(self) -> None:
        parts = urlsplit(self.canonical_url)
        if parts.username or parts.password:
            raise ValueError("canonical_url must not contain credentials")
        if not self.platform or not self.source_id or not self.canonical_url:
            raise ValueError("source identity fields must be non-empty")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceItem:
    kind: str
    locator: str
    provenance: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchDossier:
    schema_version: str
    job_id: str
    status: JobStatus
    source: SourceRef
    facts: dict[str, object] = field(default_factory=dict)
    evidence: tuple[EvidenceItem, ...] = ()
    timeline: tuple[dict[str, object], ...] = ()
    patterns: tuple[dict[str, object], ...] = ()
    gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {JobStatus.COMPLETE, JobStatus.COMPLETE_WITH_GAPS}:
            raise ValueError("dossier status must be terminal and useful")
        if self.status == JobStatus.COMPLETE and self.gaps:
            raise ValueError("complete dossier cannot contain gaps")
        if self.status == JobStatus.COMPLETE_WITH_GAPS and not self.gaps:
            raise ValueError("complete_with_gaps dossier must name gaps")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "job_id": self.job_id,
            "status": self.status.value,
            "source": self.source.to_dict(),
            "facts": self.facts,
            "evidence": [item.to_dict() for item in self.evidence],
            "timeline": list(self.timeline),
            "patterns": list(self.patterns),
            "gaps": list(self.gaps),
        }


@dataclass(frozen=True)
class ResearchJob:
    job_id: str
    source: SourceRef
    config: dict[str, object]
    status: JobStatus = JobStatus.PENDING
    error: str | None = None
    dossier_version: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "source": self.source.to_dict(),
            "config": self.config,
            "status": self.status.value,
            "error": self.error,
            "dossier_version": self.dossier_version,
        }


def stable_job_id(source: SourceRef, config: dict[str, object]) -> str:
    payload = {"source": source.to_dict(), "config": config}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()[:20]
