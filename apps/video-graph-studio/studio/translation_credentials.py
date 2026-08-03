"""Local custody for cloud translation credentials.

Studio owns only provider readiness and the setup interaction. Credential Vault
owns encrypted persistence and releases a secret only into a single child
process environment.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable


DEEPSEEK_CREDENTIAL_ID = "deepseek-api"
DEEPSEEK_PROVIDER = "deepseek"
DEEPSEEK_TARGET_ENVIRONMENT = "DEEPSEEK_API_KEY"
SETUP_SECRET_ENVIRONMENT = "VIDEO_GRAPH_STUDIO_DEEPSEEK_KEY"


class TranslationCredentialError(ValueError):
    """A bounded, non-secret setup failure suitable for an API response."""


class TranslationCredentialService:
    def __init__(
        self,
        vault_launcher: Path,
        vault_path: Path,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.vault_launcher = Path(vault_launcher).resolve()
        self.vault_path = Path(vault_path).resolve()
        self.runner = runner

    def deepseek_configured(self) -> bool:
        if os.environ.get(DEEPSEEK_TARGET_ENVIRONMENT, "").strip():
            return True
        return self._vault_deepseek_configured()

    def _vault_deepseek_configured(self) -> bool:
        result = self._invoke("describe")
        value = self._payload(result).get("value", {})
        return (
            result.returncode == 0
            and value.get("provider") == DEEPSEEK_PROVIDER
            and value.get("status") == "ACTIVE"
        )

    def configure_deepseek(self, secret: str) -> dict[str, Any]:
        if not isinstance(secret, str) or not secret.strip():
            raise TranslationCredentialError("DeepSeek API Key 不能为空")
        operation = "rotate" if self._vault_deepseek_configured() else "put"
        environment = {**os.environ, SETUP_SECRET_ENVIRONMENT: secret.strip()}
        arguments = ["--secret-env", SETUP_SECRET_ENVIRONMENT]
        if operation == "put":
            arguments = [
                "--provider", DEEPSEEK_PROVIDER,
                "--label", "DeepSeek API",
                *arguments,
            ]
        try:
            result = self._invoke(operation, *arguments, environment=environment)
        finally:
            environment.pop(SETUP_SECRET_ENVIRONMENT, None)
            secret = ""
        payload = self._payload(result)
        if result.returncode != 0 or payload.get("resultClass") not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            detail = payload.get("value", {}).get("detail", "Credential Vault rejected the key")
            raise TranslationCredentialError(str(detail))
        value = payload.get("value", {})
        return {
            "provider": DEEPSEEK_PROVIDER,
            "configured": value.get("status") == "ACTIVE",
            "status": value.get("status", "UNKNOWN"),
        }

    def _invoke(
        self,
        operation: str,
        *arguments: str,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        argv = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(self.vault_launcher), operation,
            "--vault", str(self.vault_path),
            "--credential-id", DEEPSEEK_CREDENTIAL_ID,
            *arguments,
            "--json",
        ]
        return self.runner(
            argv,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    @staticmethod
    def _payload(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        try:
            payload = json.loads((result.stdout or "").strip().splitlines()[-1])
        except (IndexError, TypeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}
