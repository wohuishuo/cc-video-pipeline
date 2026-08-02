"""Public Credential Vault process adapter with one-child secret injection."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable


SECRET_ENV = "YOUTUBE_OAUTH_CREDENTIAL"


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class VaultWriteResult:
    completed: bool
    value: dict[str, Any]
    error: str | None = None


def _run(argv: list[str], environment: dict[str, str]) -> ProcessResult:
    completed = subprocess.run(argv, env=environment, text=True, capture_output=True, encoding="utf-8", errors="replace", shell=False)
    return ProcessResult(completed.returncode, completed.stdout, completed.stderr)


class VaultWriter:
    def __init__(self, launcher: Path, *, runner: Callable[[list[str], dict[str, str]], ProcessResult] = _run):
        self.launcher = Path(launcher).resolve(); self.runner = runner

    def store(self, vault: Path, credential_id: str, label: str, secret_json: str) -> VaultWriteResult:
        base = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.launcher)]
        try:
            describe = self.runner([*base, "describe", "--vault", str(Path(vault).resolve()), "--credential-id", credential_id, "--json"], dict(os.environ))
        except OSError:
            return VaultWriteResult(False, {}, "Credential Vault process could not be started")
        existing = self._payload(describe.stdout) if describe.returncode == 0 else None
        if existing and existing.get("value", {}).get("provider") != "youtube":
            return VaultWriteResult(False, {}, "existing credential provider is not youtube")
        if existing:
            command = [*base, "rotate", "--vault", str(Path(vault).resolve()), "--credential-id", credential_id, "--secret-env", SECRET_ENV, "--json"]
        else:
            command = [*base, "put", "--vault", str(Path(vault).resolve()), "--credential-id", credential_id, "--provider", "youtube", "--label", label, "--secret-env", SECRET_ENV, "--json"]
        environment = {**os.environ, SECRET_ENV: secret_json}
        try:
            try:
                result = self.runner(command, environment)
            except OSError:
                return VaultWriteResult(False, {}, "Credential Vault process could not be started")
        finally:
            environment.pop(SECRET_ENV, None); secret_json = ""
        payload = self._payload(result.stdout)
        value = payload.get("value", {}) if payload else {}
        completed = result.returncode == 0 and payload.get("resultClass") in {"COMPLETED", "DUPLICATE_COMPLETED"} and value.get("provider") == "youtube"
        return VaultWriteResult(completed, value if completed else {}, None if completed else "Credential Vault rejected YouTube credential storage")

    @staticmethod
    def _payload(text: str) -> dict[str, Any] | None:
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None
