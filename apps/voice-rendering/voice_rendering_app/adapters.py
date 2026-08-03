"""Replaceable production adapters for translated voice rendering."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import threading
import time


QWEN3_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
QWEN3_LANGUAGE_NAMES = {
    "zh": "Chinese", "en": "English", "ja": "Japanese", "ko": "Korean",
    "ru": "Russian", "de": "German", "fr": "French", "pt": "Portuguese",
    "es": "Spanish", "it": "Italian",
}


def resolve_qwen_device(requested, *, cuda_available):
    """Resolve a portable Qwen device policy without silently pinning capable PCs to CPU."""
    value = str(requested).strip().lower()
    if value == "cpu":
        return "cpu"
    if value in {"auto", "cuda"}:
        return "cuda" if cuda_available else "cpu"
    if value == "xpu":
        return "cpu"
    raise RuntimeError(f"unsupported Qwen device policy: {requested}")


class _QwenPresetEngine:
    def __init__(self, device):
        self.device = device
        self.model = None

    def load(self):
        import torch
        from qwen_tts import Qwen3TTSModel

        device = resolve_qwen_device(self.device, cuda_available=torch.cuda.is_available())
        self.resolved_device = device
        dtype = torch.float32 if device == "cpu" else torch.bfloat16
        self.model = Qwen3TTSModel.from_pretrained(
            QWEN3_MODEL_ID, device_map=device, dtype=dtype, attn_implementation="sdpa"
        )

    def synth_preset(self, text, language, speaker):
        if self.model is None:
            raise RuntimeError("Qwen3-TTS model is not loaded")
        resolved = QWEN3_LANGUAGE_NAMES.get(str(language).lower())
        if resolved is None:
            raise RuntimeError(f"Qwen3-TTS locale is unsupported: {language}")
        wavs, sample_rate = self.model.generate_custom_voice(
            text=text, language=resolved, speaker=speaker, instruct=""
        )
        if not isinstance(wavs, list) or len(wavs) != 1:
            raise RuntimeError("Qwen3-TTS must return exactly one waveform")
        return wavs[0], sample_rate


class EdgeTtsAdapter:
    identity = "edge-tts@1"
    output_suffix = ".mp3"
    max_workers = 3
    _TRANSIENT_ERRORS = (
        "NoAudioReceived",
        "No audio was received",
        "TimeoutError",
        "ConnectionError",
        "Connection reset",
        "temporarily unavailable",
    )

    def __init__(
        self,
        *,
        rate="+0%",
        volume="+0%",
        command_runner=None,
        save_runner=None,
        duration_probe=None,
        sleep=None,
        max_attempts=3,
    ):
        if command_runner is not None and save_runner is not None:
            raise ValueError("choose one Edge transport runner")
        self.rate = rate
        self.volume = volume
        self.command_runner = command_runner
        self.save_runner = save_runner or self._save
        self.duration_probe = duration_probe or self._probe
        self.sleep = sleep or time.sleep
        self.max_attempts = int(max_attempts)
        if self.max_attempts < 1:
            raise ValueError("Edge attempts must be positive")
        self.active = 0
        self.maximum_active = 0
        self._active_lock = threading.Lock()
        self._thread_state = threading.local()

    @property
    def last_attempts(self):
        return int(getattr(self._thread_state, "last_attempts", 1))

    def synthesize(self, text, language, voice, output, on_log, *, target_duration=None):
        with self._active_lock:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
        try:
            for attempt in range(1, self.max_attempts + 1):
                self._thread_state.last_attempts = attempt
                Path(output).unlink(missing_ok=True)
                try:
                    if self.command_runner is not None:
                        argv = [
                            sys.executable, "-m", "edge_tts", "--text", text,
                            "--voice", voice, "--rate", self.rate, "--volume",
                            self.volume, "--write-media", str(output),
                        ]
                        self.command_runner(argv)
                    else:
                        self.save_runner(text, voice, Path(output))
                    duration = float(self.duration_probe(output))
                    on_log(f"Synthesized {duration:.3f}s with {voice}")
                    return duration
                except Exception as error:
                    transient = any(token.casefold() in str(error).casefold() for token in self._TRANSIENT_ERRORS)
                    if not transient or attempt >= self.max_attempts:
                        raise
                    delay = float(2 ** (attempt - 1))
                    on_log(
                        f"Edge TTS transient failure; retry {attempt + 1}/{self.max_attempts} "
                        f"in {delay:.0f}s"
                    )
                    self.sleep(delay)
            raise RuntimeError("Edge TTS attempts exhausted")
        finally:
            with self._active_lock:
                self.active -= 1

    def _save(self, text, voice, output):
        import edge_tts

        asyncio.run(
            edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=self.rate,
                volume=self.volume,
                connect_timeout=10,
                receive_timeout=15,
            ).save(str(output))
        )

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
    max_workers = 1

    def __init__(self, *, device="auto", engine_factory=None, audio_writer=None):
        self.device = device
        self.engine_factory = engine_factory or self._engine
        self.audio_writer = audio_writer or self._write_wav
        self._resident = None
        self._reported_device = False
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
            engine = self._get_engine()
            if not self._reported_device:
                on_log(f"Qwen3-TTS device: {getattr(engine, 'resolved_device', self.device)}")
                self._reported_device = True
            audio, sample_rate = engine.synth_preset(
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
        return _QwenPresetEngine(self.device)

    @staticmethod
    def _write_wav(path, audio, sample_rate):
        import soundfile

        soundfile.write(str(path), audio, sample_rate, format="WAV")


class OriginalAudioAdapter:
    """Create timing clips while preserving the source track at composition."""

    identity = "original-audio-silence@1"
    output_suffix = ".wav"
    max_workers = 1

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
