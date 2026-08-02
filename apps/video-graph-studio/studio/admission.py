"""Admission adapter composed through Workspace Access's public CLI boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import Any


TOKEN_ENVIRONMENT_VARIABLE = "VIDEO_GRAPH_STUDIO_ADMISSION_TOKEN"


@dataclass(frozen=True)
class AdmissionDecision:
    authorized: bool
    result_class: str
    detail: str


class WorkspaceAccessCommandAdapter:
    def __init__(
        self,
        launcher: Path,
        registry: Path,
        workspace_id: str,
        *,
        timeout_seconds: float = 10,
    ) -> None:
        self.launcher = Path(launcher).resolve()
        self.registry = Path(registry).resolve()
        self.workspace_id = workspace_id
        self.timeout_seconds = timeout_seconds

    def describe_workspace(self) -> dict[str, Any]:
        result = self._invoke(
            [
                "describe",
                "--registry",
                str(self.registry),
                "--workspace-id",
                self.workspace_id,
                "--json",
            ]
        )
        if result.get("resultClass") != "COMPLETED" or not isinstance(result.get("value"), dict):
            raise RuntimeError("Workspace Access could not describe the configured workspace")
        return result["value"]

    def authorize(self, workspace_id: str, token: str, scope: str) -> AdmissionDecision:
        if workspace_id != self.workspace_id:
            return AdmissionDecision(False, "REJECTED_WORKSPACE", "workspace is not served here")
        if not token:
            return AdmissionDecision(False, "REJECTED_UNAUTHORIZED", "credential required")
        try:
            result = self._invoke(
                [
                    "authorize",
                    "--registry",
                    str(self.registry),
                    "--workspace-id",
                    self.workspace_id,
                    "--required-scope",
                    scope,
                    "--token-env",
                    TOKEN_ENVIRONMENT_VARIABLE,
                    "--json",
                ],
                token=token,
            )
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            return AdmissionDecision(False, "REJECTED_UNAUTHORIZED", "authorization unavailable")
        result_class = str(result.get("resultClass", "REJECTED_UNAUTHORIZED"))
        return AdmissionDecision(
            result_class == "AUTHORIZED",
            result_class if result_class == "AUTHORIZED" else "REJECTED_UNAUTHORIZED",
            "authorized" if result_class == "AUTHORIZED" else "scope denied",
        )

    def _invoke(self, arguments: list[str], *, token: str | None = None) -> dict[str, Any]:
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        if token is not None:
            environment[TOKEN_ENVIRONMENT_VARIABLE] = token
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
            env=environment,
            timeout=self.timeout_seconds,
            check=False,
        )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("Workspace Access returned no decision")
        try:
            value = json.loads(lines[-1])
        except json.JSONDecodeError as error:
            raise RuntimeError("Workspace Access returned an invalid decision") from error
        if not isinstance(value, dict):
            raise RuntimeError("Workspace Access returned an invalid decision")
        return value
