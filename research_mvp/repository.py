from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any

from .models import EvidenceItem, JobStatus, ResearchDossier, ResearchJob, SourceRef


class ConflictError(RuntimeError):
    pass


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _source(data: dict[str, Any]) -> SourceRef:
    return SourceRef(
        platform=str(data["platform"]),
        source_id=str(data["source_id"]),
        canonical_url=str(data["canonical_url"]),
    )


def _job(data: dict[str, Any]) -> ResearchJob:
    return ResearchJob(
        job_id=str(data["job_id"]),
        source=_source(data["source"]),
        config=dict(data["config"]),
        status=JobStatus(str(data["status"])),
        error=data.get("error"),
        dossier_version=data.get("dossier_version"),
    )


def _dossier(data: dict[str, Any]) -> ResearchDossier:
    return ResearchDossier(
        schema_version=str(data["schema_version"]),
        job_id=str(data["job_id"]),
        status=JobStatus(str(data["status"])),
        source=_source(data["source"]),
        facts=dict(data.get("facts", {})),
        evidence=tuple(EvidenceItem(**item) for item in data.get("evidence", [])),
        timeline=tuple(data.get("timeline", [])),
        patterns=tuple(data.get("patterns", [])),
        gaps=tuple(data.get("gaps", [])),
    )


class FileResearchRepository:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _job_dir(self, job_id: str) -> Path:
        if not _SAFE_ID.fullmatch(job_id):
            raise ValueError("unsafe job id")
        path = (self.workspace / job_id).resolve()
        if self.workspace not in path.parents:
            raise ValueError("job path escaped workspace")
        return path

    @staticmethod
    def _write_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        os.replace(temporary, path)

    def create_job(self, job: ResearchJob) -> ResearchJob:
        path = self._job_dir(job.job_id) / "job.json"
        if path.exists():
            current = self.load_job(job.job_id)
            if current != job:
                raise ConflictError(
                    f"job {job.job_id} already exists with different state"
                )
            return current
        self._write_atomic(path, job.to_dict())
        return job

    def save_job(self, job: ResearchJob) -> None:
        self._write_atomic(
            self._job_dir(job.job_id) / "job.json", job.to_dict()
        )

    def load_job(self, job_id: str) -> ResearchJob:
        data = json.loads(
            (self._job_dir(job_id) / "job.json").read_text(encoding="utf-8")
        )
        return _job(data)

    def commit_dossier(self, dossier: ResearchDossier) -> int:
        job_dir = self._job_dir(dossier.job_id)
        versions = [
            int(path.stem[1:])
            for path in job_dir.glob("v*.json")
            if path.stem[1:].isdigit()
        ]
        version = max(versions, default=0) + 1
        self._write_atomic(job_dir / f"v{version}.json", dossier.to_dict())
        job = self.load_job(dossier.job_id)
        self.save_job(
            replace(
                job,
                status=dossier.status,
                error=None,
                dossier_version=version,
            )
        )
        return version

    def load_dossier(
        self, job_id: str, version: int | None = None
    ) -> ResearchDossier:
        job = self.load_job(job_id)
        selected = version if version is not None else job.dossier_version
        if selected is None:
            raise FileNotFoundError(f"job {job_id} has no committed dossier")
        data = json.loads(
            (self._job_dir(job_id) / f"v{selected}.json").read_text(
                encoding="utf-8"
            )
        )
        return _dossier(data)
