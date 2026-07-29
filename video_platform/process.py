from __future__ import annotations

import subprocess
import os
from pathlib import Path
from typing import Mapping, Sequence

from .models import ProcessResult


class ProcessRunner:
    def run(
        self,
        args: Sequence[str],
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        child_env = os.environ.copy()
        child_env.setdefault("PYTHONUTF8", "1")
        child_env.setdefault("PYTHONIOENCODING", "utf-8")
        child_env.update(env or {})
        completed = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=child_env,
        )
        return ProcessResult(tuple(str(item) for item in args), completed.returncode, completed.stdout, completed.stderr)
