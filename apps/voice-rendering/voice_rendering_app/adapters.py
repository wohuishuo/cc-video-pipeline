"""Replaceable production adapters for translated voice rendering."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


class EdgeTtsAdapter:
    identity = "edge-tts@1"
    output_suffix = ".mp3"

    def __init__(self, *, rate="+0%", volume="+0%", command_runner=None, duration_probe=None):
        self.rate = rate
        self.volume = volume
        self.command_runner = command_runner or self._run
        self.duration_probe = duration_probe or self._probe
        self.active = 0
        self.maximum_active = 0

    def synthesize(self, text, language, voice, output, on_log, *, target_duration=None):
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


class Qwen3TtsAdapter:
    """Keep one local Qwen3-TTS preset engine resident for the whole run."""

    identity = "qwen3-tts-preset@1"
    output_suffix = ".wav"

    def __init__(self, *, device="cpu", engine_factory=None, audio_writer=None):
        self.device = device
        self.engine_factory = engine_factory or self._engine
        self.audio_writer = audio_writer or self._write_wav
        self._resident = None
        self.active = 0
        self.maximum_active = 0

    def _get_engine(self):
        if self._resident is None:
            self._resident = self.engine_factory()
            self._resident.load()
        return self._resident

    def synthesize(self, text, language, voice, output, on_log, *, target_duration=None):
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            audio, sample_rate = self._get_engine().synth_preset(
                text, str(language).split("-", 1)[0], voice
            )
            sample_rate = int(sample_rate)
            if sample_rate <= 0 or len(audio) <= 0:
                raise RuntimeError("Qwen3-TTS returned invalid audio")
            self.audio_writer(output, audio, sample_rate)
            duration = len(audio) / sample_rate
            on_log(f"Synthesized {duration:.3f}s with Qwen3-TTS {voice}")
            return duration
        finally:
            self.active -= 1

    def _engine(self):
        from ttslib.registry import get_engine

        return get_engine("qwen", device=self.device)

    @staticmethod
    def _write_wav(path, audio, sample_rate):
        import soundfile

        soundfile.write(str(path), audio, sample_rate, format="WAV")


class OriginalAudioAdapter:
    """Create timing clips while preserving the source track at composition."""

    identity = "original-audio-silence@1"
    output_suffix = ".wav"

    def __init__(self, *, command_runner=None):
        self.command_runner = command_runner or self._run
        self.active = 0
        self.maximum_active = 0

    def synthesize(self, text, language, voice, output, on_log, *, target_duration=None):
        duration = float(target_duration or 0)
        if duration <= 0:
            raise RuntimeError("original-audio timing requires a positive segment duration")
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            self.command_runner([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                "-i", "anullsrc=r=24000:cl=mono", "-t", f"{duration:.6f}",
                "-c:a", "pcm_s16le", "-y", str(output),
            ])
            on_log(f"Prepared {duration:.3f}s original-audio timing clip")
            return duration
        finally:
            self.active -= 1

    @staticmethod
    def _run(argv):
        completed = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "ffmpeg failed")[-2000:])
