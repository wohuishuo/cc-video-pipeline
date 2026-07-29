from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from .models import ProcessResult


class ProcessRunner:
    def run(self, args: Sequence[str], cwd: Path | None = None) -> ProcessResult:
        completed = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return ProcessResult(tuple(str(item) for item in args), completed.returncode, completed.stdout, completed.stderr)
