# Research MVP Domain Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a clean, independently runnable research MVP domain core that turns one normalized source into one committed research dossier using substitute connectors and evidence collectors.

**Architecture:** A Python package owns research job lifecycle and dossier versions. Source connectors and evidence collectors are ports; tests use fakes so domain behavior is proven without network access, cookies, FFmpeg, or large models. A filesystem repository atomically commits JSON state, while the CLI exposes `create`, `status`, `show`, and `retry`.

**Tech Stack:** Python 3.12 standard library, `unittest`, `dataclasses`, `typing.Protocol`, JSON, PowerShell invocation through `tools/.venv/Scripts/python.exe`.

## Global Constraints

- Existing scripts are behavioral evidence only; do not import legacy pipeline modules.
- Scene detection, loudness analysis, frame extraction, authentication, and model routing remain private adapters or policies.
- A dossier cannot be committed without a stable source identity.
- Credentials and platform sessions never appear in state, logs, or dossier JSON.
- All committed paths must remain inside the selected research workspace.
- Domain tests must not use network access, cookies, FFmpeg, or model downloads.
- Use standard-library dependencies only for the domain core.
- Do not create empty scaffolds for later MVPs.

---

## File Structure

```text
research_mvp/
  __init__.py          public domain exports
  __main__.py          module entry point
  models.py            immutable source/evidence/dossier values and job lifecycle
  ports.py             connector and evidence-collector protocols
  repository.py        atomic filesystem state owner
  service.py           create, retry, status, and show use cases
  cli.py               JSON command-line interface
tests/
  research_mvp/
    __init__.py
    fakes.py
    test_models.py
    test_repository.py
    test_service.py
    test_cli.py
```

## Task 1: Stable Source Identity and Domain Values

**Files:**
- Create: `research_mvp/__init__.py`
- Create: `research_mvp/models.py`
- Create: `tests/research_mvp/__init__.py`
- Create: `tests/research_mvp/test_models.py`

**Interfaces:**
- Consumes: raw source string and normalized connector result.
- Produces: `SourceRef`, `EvidenceItem`, `ResearchDossier`, `ResearchJob`, `JobStatus`, `stable_job_id(source, config)`.

- [ ] **Step 1: Write failing source-identity and redaction tests**

```python
# tests/research_mvp/test_models.py
import unittest
from research_mvp.models import SourceRef, stable_job_id


class SourceIdentityTests(unittest.TestCase):
    def test_equivalent_source_has_stable_job_id(self):
        source = SourceRef(
            platform="bilibili",
            source_id="BV1abc",
            canonical_url="https://www.bilibili.com/video/BV1abc",
        )
        self.assertEqual(
            stable_job_id(source, {"language": "zh"}),
            stable_job_id(source, {"language": "zh"}),
        )

    def test_evidence_affecting_configuration_changes_job_id(self):
        source = SourceRef("local", "sha256:abc", "file:///clip.mp4")
        self.assertNotEqual(
            stable_job_id(source, {"language": "zh"}),
            stable_job_id(source, {"language": "en"}),
        )

    def test_source_ref_rejects_secret_bearing_url(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            SourceRef("example", "123", "https://user:secret@example.com/v/123")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and observe RED**

Run:

```powershell
.\tools\.venv\Scripts\python.exe -m unittest tests.research_mvp.test_models -v
```

Expected: `ModuleNotFoundError: No module named 'research_mvp'`.

- [ ] **Step 3: Implement immutable domain values and lifecycle validation**

```python
# research_mvp/models.py
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
```

```python
# research_mvp/__init__.py
from .models import EvidenceItem, JobStatus, ResearchDossier, ResearchJob, SourceRef, stable_job_id

__all__ = [
    "EvidenceItem",
    "JobStatus",
    "ResearchDossier",
    "ResearchJob",
    "SourceRef",
    "stable_job_id",
]
```

```python
# tests/research_mvp/__init__.py
```

- [ ] **Step 4: Run focused tests and observe GREEN**

Run:

```powershell
.\tools\.venv\Scripts\python.exe -m unittest tests.research_mvp.test_models -v
```

Expected: `Ran 3 tests` and `OK`.

- [ ] **Step 5: Commit the domain values**

```powershell
git add research_mvp tests/research_mvp
git commit -m "feat(research): define source and dossier domain values"
```

## Task 2: Atomic Research State Repository

**Files:**
- Create: `research_mvp/repository.py`
- Create: `tests/research_mvp/test_repository.py`

**Interfaces:**
- Consumes: `ResearchJob`, `ResearchDossier`, workspace `Path`.
- Produces: `FileResearchRepository.create_job`, `save_job`, `load_job`, `commit_dossier`, and `load_dossier`.

- [ ] **Step 1: Write failing ownership, idempotency, conflict, and path tests**

```python
# tests/research_mvp/test_repository.py
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research_mvp.models import JobStatus, ResearchDossier, ResearchJob, SourceRef
from research_mvp.repository import ConflictError, FileResearchRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.repo = FileResearchRepository(Path(self.tmp.name))
        self.source = SourceRef("local", "sha256:abc", "file:///clip.mp4")
        self.job = ResearchJob("job-1", self.source, {"language": "zh"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_is_idempotent_for_same_job(self):
        self.repo.create_job(self.job)
        self.repo.create_job(self.job)
        self.assertEqual(self.repo.load_job("job-1"), self.job)

    def test_create_rejects_conflicting_existing_job(self):
        self.repo.create_job(self.job)
        changed = ResearchJob("job-1", self.source, {"language": "en"})
        with self.assertRaises(ConflictError):
            self.repo.create_job(changed)

    def test_job_id_cannot_escape_workspace(self):
        with self.assertRaises(ValueError):
            self.repo.load_job("../outside")

    def test_committed_dossier_round_trips(self):
        self.repo.create_job(self.job)
        dossier = ResearchDossier("1", "job-1", JobStatus.COMPLETE, self.source)
        version = self.repo.commit_dossier(dossier)
        self.assertEqual(version, 1)
        self.assertEqual(self.repo.load_dossier("job-1", 1), dossier)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run repository tests and observe RED**

Run:

```powershell
.\tools\.venv\Scripts\python.exe -m unittest tests.research_mvp.test_repository -v
```

Expected: import failure for `research_mvp.repository`.

- [ ] **Step 3: Implement atomic JSON state ownership**

Implement `research_mvp/repository.py` with these exact public behaviors:

```python
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from .models import EvidenceItem, JobStatus, ResearchDossier, ResearchJob, SourceRef


class ConflictError(RuntimeError):
    pass


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _source(data: dict[str, str]) -> SourceRef:
    return SourceRef(**data)


def _job(data: dict[str, object]) -> ResearchJob:
    return ResearchJob(
        job_id=str(data["job_id"]),
        source=_source(data["source"]),
        config=dict(data["config"]),
        status=JobStatus(str(data["status"])),
        error=data.get("error"),
        dossier_version=data.get("dossier_version"),
    )


def _dossier(data: dict[str, object]) -> ResearchDossier:
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
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        os.replace(temporary, path)

    def create_job(self, job: ResearchJob) -> ResearchJob:
        path = self._job_dir(job.job_id) / "job.json"
        if path.exists():
            current = self.load_job(job.job_id)
            if current != job:
                raise ConflictError(f"job {job.job_id} already exists with different state")
            return current
        self._write_atomic(path, job.to_dict())
        return job

    def save_job(self, job: ResearchJob) -> None:
        self._write_atomic(self._job_dir(job.job_id) / "job.json", job.to_dict())

    def load_job(self, job_id: str) -> ResearchJob:
        data = json.loads((self._job_dir(job_id) / "job.json").read_text(encoding="utf-8"))
        return _job(data)

    def commit_dossier(self, dossier: ResearchDossier) -> int:
        job_dir = self._job_dir(dossier.job_id)
        versions = [int(path.stem[1:]) for path in job_dir.glob("v*.json") if path.stem[1:].isdigit()]
        version = max(versions, default=0) + 1
        self._write_atomic(job_dir / f"v{version}.json", dossier.to_dict())
        job = self.load_job(dossier.job_id)
        self.save_job(replace(job, status=dossier.status, error=None, dossier_version=version))
        return version

    def load_dossier(self, job_id: str, version: int | None = None) -> ResearchDossier:
        job = self.load_job(job_id)
        selected = version if version is not None else job.dossier_version
        if selected is None:
            raise FileNotFoundError(f"job {job_id} has no committed dossier")
        data = json.loads((self._job_dir(job_id) / f"v{selected}.json").read_text(encoding="utf-8"))
        return _dossier(data)
```

- [ ] **Step 4: Run repository and model tests**

Run:

```powershell
.\tools\.venv\Scripts\python.exe -m unittest tests.research_mvp.test_models tests.research_mvp.test_repository -v
```

Expected: `Ran 7 tests` and `OK`.

- [ ] **Step 5: Commit repository ownership**

```powershell
git add research_mvp/repository.py tests/research_mvp/test_repository.py
git commit -m "feat(research): add atomic research state repository"
```

## Task 3: Ports, Fakes, and Research Use Cases

**Files:**
- Create: `research_mvp/ports.py`
- Create: `research_mvp/service.py`
- Create: `tests/research_mvp/fakes.py`
- Create: `tests/research_mvp/test_service.py`

**Interfaces:**
- Consumes: `SourceConnector.resolve(raw_source)`, `EvidenceCollector.collect(source, workspace)`.
- Produces: `ResearchService.create`, `retry`, `status`, and `show`.

- [ ] **Step 1: Write failing lifecycle tests**

Create fakes that never contain credential fields:

```python
# tests/research_mvp/fakes.py
from pathlib import Path
from research_mvp.models import EvidenceItem, SourceRef


class FakeConnector:
    def __init__(self, source: SourceRef):
        self.source = source

    def resolve(self, raw_source: str) -> SourceRef:
        return self.source

    def facts(self, source: SourceRef) -> dict[str, object]:
        return {"title": "Fixture video", "duration_seconds": 12}


class FakeCollector:
    def __init__(self, *, gaps=(), error: Exception | None = None):
        self.gaps = tuple(gaps)
        self.error = error

    def collect(self, source: SourceRef, workspace: Path):
        if self.error:
            raise self.error
        workspace.mkdir(parents=True, exist_ok=True)
        transcript = workspace / "transcript.json"
        transcript.write_text('{"segments": []}\n', encoding="utf-8")
        return (
            (EvidenceItem("transcript", str(transcript), {"adapter": "fake"}),),
            self.gaps,
        )
```

```python
# tests/research_mvp/test_service.py
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research_mvp.models import JobStatus, SourceRef
from research_mvp.repository import FileResearchRepository
from research_mvp.service import ResearchService
from tests.research_mvp.fakes import FakeCollector, FakeConnector


class ResearchServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.repo = FileResearchRepository(self.workspace)
        self.source = SourceRef("bilibili", "BV1abc", "https://www.bilibili.com/video/BV1abc")

    def tearDown(self):
        self.tmp.cleanup()

    def service(self, collector):
        return ResearchService(self.repo, FakeConnector(self.source), collector)

    def test_create_commits_useful_dossier(self):
        dossier = self.service(FakeCollector()).create("raw", {"language": "zh"})
        self.assertEqual(dossier.status, JobStatus.COMPLETE)
        self.assertEqual(dossier.facts["title"], "Fixture video")

    def test_optional_gap_is_explicit_terminal_result(self):
        dossier = self.service(FakeCollector(gaps=("visual_evidence_unavailable",))).create("raw", {})
        self.assertEqual(dossier.status, JobStatus.COMPLETE_WITH_GAPS)
        self.assertEqual(dossier.gaps, ("visual_evidence_unavailable",))

    def test_failure_can_be_retried_without_new_job_identity(self):
        failing = self.service(FakeCollector(error=RuntimeError("collector unavailable")))
        with self.assertRaisesRegex(RuntimeError, "collector unavailable"):
            failing.create("raw", {})
        job = next(self.workspace.iterdir()).name
        self.assertEqual(self.repo.load_job(job).status, JobStatus.FAILED)
        recovered = self.service(FakeCollector()).retry(job)
        self.assertEqual(recovered.job_id, job)
        self.assertEqual(recovered.status, JobStatus.COMPLETE)

    def test_same_source_and_config_is_idempotent(self):
        service = self.service(FakeCollector())
        first = service.create("raw", {"language": "zh"})
        second = service.create("raw", {"language": "zh"})
        self.assertEqual(first, second)
        self.assertEqual(self.repo.load_job(first.job_id).dossier_version, 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run lifecycle tests and observe RED**

Run:

```powershell
.\tools\.venv\Scripts\python.exe -m unittest tests.research_mvp.test_service -v
```

Expected: import failure for `research_mvp.service`.

- [ ] **Step 3: Define ports and implement minimal use cases**

```python
# research_mvp/ports.py
from pathlib import Path
from typing import Protocol
from .models import EvidenceItem, SourceRef


class SourceConnector(Protocol):
    def resolve(self, raw_source: str) -> SourceRef: ...
    def facts(self, source: SourceRef) -> dict[str, object]: ...


class EvidenceCollector(Protocol):
    def collect(
        self, source: SourceRef, workspace: Path
    ) -> tuple[tuple[EvidenceItem, ...], tuple[str, ...]]: ...
```

```python
# research_mvp/service.py
from dataclasses import replace
from pathlib import Path

from .models import JobStatus, ResearchDossier, ResearchJob, stable_job_id
from .ports import EvidenceCollector, SourceConnector
from .repository import ConflictError, FileResearchRepository


class ResearchService:
    def __init__(self, repository: FileResearchRepository, connector: SourceConnector, collector: EvidenceCollector):
        self.repository = repository
        self.connector = connector
        self.collector = collector

    def create(self, raw_source: str, config: dict[str, object]) -> ResearchDossier:
        source = self.connector.resolve(raw_source)
        job_id = stable_job_id(source, config)
        job = ResearchJob(job_id, source, config)
        try:
            current = self.repository.create_job(job)
        except ConflictError:
            raise
        if current.dossier_version is not None:
            return self.repository.load_dossier(job_id)
        return self._run(current)

    def retry(self, job_id: str) -> ResearchDossier:
        job = self.repository.load_job(job_id)
        if job.status != JobStatus.FAILED:
            if job.dossier_version is not None:
                return self.repository.load_dossier(job_id)
            raise ValueError("only failed or completed jobs can be retried idempotently")
        return self._run(replace(job, status=JobStatus.PENDING, error=None))

    def status(self, job_id: str) -> ResearchJob:
        return self.repository.load_job(job_id)

    def show(self, job_id: str) -> ResearchDossier:
        return self.repository.load_dossier(job_id)

    def _run(self, job: ResearchJob) -> ResearchDossier:
        collecting = replace(job, status=JobStatus.COLLECTING, error=None)
        self.repository.save_job(collecting)
        try:
            facts = self.connector.facts(job.source)
            evidence, gaps = self.collector.collect(job.source, self.repository.workspace / job.job_id / "evidence")
            status = JobStatus.COMPLETE_WITH_GAPS if gaps else JobStatus.COMPLETE
            dossier = ResearchDossier(
                schema_version="1",
                job_id=job.job_id,
                status=status,
                source=job.source,
                facts=facts,
                evidence=evidence,
                gaps=gaps,
            )
            self.repository.commit_dossier(dossier)
            return dossier
        except Exception as error:
            self.repository.save_job(replace(job, status=JobStatus.FAILED, error=str(error)))
            raise
```

- [ ] **Step 4: Run all domain tests**

Run:

```powershell
.\tools\.venv\Scripts\python.exe -m unittest discover -s tests/research_mvp -t . -v
```

Expected: `Ran 11 tests` and `OK`.

- [ ] **Step 5: Commit the verified domain use cases**

```powershell
git add research_mvp/ports.py research_mvp/service.py tests/research_mvp/fakes.py tests/research_mvp/test_service.py
git commit -m "feat(research): prove dossier lifecycle with substitute ports"
```

## Task 4: JSON CLI and Independent Demonstration

**Files:**
- Create: `research_mvp/cli.py`
- Create: `research_mvp/__main__.py`
- Create: `tests/research_mvp/test_cli.py`
- Create: `research_mvp/demo_adapters.py`

**Interfaces:**
- Consumes: `python -m research_mvp --workspace PATH create SOURCE [--language LANG]`.
- Produces: JSON on stdout, non-zero exit code and JSON error on stderr, plus `status`, `show`, and `retry` commands.

- [ ] **Step 1: Write a failing subprocess acceptance test**

```python
# tests/research_mvp/test_cli.py
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class CliTests(unittest.TestCase):
    def test_demo_create_outputs_committed_json_dossier(self):
        with TemporaryDirectory() as workspace:
            result = subprocess.run(
                [sys.executable, "-m", "research_mvp", "--workspace", workspace, "create", "demo:video-1"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["source"]["platform"], "demo")
            self.assertIn(payload["status"], {"complete", "complete_with_gaps"})
            self.assertNotIn("secret", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the CLI test and observe RED**

Run:

```powershell
.\tools\.venv\Scripts\python.exe -m unittest tests.research_mvp.test_cli -v
```

Expected: non-zero subprocess result because `research_mvp.__main__` does not exist.

- [ ] **Step 3: Implement bounded demo adapters and CLI wiring**

```python
# research_mvp/demo_adapters.py
from hashlib import sha256
from pathlib import Path

from .models import EvidenceItem, SourceRef


class DemoConnector:
    def resolve(self, raw_source: str) -> SourceRef:
        if not raw_source.startswith("demo:") or not raw_source[5:]:
            raise ValueError("demo connector requires demo:<id>")
        source_id = raw_source[5:]
        return SourceRef("demo", source_id, f"demo://{source_id}")

    def facts(self, source: SourceRef) -> dict[str, object]:
        return {"title": f"Demo {source.source_id}", "duration_seconds": 12}


class DemoEvidenceCollector:
    def collect(self, source: SourceRef, workspace: Path):
        workspace.mkdir(parents=True, exist_ok=True)
        transcript = workspace / "transcript.json"
        content = '{"language":"zh","segments":[]}\n'
        transcript.write_text(content, encoding="utf-8")
        digest = sha256(content.encode("utf-8")).hexdigest()
        evidence = EvidenceItem(
            kind="transcript",
            locator=str(transcript.resolve()),
            provenance={"adapter": "demo", "sha256": digest},
        )
        return (evidence,), ("visual_evidence_unavailable",)
```

```python
# research_mvp/cli.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .demo_adapters import DemoConnector, DemoEvidenceCollector
from .repository import ConflictError, FileResearchRepository
from .service import ResearchService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research")
    parser.add_argument("--workspace", required=True)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("source")
    create.add_argument("--language", default="auto")

    for name in ("status", "show", "retry"):
        command = commands.add_parser(name)
        command.add_argument("job_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository = FileResearchRepository(Path(args.workspace))
    service = ResearchService(repository, DemoConnector(), DemoEvidenceCollector())
    try:
        if args.command == "create":
            result = service.create(args.source, {"language": args.language})
        elif args.command == "status":
            result = service.status(args.job_id)
        elif args.command == "show":
            result = service.show(args.job_id)
        else:
            result = service.retry(args.job_id)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError, ConflictError) as error:
        payload = {"status": "failed", "error": str(error)}
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 2
```

```python
# research_mvp/__main__.py
from .cli import main

raise SystemExit(main())
```

- [ ] **Step 4: Run full tests and a manual independent demonstration**

Run:

```powershell
.\tools\.venv\Scripts\python.exe -m unittest discover -s tests/research_mvp -t . -v
$demo = Join-Path $env:TEMP "research-mvp-demo"
Remove-Item -Recurse -Force $demo -ErrorAction SilentlyContinue
.\tools\.venv\Scripts\python.exe -m research_mvp --workspace $demo create demo:video-1
```

Expected: all tests pass and the demonstration prints a committed JSON dossier containing demo source facts and transcript evidence.

- [ ] **Step 5: Commit the independently runnable domain MVP**

```powershell
git add research_mvp tests/research_mvp/test_cli.py
git commit -m "feat(research): expose independently runnable research CLI"
```

## Task 5: Evidence Audit and Documentation

**Files:**
- Create: `docs/mvp/research/vertical-slice-brief.md`
- Create: `docs/mvp/research/capability-dag.md`
- Create: `docs/mvp/research/capability-evidence.md`
- Create: `docs/mvp/research/delivery-ledger.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: exact commands and results from Tasks 1-4.
- Produces: the four required MVP Vertical Slices artifacts and a discoverable README entry.

- [ ] **Step 1: Run final domain verification and capture facts**

Run:

```powershell
$workspace = "$env:TEMP\research-mvp-evidence"
$created = .\tools\.venv\Scripts\python.exe -m research_mvp --workspace $workspace create demo:evidence | ConvertFrom-Json
.\tools\.venv\Scripts\python.exe -m unittest discover -s tests/research_mvp -t . -v
.\tools\.venv\Scripts\python.exe -m research_mvp --workspace $workspace show $created.job_id
git status --short
```

Expected: all tests pass; `show` returns the same committed dossier; only intended files are modified.

- [ ] **Step 2: Write the required workflow artifacts with observed evidence**

`vertical-slice-brief.md` records the observable result, commands, owners, invariants, decision gates, and non-goals from the design.

`capability-dag.md` records source resolution → job lifecycle → fake evidence collection → dossier commit, with each edge labeled `Query`, `Command`, or `Fact`, and marks real platform adapters as substitutes not yet integrated.

`capability-evidence.md` records every RED command and failure, every GREEN command and test count, public interfaces, and the failure matrix:

| Condition | Required observed behavior |
| --- | --- |
| duplicate | same source/config returns dossier version 1 |
| conflict | same job ID with different state raises `ConflictError` |
| stale | changed evidence config creates a different job ID |
| reentry | completed create/retry returns committed dossier |
| partial failure | job becomes `failed`, no dossier is committed |
| cleanup | temporary test workspace is removed by test teardown |

`delivery-ledger.md` sets the supported level to `DOMAIN_VERIFIED`, lists fake connector/collector substitutes, and forbids platform or production claims.

- [ ] **Step 3: Add README entry without advertising unverified integrations**

Add a “New MVP architecture” section that shows only the demo invocation and states:

```text
research-mvp is domain-verified with substitute adapters.
Real Bilibili/YouTube, FFmpeg, and transcription adapters remain platform-integration work.
```

- [ ] **Step 4: Scan documentation and run verification again**

Run:

```powershell
Get-ChildItem docs\mvp\research -File | Select-String -Pattern (('T'+'BD')+'|'+('T'+'ODO')+'|production ready|platform integrated')
.\tools\.venv\Scripts\python.exe -m unittest discover -s tests/research_mvp -t . -v
git diff --check
```

Expected: no placeholders or forbidden claims, all tests pass, and `git diff --check` exits 0.

- [ ] **Step 5: Commit domain-verification evidence**

```powershell
git add README.md docs/mvp/research
git commit -m "docs(research): record domain verification evidence"
```

## Deferred Plans

The following require separate specifications or implementation plans after this plan is verified:

1. Local-file and generated-media adjacent integration.
2. Real FFmpeg evidence adapter.
3. Real transcription adapter.
4. Bilibili and YouTube connectors plus credential strategies.
5. `authoring-mvp`, `voice-mvp`, `production-mvp`, `distribution-mvp`, and evidence-backed `review-mvp`.
