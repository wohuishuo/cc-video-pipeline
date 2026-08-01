"""Adapter for the public Platform I/O PowerShell boundary."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Callable

from .contracts import SUPPORTED_EXTENSIONS, SourceSpec
from .operation import TransportResult


class PlatformIOTransport:
    def __init__(self, launcher: Path, *, cookies: Path | None = None):
        self.launcher = Path(launcher).resolve()
        self.cookies = Path(cookies).resolve() if cookies else None

    def fetch(
        self, spec: SourceSpec, output_dir: Path, on_log: Callable[[str], None]
    ) -> TransportResult:
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.launcher),
            "download",
            str(spec.platform),
            spec.value,
            "--output-dir",
            str(output_dir),
            "--max-height",
            str(spec.max_height),
            "--json",
        ]
        if self.cookies:
            command.extend(["--cookies", str(self.cookies)])
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in completed.stdout.splitlines():
            if line.strip():
                on_log(line.strip())
        receipt_path = output_dir / "download-receipt.json"
        if not receipt_path.is_file():
            return TransportResult(False, (), None, {}, completed.stderr[-2000:] or "platform receipt missing")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            return TransportResult(False, (), receipt_path, {}, f"invalid platform receipt: {error}")
        media = tuple(
            sorted(
                (
                    path.resolve()
                    for path in output_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
                ),
                key=lambda path: path.as_posix().casefold(),
            )
        )
        if completed.returncode != 0 or receipt.get("status") != "ok" or not media:
            return TransportResult(
                False,
                media,
                receipt_path,
                dict(receipt.get("facts") or {}),
                str(receipt.get("error") or completed.stderr[-2000:] or "platform download failed"),
            )
        return TransportResult(True, media, receipt_path, dict(receipt.get("facts") or {}))

