"""Multi-workspace runtime routing through public access and storage CLIs."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import threading
from typing import Any, Callable


class WorkspaceRoutingError(RuntimeError):
    def __init__(self, result_class: str, detail: str):
        super().__init__(detail)
        self.result_class = result_class
        self.detail = detail


class WorkspaceStorageCommandAdapter:
    def __init__(
        self,
        launcher: Path,
        registry: Path,
        *,
        timeout_seconds: float = 10,
    ) -> None:
        self.launcher = Path(launcher).resolve()
        self.registry = Path(registry).resolve()
        self.timeout_seconds = timeout_seconds

    def describe_workspace(self, workspace_id: str) -> dict[str, Any]:
        result = self._invoke(
            [
                "describe",
                "--registry",
                str(self.registry),
                "--workspace-id",
                workspace_id,
                "--json",
            ]
        )
        if result.get("resultClass") != "COMPLETED" or not isinstance(
            result.get("value"), dict
        ):
            raise WorkspaceRoutingError(
                str(result.get("resultClass", "REJECTED_STORAGE")),
                "workspace storage is not provisioned",
            )
        return result["value"]

    def check_capacity(self, workspace_id: str, required_bytes: int) -> dict[str, Any]:
        return self._invoke(
            [
                "capacity",
                "--registry",
                str(self.registry),
                "--workspace-id",
                workspace_id,
                "--required-bytes",
                str(required_bytes),
                "--json",
            ]
        )

    def _invoke(self, arguments: list[str]) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(self.launcher),
                    *arguments,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise WorkspaceRoutingError(
                "REJECTED_STORAGE", "workspace storage is unavailable"
            ) from error
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise WorkspaceRoutingError(
                "REJECTED_STORAGE", "workspace storage returned no decision"
            )
        try:
            value = json.loads(lines[-1])
        except json.JSONDecodeError as error:
            raise WorkspaceRoutingError(
                "REJECTED_STORAGE", "workspace storage returned invalid JSON"
            ) from error
        if not isinstance(value, dict):
            raise WorkspaceRoutingError(
                "REJECTED_STORAGE", "workspace storage returned an invalid decision"
            )
        return value


class WorkspaceRuntimeRouter:
    def __init__(
        self,
        access: Any,
        storage: WorkspaceStorageCommandAdapter,
        factory: Callable[
            [str, Path, Path, tuple[Path, ...]],
            tuple[Any, Any],
        ],
    ) -> None:
        self.access = access
        self.storage = storage
        self.factory = factory
        self._lock = threading.RLock()
        self._runtimes: dict[str, tuple[Any, Any]] = {}

    def application_for(self, workspace_id: str, *, required_bytes: int = 0):
        if required_bytes:
            capacity = self.storage.check_capacity(workspace_id, required_bytes)
            if capacity.get("resultClass") != "ALLOWED":
                raise WorkspaceRoutingError(
                    str(capacity.get("resultClass", "REJECTED_STORAGE")),
                    "workspace capacity denied",
                )
        with self._lock:
            existing = self._runtimes.get(workspace_id)
            if existing is not None:
                return existing[0]
            try:
                access = self.access.describe_workspace(workspace_id)
                storage = self.storage.describe_workspace(workspace_id)
                allowed_roots = tuple(
                    Path(value).resolve() for value in access["allowedRoots"]
                )
                state_root = (
                    Path(storage["roots"]["state"]) / "video-graph-studio"
                )
                artifact_root = (
                    Path(storage["roots"]["artifacts"]) / "video-graph-studio"
                )
            except (KeyError, TypeError, RuntimeError) as error:
                if isinstance(error, WorkspaceRoutingError):
                    raise
                raise WorkspaceRoutingError(
                    "REJECTED_STORAGE", "workspace descriptors are unavailable"
                ) from error
            try:
                runtime = self.factory(
                    workspace_id,
                    state_root,
                    artifact_root,
                    allowed_roots,
                )
            except Exception as error:
                raise WorkspaceRoutingError(
                    "REJECTED_STORAGE", "workspace runtime could not be initialized"
                ) from error
            self._runtimes[workspace_id] = runtime
            return runtime[0]

    def health(self) -> dict[str, Any]:
        with self._lock:
            runtimes = list(self._runtimes.values())
        active_workers = sum(
            1 for _, engine in runtimes if getattr(engine, "active_run_id", None)
        )
        queued_runs = 0
        for application, _ in runtimes:
            store = getattr(application, "store", None)
            if store is not None:
                queued_runs += store.queue_snapshot()["queuedRuns"]
        return {
            "database": "workspace-routed",
            "activeWorkers": active_workers,
            "queuedRuns": queued_runs,
            "initializedWorkspaces": len(runtimes),
        }

    def shutdown(self) -> None:
        with self._lock:
            runtimes = list(self._runtimes.values())
            self._runtimes.clear()
        for _, engine in runtimes:
            engine.shutdown()
