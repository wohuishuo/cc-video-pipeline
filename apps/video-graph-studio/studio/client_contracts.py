"""Cached composition adapter for the independent Client Contracts public CLI."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import threading


SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_COMMANDS = {"CMD-RUN-CREATE", "CMD-RUN-START", "CMD-RUN-CANCEL"}


class ClientContractsError(RuntimeError):
    pass


class ClientContractsCommandAdapter:
    def __init__(self, launcher: Path, *, timeout_seconds: float = 10):
        self.launcher = Path(launcher).resolve()
        self.timeout_seconds = timeout_seconds
        self._lock = threading.RLock()
        self._cached: dict | None = None

    def discover(self) -> dict:
        with self._lock:
            if self._cached is not None:
                return self._cached
            try:
                completed = subprocess.run(
                    [
                        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(self.launcher), "show", "--json",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ClientContractsError("client contracts are unavailable") from error
            lines = [line for line in completed.stdout.splitlines() if line.strip()]
            if not lines:
                raise ClientContractsError("client contracts returned no decision")
            try:
                payload = json.loads(lines[-1])
            except json.JSONDecodeError as error:
                raise ClientContractsError("client contracts returned invalid JSON") from error
            self._validate(payload)
            self._cached = payload
            return payload

    @staticmethod
    def _validate(payload: object) -> None:
        if not isinstance(payload, dict) or payload.get("resultClass") != "COMPLETED":
            raise ClientContractsError("client contracts rejected discovery")
        value = payload.get("value")
        bundle = value.get("bundle") if isinstance(value, dict) else None
        digest = value.get("sha256") if isinstance(value, dict) else None
        if (
            not isinstance(bundle, dict)
            or bundle.get("schemaVersion") != 1
            or not isinstance(bundle.get("contractVersion"), str)
            or not REQUIRED_COMMANDS.issubset(bundle.get("commands", {}))
            or "GET /api/v1/contracts" not in bundle.get("endpoints", {})
            or not isinstance(digest, str)
            or not SHA256.fullmatch(digest)
        ):
            raise ClientContractsError("client contracts returned a malformed bundle")
