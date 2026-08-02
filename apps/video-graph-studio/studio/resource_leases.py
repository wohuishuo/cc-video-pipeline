"""Resource Budget CLI composition without copying resource state into Studio."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import threading
from typing import Any, Callable


class ResourceLeaseUnavailable(RuntimeError):
    def __init__(self, result_class: str, detail: str):
        super().__init__(detail)
        self.result_class = result_class
        self.detail = detail


class ResourceBudgetCommandAdapter:
    def __init__(self, launcher: Path, database: Path, *, timeout_seconds: float = 15):
        self.launcher = Path(launcher).resolve()
        self.database = Path(database).resolve()
        self.timeout_seconds = timeout_seconds

    def reserve(self, workspace_id, reservation_id, bytes_requested, slots, ttl_seconds):
        return self._invoke(
            "reserve", workspace_id, reservation_id,
            "--bytes", bytes_requested, "--slots", slots, "--ttl-seconds", ttl_seconds,
        )

    def renew(self, workspace_id, reservation_id, expected_generation, ttl_seconds):
        return self._invoke(
            "renew", workspace_id, reservation_id,
            "--expected-generation", expected_generation, "--ttl-seconds", ttl_seconds,
        )

    def release(self, workspace_id, reservation_id, expected_generation):
        return self._invoke(
            "release", workspace_id, reservation_id,
            "--expected-generation", expected_generation,
        )

    def describe(self, workspace_id, reservation_id):
        return self._invoke("describe", workspace_id, reservation_id)

    def _invoke(self, command, workspace_id, reservation_id, *arguments):
        argv = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(self.launcher), command,
            "--database", str(self.database),
            "--workspace-id", str(workspace_id),
            "--reservation-id", str(reservation_id),
            *map(str, arguments), "--json",
        ]
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ResourceLeaseUnavailable(
                "REJECTED_STORAGE", "resource budget is unavailable"
            ) from error
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise ResourceLeaseUnavailable(
                "REJECTED_STORAGE", "resource budget returned no decision"
            )
        try:
            payload = json.loads(lines[-1])
        except json.JSONDecodeError as error:
            raise ResourceLeaseUnavailable(
                "REJECTED_STORAGE", "resource budget returned invalid JSON"
            ) from error
        if not isinstance(payload, dict) or not isinstance(payload.get("resultClass"), str):
            raise ResourceLeaseUnavailable(
                "REJECTED_STORAGE", "resource budget returned an invalid decision"
            )
        return payload


class ResourceLease:
    def __init__(self, commands, workspace_id: str, reservation_id: str, generation: int, ttl_seconds: int):
        self.commands = commands
        self.workspace_id = workspace_id
        self.reservation_id = reservation_id
        self.generation = generation
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, on_failure: Callable[[str], None]) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._heartbeat,
            args=(on_failure,),
            name=f"resource-lease-{self.reservation_id}",
            daemon=True,
        )
        self._thread.start()

    def renew_once(self) -> None:
        with self._lock:
            result = self.commands.renew(
                self.workspace_id,
                self.reservation_id,
                self.generation,
                self.ttl_seconds,
            )
            if result.get("resultClass") not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
                raise ResourceLeaseUnavailable(
                    str(result.get("resultClass", "REJECTED_STORAGE")),
                    "resource lease renewal was rejected",
                )
            try:
                self.generation = int(result["value"]["generation"])
            except (KeyError, TypeError, ValueError) as error:
                raise ResourceLeaseUnavailable(
                    "REJECTED_STORAGE", "resource lease renewal omitted its generation"
                ) from error

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=max(1.0, self.ttl_seconds / 3 + 1))
        with self._lock:
            result = self.commands.release(
                self.workspace_id, self.reservation_id, self.generation
            )
        if result.get("resultClass") not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            raise ResourceLeaseUnavailable(
                str(result.get("resultClass", "REJECTED_STORAGE")),
                "resource lease release was rejected",
            )

    def _heartbeat(self, on_failure: Callable[[str], None]) -> None:
        interval = max(0.1, self.ttl_seconds / 3)
        while not self._stop.wait(interval):
            try:
                self.renew_once()
            except ResourceLeaseUnavailable as error:
                on_failure(f"{error.result_class}: {error.detail}")
                return


class ResourceLeaseCoordinator:
    def __init__(self, commands, *, workspace_id: str, bytes_per_run: int, ttl_seconds: int):
        if bytes_per_run <= 0:
            raise ValueError("bytes_per_run must be positive")
        if ttl_seconds < 3:
            raise ValueError("ttl_seconds must be at least 3")
        self.commands = commands
        self.workspace_id = workspace_id
        self.bytes_per_run = bytes_per_run
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def reservation_id(run_id: str) -> str:
        return f"studio-{run_id}"

    def acquire(self, run_id: str) -> ResourceLease:
        reservation_id = self.reservation_id(run_id)
        result = self.commands.reserve(
            self.workspace_id,
            reservation_id,
            self.bytes_per_run,
            1,
            self.ttl_seconds,
        )
        if result.get("resultClass") not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            raise ResourceLeaseUnavailable(
                str(result.get("resultClass", "REJECTED_STORAGE")),
                "resource reservation was rejected",
            )
        try:
            generation = int(result["value"]["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise ResourceLeaseUnavailable(
                "REJECTED_STORAGE", "resource reservation omitted its generation"
            ) from error
        return ResourceLease(
            self.commands,
            self.workspace_id,
            reservation_id,
            generation,
            self.ttl_seconds,
        )

    def reconcile(self, runs: list[dict[str, Any]]) -> None:
        for run in runs:
            if run.get("status") not in {"COMPLETED", "FAILED", "CANCELLED"}:
                continue
            reservation_id = self.reservation_id(str(run["runId"]))
            result = self.commands.describe(self.workspace_id, reservation_id)
            if result.get("resultClass") != "COMPLETED":
                continue
            value = result.get("value")
            if not isinstance(value, dict) or value.get("status") != "ACTIVE":
                continue
            generation = value.get("generation")
            if isinstance(generation, int):
                self.commands.release(self.workspace_id, reservation_id, generation)
