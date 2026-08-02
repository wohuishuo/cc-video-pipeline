"""Public-launcher adapter for the one-video Publication owner."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import threading
from typing import Any, Callable

from .contracts import BatchPolicy, Derivative, sha256_file
from .operation import ChildPlanFact, _plan_matches


class PlanChildError(RuntimeError):
    """The Publication child did not commit a valid plan fact."""


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


def _run(argv: list[str], on_log: Callable[[str], None]) -> ProcessResult:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creationflags,
    )
    output: Queue[tuple[str, str] | None] = Queue()

    def read(stream, name: str) -> None:
        assert stream is not None
        for line in stream:
            output.put((name, line.rstrip("\r\n")))
        output.put(None)

    threads = [
        threading.Thread(target=read, args=(process.stdout, "stdout"), daemon=True),
        threading.Thread(target=read, args=(process.stderr, "stderr"), daemon=True),
    ]
    for thread in threads:
        thread.start()
    closed = 0
    stdout: list[str] = []
    stderr: list[str] = []
    while process.poll() is None or closed < len(threads):
        try:
            row = output.get(timeout=0.05)
        except Empty:
            continue
        if row is None:
            closed += 1
            continue
        name, line = row
        (stdout if name == "stdout" else stderr).append(line)
        if line:
            on_log(line)
    for thread in threads:
        thread.join(timeout=1)
    return ProcessResult(process.wait(), "\n".join(stdout), "\n".join(stderr))


def _last_json(text: str) -> dict[str, Any] | None:
    for line in reversed(text.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


class PublicPublicationPlanner:
    """Translate one batch item into a verified Publication launcher call."""

    def __init__(
        self,
        launcher: str | Path,
        *,
        runner: Callable[[list[str], Callable[[str], None]], ProcessResult] = _run,
    ) -> None:
        self.launcher = Path(launcher).resolve()
        self.runner = runner

    def plan(
        self,
        derivative: Derivative,
        metadata_path: Path,
        output_dir: Path,
        operation_id: str,
        policy: BatchPolicy,
        on_log: Callable[[str], None],
    ) -> ChildPlanFact:
        metadata = Path(metadata_path).resolve()
        output = Path(output_dir).resolve()
        argv = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.launcher),
            "plan",
            str(derivative.path),
            "--metadata",
            str(metadata),
        ]
        for platform, account in policy.targets:
            argv.extend(["--target", f"{platform}={account}"])
        for platform, credential_id in policy.credentials:
            argv.extend(["--credential", f"{platform}={credential_id}"])
        argv.extend(["--output-dir", str(output), "--operation-id", operation_id, "--json"])
        try:
            completed = self.runner(argv, on_log)
        except OSError as error:
            raise PlanChildError("Publication process could not be started") from error
        payload = _last_json(completed.stdout)
        if (
            completed.returncode != 0
            or payload is None
            or payload.get("resultClass") not in {"COMPLETED", "DUPLICATE_COMPLETED"}
        ):
            detail = payload.get("error") if isinstance(payload, dict) else None
            raise PlanChildError(str(detail or completed.stderr[-4000:] or "Publication planning failed"))
        receipt_path = output / "planning-receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            raise PlanChildError("Publication planning receipt is missing or invalid") from error
        required = {
            "schemaVersion",
            "operationId",
            "inputFingerprint",
            "resultClass",
            "plan",
            "planSha256",
            "jobCount",
        }
        if not isinstance(receipt, dict) or set(receipt) != required:
            raise PlanChildError("Publication planning receipt schema is invalid")
        try:
            plan_path = Path(str(receipt["plan"])).resolve()
            plan_sha = str(receipt["planSha256"])
            job_count = int(receipt["jobCount"])
        except (KeyError, TypeError, ValueError) as error:
            raise PlanChildError("Publication planning receipt fields are invalid") from error
        if (
            receipt.get("schemaVersion") != 1
            or receipt.get("operationId") != operation_id
            or receipt.get("resultClass") != "COMPLETED"
            or job_count != len(policy.targets)
            or not _plan_matches(plan_path, plan_sha, derivative, metadata, sha256_file(metadata), policy)
        ):
            raise PlanChildError("Publication planning receipt or plan verification failed")
        return ChildPlanFact(plan_path, plan_sha, job_count)
