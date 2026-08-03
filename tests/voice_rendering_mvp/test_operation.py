import json
from pathlib import Path
import sys
import threading
import time


APP = Path(__file__).resolve().parents[2] / "apps" / "voice-rendering"
sys.path.insert(0, str(APP))

from .helpers import translation_manifest  # noqa: E402
from voice_rendering_app.operation import VoiceRenderingLoop  # noqa: E402


class FakeAdapter:
    identity = "fake-voice@1"
    output_suffix = ".mp3"

    def __init__(self, failures=()):
        self.failures = set(failures)
        self.calls = []
        self.active = 0
        self.maximum_active = 0

    def synthesize(self, text, language, voice, output, on_log, *, target_duration=None):
        self.calls.append((voice, text))
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            if text in self.failures:
                raise RuntimeError(f"failed {text}")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(f"audio:{voice}:{text}".encode())
            return 0.75
        finally:
            self.active -= 1


VOICES = {"ru-RU": "ru-RU-DmitryNeural", "en-US": "en-US-GuyNeural"}


def test_loop_renders_translation_order_one_clip_at_a_time(tmp_path):
    result = VoiceRenderingLoop().execute(
        translation_manifest(tmp_path), tmp_path / "out", "op-1", voices=VOICES, adapter=FakeAdapter()
    )

    assert result.result_class == "COMPLETED"
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert [(row["targetLanguage"], row["segmentId"]) for row in receipt["items"]] == [
        ("ru-RU", 1), ("ru-RU", 2), ("en-US", 1), ("en-US", 2),
    ]
    assert all(Path(row["clip"]["path"]).is_file() for row in receipt["items"])
    assert receipt["maximumActiveSynthesis"] == 1
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["clips"]) == 4
    assert manifest["voices"] == VOICES


def test_failed_clip_prevents_manifest_and_retry_reuses_completed_clips(tmp_path):
    source = translation_manifest(tmp_path)
    output = tmp_path / "out"
    failed = VoiceRenderingLoop().execute(
        source, output, "op-1", voices=VOICES, adapter=FakeAdapter({"Привет"})
    )
    assert failed.result_class == "FAILED"
    assert failed.manifest_path is None

    retry_adapter = FakeAdapter()
    completed = VoiceRenderingLoop().execute(source, output, "op-1", voices=VOICES, adapter=retry_adapter)
    assert completed.result_class == "COMPLETED"
    assert retry_adapter.calls == [("ru-RU-DmitryNeural", "Привет")]


def test_replay_skips_adapter_and_voice_change_conflicts(tmp_path):
    source = translation_manifest(tmp_path)
    output = tmp_path / "out"
    VoiceRenderingLoop().execute(source, output, "op-1", voices=VOICES, adapter=FakeAdapter())
    replay_adapter = FakeAdapter()
    replay = VoiceRenderingLoop().execute(source, output, "op-1", voices=VOICES, adapter=replay_adapter)
    changed = VoiceRenderingLoop().execute(
        source, output, "op-1", voices={**VOICES, "ru-RU": "ru-RU-SvetlanaNeural"}, adapter=FakeAdapter()
    )
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert replay_adapter.calls == []
    assert changed.result_class == "REJECTED_CONFLICT"


def test_voice_loop_passes_locale_duration_and_uses_adapter_suffix(tmp_path):
    observed = []

    class WavAdapter(FakeAdapter):
        identity = "wav-provider@1"
        output_suffix = ".wav"

        def synthesize(self, text, language, voice, output, on_log, *, target_duration=None):
            observed.append((language, target_duration, output.name))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"voice")
            return target_duration

    result = VoiceRenderingLoop().execute(
        translation_manifest(tmp_path), tmp_path / "wav-out", "wav-op",
        voices=VOICES, adapter=WavAdapter(),
    )

    assert result.result_class == "COMPLETED"
    assert [(language, duration) for language, duration, _ in observed] == [
        ("ru-RU", 1.0), ("ru-RU", 1.0), ("en-US", 1.0), ("en-US", 1.0)
    ]
    assert all(name.endswith(".wav.partial") for _, _, name in observed)


def test_edge_capable_loop_bounds_concurrency_and_keeps_receipt_order(tmp_path):
    class ConcurrentAdapter(FakeAdapter):
        max_workers = 3

        def __init__(self):
            super().__init__()
            self._lock = threading.Lock()

        @property
        def last_attempts(self):
            return 1

        def synthesize(self, text, language, voice, output, on_log, *, target_duration=None):
            with self._lock:
                self.active += 1
                self.maximum_active = max(self.maximum_active, self.active)
            try:
                time.sleep(0.05)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(f"audio:{language}:{text}".encode())
                return 0.75
            finally:
                with self._lock:
                    self.active -= 1

    adapter = ConcurrentAdapter()
    result = VoiceRenderingLoop().execute(
        translation_manifest(tmp_path),
        tmp_path / "concurrent-out",
        "concurrent-op",
        voices=VOICES,
        adapter=adapter,
    )

    assert result.result_class == "COMPLETED"
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert [(row["targetLanguage"], row["segmentId"]) for row in receipt["items"]] == [
        ("ru-RU", 1), ("ru-RU", 2), ("en-US", 1), ("en-US", 2),
    ]
    assert receipt["maximumActiveSynthesis"] == 3
    assert all(row["attempts"] == 1 for row in receipt["items"])
    assert all(row["elapsedSeconds"] > 0 for row in receipt["items"])
