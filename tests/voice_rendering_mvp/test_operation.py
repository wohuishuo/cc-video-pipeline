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


def test_batch_capable_loop_reduces_model_calls_and_keeps_exact_clip_alignment(tmp_path):
    class BatchAdapter:
        identity = "batch-voice@1"
        output_suffix = ".wav"
        max_workers = 1
        batch_size = 3

        def __init__(self):
            self.calls = []
            self.maximum_active = 0

        def synthesize(self, *args, **kwargs):
            raise AssertionError("batch-capable adapter fell back to one model call per segment")

        def synthesize_batch(self, requests, on_log):
            self.calls.append([request["text"] for request in requests])
            self.maximum_active = 1
            durations = []
            for request in requests:
                request["output"].parent.mkdir(parents=True, exist_ok=True)
                request["output"].write_bytes(f"audio:{request['text']}".encode())
                durations.append(float(request["target_duration"]))
            return durations

    adapter = BatchAdapter()
    result = VoiceRenderingLoop().execute(
        translation_manifest(tmp_path), tmp_path / "batch-out", "batch-op",
        voices=VOICES, adapter=adapter,
    )

    assert result.result_class == "COMPLETED"
    assert [len(batch) for batch in adapter.calls] == [3, 1]
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert [(row["targetLanguage"], row["segmentId"]) for row in receipt["items"]] == [
        ("ru-RU", 1), ("ru-RU", 2), ("en-US", 1), ("en-US", 2),
    ]
    assert [row["end"] - row["start"] for row in receipt["items"]] == [1.0, 1.0, 1.0, 1.0]
    assert receipt["maximumActiveSynthesis"] == 1


def test_failed_batch_retries_only_that_batch_as_independent_clips(tmp_path):
    class RecoveringBatchAdapter(FakeAdapter):
        identity = "recovering-batch@1"
        output_suffix = ".wav"
        batch_size = 3

        def __init__(self):
            super().__init__()
            self.batch_calls = 0

        def synthesize_batch(self, requests, on_log):
            self.batch_calls += 1
            if self.batch_calls == 1:
                raise RuntimeError("simulated GPU batch pressure")
            for request in requests:
                request["output"].parent.mkdir(parents=True, exist_ok=True)
                request["output"].write_bytes(b"batch-audio")
            return [0.75] * len(requests)

    logs = []
    adapter = RecoveringBatchAdapter()
    result = VoiceRenderingLoop().execute(
        translation_manifest(tmp_path), tmp_path / "batch-recovery", "batch-recovery-op",
        voices=VOICES, adapter=adapter, on_log=logs.append,
    )

    assert result.result_class == "COMPLETED"
    assert adapter.batch_calls == 2
    assert len(adapter.calls) == 3
    assert any("serially after batch provider failure" in line for line in logs)
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert all(row["status"] == "COMPLETED" for row in receipt["items"])


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


def test_concurrent_failures_receive_a_serial_recovery_pass(tmp_path):
    class ConcurrencySensitiveAdapter(FakeAdapter):
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
                collided = self.active > 1
            try:
                time.sleep(0.03)
                if collided:
                    raise RuntimeError("provider rejected concurrent request")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(f"audio:{language}:{text}".encode())
                return 0.75
            finally:
                with self._lock:
                    self.active -= 1

    logs = []
    adapter = ConcurrencySensitiveAdapter()
    result = VoiceRenderingLoop().execute(
        translation_manifest(tmp_path), tmp_path / "adaptive-out", "adaptive-op",
        voices=VOICES, adapter=adapter, on_log=logs.append,
    )

    assert result.result_class == "COMPLETED"
    assert adapter.maximum_active == 3
    assert any("serially" in line for line in logs)
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert all(row["status"] == "COMPLETED" for row in receipt["items"])
