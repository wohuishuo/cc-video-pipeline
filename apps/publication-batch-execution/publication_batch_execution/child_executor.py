"""Public-launcher adapter for one guarded Publication execution."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import threading
from typing import Callable

from .contracts import ExecutionItem, sha256_file
from .operation import ChildExecutionFact


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


def _run(argv: list[str], on_log: Callable[[str], None]) -> ProcessResult:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace", bufsize=1, creationflags=creationflags,
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
    closed = 0; stdout: list[str] = []; stderr: list[str] = []
    while process.poll() is None or closed < len(threads):
        try:
            row = output.get(timeout=0.05)
        except Empty:
            continue
        if row is None:
            closed += 1; continue
        name, line = row; (stdout if name == "stdout" else stderr).append(line)
        if line:
            on_log(line)
    for thread in threads:
        thread.join(timeout=1)
    return ProcessResult(process.wait(), "\n".join(stdout), "\n".join(stderr))


def _last_json(text: str) -> dict | None:
    for line in reversed(text.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _read(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


class PublicPublicationExecutor:
    """Execute and verify one child through Publication's public CLI."""

    def __init__(
        self,
        launcher: str | Path,
        *,
        platform_io_launcher: str | Path | None = None,
        runner: Callable[[list[str], Callable[[str], None]], ProcessResult] = _run,
    ) -> None:
        self.launcher = Path(launcher).resolve()
        self.platform_io_launcher = Path(platform_io_launcher).resolve() if platform_io_launcher else None
        self.runner = runner
        suffix = ""
        if self.platform_io_launcher:
            suffix = ":" + hashlib.sha256(str(self.platform_io_launcher).encode("utf-8")).hexdigest()[:12]
        self.identity = "publication-public-launcher@1" + suffix

    def execute(
        self,
        item: ExecutionItem,
        output_dir: str | Path,
        child_operation_id: str,
        vault_path: str | Path,
        on_log: Callable[[str], None],
    ) -> ChildExecutionFact:
        output = Path(output_dir).resolve(); vault = Path(vault_path).resolve()
        argv = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.launcher),
            "execute", str(item.plan_path), "--confirmation", item.plan_sha256,
            "--credential-vault", str(vault), "--output-dir", str(output),
            "--operation-id", child_operation_id, "--json",
        ]
        if self.platform_io_launcher:
            argv.extend(["--platform-io-launcher", str(self.platform_io_launcher)])
        try:
            completed = self.runner(argv, on_log)
        except OSError:
            return ChildExecutionFact("FAILED", output / "publication-receipt.json", None, None, None, "Publication process could not be started")
        payload = _last_json(completed.stdout)
        payload_class = str(payload.get("resultClass") or "") if isinstance(payload, dict) else ""
        receipt_path = output / "publication-receipt.json"; receipt = _read(receipt_path)
        if payload_class in {"UNKNOWN", "REJECTED_UNKNOWN"}:
            if self._unknown_receipt(receipt, receipt_path, item, child_operation_id):
                return ChildExecutionFact(payload_class, receipt_path, None, None, None, "publication outcome is unknown")
            return ChildExecutionFact("FAILED", receipt_path, None, None, None, "Publication unknown receipt is invalid")
        if completed.returncode != 0 or payload_class not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            return ChildExecutionFact("FAILED", receipt_path, None, None, None, "Publication execution failed")
        fact = self._completed_fact(receipt, receipt_path, item, child_operation_id)
        return fact or ChildExecutionFact("FAILED", receipt_path, None, None, None, "Publication completion fact is invalid")

    @staticmethod
    def _unknown_receipt(receipt: dict | None, receipt_path: Path, item: ExecutionItem, child_operation_id: str) -> bool:
        return bool(
            receipt_path.is_file()
            and isinstance(receipt, dict)
            and receipt.get("schemaVersion") == 1
            and receipt.get("operationId") == child_operation_id
            and Path(str(receipt.get("plan", ""))).resolve() == item.plan_path
            and receipt.get("planSha256") == item.plan_sha256
            and receipt.get("resultClass") in {"UNKNOWN", "REJECTED_UNKNOWN"}
            and receipt.get("manifest") is None
            and receipt.get("manifestSha256") is None
        )

    @staticmethod
    def _completed_fact(
        receipt: dict | None,
        receipt_path: Path,
        item: ExecutionItem,
        child_operation_id: str,
    ) -> ChildExecutionFact | None:
        try:
            manifest_path = Path(str(receipt["manifest"])).resolve()
            manifest_sha = str(receipt["manifestSha256"])
            manifest = _read(manifest_path)
            publications = manifest["publications"]
            publication = publications[0]
            external_id = publication["externalId"]
            valid = (
                receipt.get("schemaVersion") == 1
                and receipt.get("operationId") == child_operation_id
                and Path(str(receipt.get("plan", ""))).resolve() == item.plan_path
                and receipt.get("planSha256") == item.plan_sha256
                and receipt.get("resultClass") == "COMPLETED"
                and manifest_path.is_file()
                and sha256_file(manifest_path) == manifest_sha
                and isinstance(manifest, dict)
                and manifest.get("schemaVersion") == 1
                and manifest.get("public") is False
                and Path(str(manifest.get("plan", ""))).resolve() == item.plan_path
                and manifest.get("planSha256") == item.plan_sha256
                and isinstance(publications, list)
                and len(publications) == 1
                and publication.get("jobId") == item.job_id
                and publication.get("platform") == "youtube"
                and publication.get("status") == "COMPLETED"
                and isinstance(external_id, str)
                and bool(external_id.strip())
            )
        except (KeyError, TypeError, ValueError, OSError):
            return None
        return ChildExecutionFact("COMPLETED", receipt_path, manifest_path, manifest_sha, external_id.strip()) if valid else None
