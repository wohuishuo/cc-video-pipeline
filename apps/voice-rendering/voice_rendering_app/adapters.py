"""Edge TTS production adapter."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


class EdgeTtsAdapter:
    identity = "edge-tts@1"

    def __init__(self, *, rate="+0%", volume="+0%", command_runner=None, duration_probe=None):
        self.rate = rate
        self.volume = volume
        self.command_runner = command_runner or self._run
        self.duration_probe = duration_probe or self._probe
        self.active = 0
        self.maximum_active = 0

    def synthesize(self, text, voice, output, on_log):
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            argv = [sys.executable, "-m", "edge_tts", "--text", text, "--voice", voice,
                    "--rate", self.rate, "--volume", self.volume, "--write-media", str(output)]
            self.command_runner(argv)
            duration = float(self.duration_probe(output))
            on_log(f"Synthesized {duration:.3f}s with {voice}")
            return duration
        finally:
            self.active -= 1

    @staticmethod
    def _run(argv):
        completed = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "edge-tts failed")[-2000:])

    @staticmethod
    def _probe(path: Path) -> float:
        completed = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or "ffprobe failed")[-2000:])
        return float(json.loads(completed.stdout)["format"]["duration"])
