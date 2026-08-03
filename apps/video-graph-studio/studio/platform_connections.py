"""Read-only projection of real local publishing adapters and accounts."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Callable


PLATFORMS = (
    ("youtube", "YouTube"),
    ("bilibili", "Bilibili"),
    ("douyin", "Douyin"),
    ("tiktok", "TikTok"),
)


class PlatformConnectionService:
    def __init__(
        self,
        repository: Path,
        vault_launcher: Path,
        vault_path: Path,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.repository = Path(repository).resolve()
        self.vault_launcher = Path(vault_launcher).resolve()
        self.vault_path = Path(vault_path).resolve()
        self.runner = runner

    def catalog(self) -> list[dict[str, Any]]:
        records = self._records()
        social_checkout = self.repository / ".tools" / "social-auto-upload"
        youtube_ready = (self.repository / "apps" / "youtube-publisher" / "run.ps1").is_file()
        social_ready = (social_checkout / "sau_cli.py").is_file()
        result: list[dict[str, Any]] = []
        for platform, label in PLATFORMS:
            adapter_ready = youtube_ready if platform == "youtube" else social_ready
            accounts = [
                {"id": str(row["credentialId"]), "label": str(row["label"])}
                for row in records
                if row.get("provider") == platform and row.get("status") == "ACTIVE"
            ]
            state = (
                "ADAPTER_NOT_INSTALLED"
                if not adapter_ready
                else "READY_PRIVATE"
                if accounts
                else "CONNECTION_REQUIRED"
            )
            result.append(
                {
                    "id": platform,
                    "label": label,
                    "uploadState": state,
                    "accounts": accounts,
                    "allowedVisibilities": ["private"] if platform == "youtube" and adapter_ready else [],
                    "connectionMode": "oauth" if platform == "youtube" else "browser-profile",
                }
            )
        return result

    def _records(self) -> list[dict[str, Any]]:
        completed = self.runner(
            [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(self.vault_launcher), "list", "--vault", str(self.vault_path), "--json",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            payload = json.loads((completed.stdout or "").strip().splitlines()[-1])
            records = payload.get("value", {}).get("records", [])
        except (IndexError, AttributeError, json.JSONDecodeError):
            return []
        return records if completed.returncode == 0 and isinstance(records, list) else []
