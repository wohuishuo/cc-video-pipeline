import builtins
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import wave

import pytest


LOCALIZATION_ROOT = Path(__file__).resolve().parents[2] / "apps" / "localization"
sys.path.insert(0, str(LOCALIZATION_ROOT))

from localizer.contracts import (  # noqa: E402
    BatchManifest,
    JobRecord,
    StageRecord,
    atomic_write_json,
    sha256_file,
)
from localizer.translation import TranslationSegment  # noqa: E402
from localizer.voice import (  # noqa: E402
    ADAPTER,
    AUTHORIZED_REFERENCE_RELATIVE,
    AUTHORIZED_REFERENCE_TEXT,
    VoiceError,
    classify_duration,
    plan_voice_segments,
    text_sha256,
    validate_authorized_reference,
    validate_clip,
)
from localizer.qwen_voice_worker import process_voice_job, run_voice_batch  # noqa: E402
from localizer.qwen_voice_worker import QwenSynthesizer  # noqa: E402


def write_sine_wave(
    path: Path,
    *,
    seconds: float = 1.0,
    sample_rate: int = 24_000,
    channels: int = 1,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * sample_rate)
    sample = (512).to_bytes(2, byteorder="little", signed=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(sample * frames * channels)


def ru_segment(
    identifier: int, start: float, end: float, text: str
) -> TranslationSegment:
    return TranslationSegment(identifier, start, end, text)


def completed_entry(clip: Path, *, text: str, target_duration: float) -> dict:
    probe = validate_clip(clip, target_duration=target_duration)
    return {
        "id": int(clip.stem),
        "text": text,
        "text_sha256": text_sha256(text),
        "path": clip.name,
        "duration": probe.duration,
        "sha256": probe.sha256,
        "status": "completed",
        "fit": probe.fit,
    }


def test_voice_plan_reuses_only_text_and_hash_matching_valid_clip(tmp_path):
    """Stale text, clip content, or WAV validity must schedule synthesis again."""
    clip = tmp_path / "0001.wav"
    segment = ru_segment(1, 0.0, 1.2, "Тест")
    write_sine_wave(clip, seconds=1.0)

    assert [item.id for item in plan_voice_segments([segment], tmp_path, {}).pending] == [1]

    manifest = {
        "segments": [completed_entry(clip, text="Тест", target_duration=1.2)]
    }
    assert plan_voice_segments([segment], tmp_path, manifest).pending == []

    manifest["segments"][0]["text"] = "Другой текст"
    assert [item.id for item in plan_voice_segments([segment], tmp_path, manifest).pending] == [1]

    manifest["segments"][0]["text"] = "Тест"
    clip.write_bytes(clip.read_bytes() + b"changed")
    assert [item.id for item in plan_voice_segments([segment], tmp_path, manifest).pending] == [1]


def test_voice_plan_requires_the_canonical_manifest_clip_path(tmp_path):
    """A reusable entry must point to the exact public clip path that was validated."""
    clip = tmp_path / "0001.wav"
    segment = ru_segment(1, 0.0, 1.2, "Тест")
    write_sine_wave(clip)
    entry = completed_entry(clip, text=segment.text, target_duration=1.2)
    entry["path"] = "../../other/0001.wav"

    assert [item.id for item in plan_voice_segments([segment], tmp_path, {"segments": [entry]}).pending] == [1]


@pytest.mark.parametrize("bad_clip", ["missing", "zero", "corrupt", "wrong-rate", "stereo"])
def test_voice_plan_retries_missing_or_invalid_clip(tmp_path, bad_clip):
    """A declared completion must not hide an absent, empty, corrupt, or wrong-format WAV."""
    clip = tmp_path / "0001.wav"
    segment = ru_segment(1, 0.0, 1.0, "Проверка")
    if bad_clip == "zero":
        clip.touch()
    elif bad_clip == "corrupt":
        clip.write_bytes(b"not a wav")
    elif bad_clip == "wrong-rate":
        write_sine_wave(clip, sample_rate=16_000)
    elif bad_clip == "stereo":
        write_sine_wave(clip, channels=2)

    manifest = {
        "segments": [
            {
                "id": 1,
                "text": "Проверка",
                "text_sha256": text_sha256("Проверка"),
                "path": "0001.wav",
                "duration": 1.0,
                "sha256": "0" * 64,
                "status": "completed",
                "fit": "fit",
            }
        ]
    }

    assert [item.id for item in plan_voice_segments([segment], tmp_path, manifest).pending] == [1]


@pytest.mark.parametrize(
    ("clip_duration", "target_duration", "expected"),
    [(3.0, 3.0, "fit"), (3.9, 3.0, "compress"), (4.05, 3.0, "compress"), (4.051, 3.0, "overflow")],
)
def test_duration_classification_protects_the_35_percent_rewrite_boundary(
    clip_duration, target_duration, expected
):
    """Moving the 35% boundary would over-compress speech or rewrite usable clips."""
    assert classify_duration(clip_duration, target_duration) == expected


class FakeSynthesizer:
    def __init__(self, outcomes=None):
        self.outcomes = list(outcomes or [])
        self.calls = []
        self.closed = False

    def synthesize(self, text, destination, *, batch_size=None):
        self.calls.append((text, batch_size))
        outcome = self.outcomes.pop(0) if self.outcomes else 0.8
        if isinstance(outcome, BaseException):
            raise outcome
        write_sine_wave(Path(destination), seconds=outcome)

    def close(self):
        self.closed = True


def translation_job(tmp_path, *, job_id="123", segments=None):
    source = tmp_path / f"[{job_id}] source.mp4"
    source.write_bytes(b"fixture media")
    job = JobRecord(id=job_id, source=str(source), source_sha256=sha256_file(source))
    artifact_dir = tmp_path / "russian" / "jobs" / job.id
    artifact_dir.mkdir(parents=True)
    translation = artifact_dir / "translation.ru.json"
    rows = segments or [
        {"id": 1, "start": 0.0, "end": 1.0, "text_ru": "Первый"},
        {"id": 2, "start": 1.0, "end": 2.0, "text_ru": "Второй"},
    ]
    translation.write_text(
        json.dumps({"schema_version": 1, "segments": rows}, ensure_ascii=False),
        encoding="utf-8",
    )
    job.stages["translation"] = StageRecord.completed(
        adapter="ollama@qwen3.5:9b",
        inputs={"source_sha256": job.source_sha256},
        outputs={"translation": str(translation)},
    )
    return job, artifact_dir


def test_worker_persists_each_completion_before_the_next_segment(tmp_path):
    """Deferring the manifest write until job end would lose completed work on interruption."""
    job, artifact_dir = translation_job(tmp_path)
    manifest_path = artifact_dir / "voice" / "manifest.json"

    class ObservingSynthesizer(FakeSynthesizer):
        def synthesize(self, text, destination, *, batch_size=None):
            if text == "Второй":
                persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
                assert [(row["id"], row["status"]) for row in persisted["segments"]] == [
                    (1, "completed")
                ]
            super().synthesize(text, destination, batch_size=batch_size)

    process_voice_job(
        ObservingSynthesizer(),
        job,
        model_id="fixture-model",
        reference=tmp_path / "reference.wav",
        reference_sha256="a" * 64,
        reference_text=AUTHORIZED_REFERENCE_TEXT,
    )

    final = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [(row["id"], row["status"]) for row in final["segments"]] == [
        (1, "completed"),
        (2, "completed"),
    ]
    assert job.stages["voice"].status == "completed"
    assert job.stages["voice"].outputs == {"voice": str(manifest_path)}


def test_worker_resumes_after_interruption_without_resynthesizing_completed_clip(tmp_path):
    """An interrupted run must continue from its first unverified clip."""
    job, artifact_dir = translation_job(tmp_path)
    interrupted = FakeSynthesizer([0.8, KeyboardInterrupt()])

    with pytest.raises(KeyboardInterrupt):
        process_voice_job(
            interrupted,
            job,
            model_id="fixture-model",
            reference=tmp_path / "reference.wav",
            reference_sha256="a" * 64,
            reference_text=AUTHORIZED_REFERENCE_TEXT,
        )

    manifest_path = artifact_dir / "voice" / "manifest.json"
    partial = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [row["id"] for row in partial["segments"]] == [1]

    resumed = FakeSynthesizer()
    process_voice_job(
        resumed,
        job,
        model_id="fixture-model",
        reference=tmp_path / "reference.wav",
        reference_sha256="a" * 64,
        reference_text=AUTHORIZED_REFERENCE_TEXT,
    )

    assert resumed.calls == [("Второй", None)]
    assert [row["id"] for row in json.loads(manifest_path.read_text(encoding="utf-8"))["segments"]] == [1, 2]


class OutOfMemoryError(RuntimeError):
    pass


def test_batch_retries_cuda_oom_at_one_and_cleans_up_without_gpu_imports(tmp_path):
    """A CUDA OOM must clear cached state, retry only that segment, and release one resident model."""
    job, _artifact_dir = translation_job(
        tmp_path,
        segments=[{"id": 1, "start": 0.0, "end": 1.0, "text_ru": "Текст"}],
    )
    source_manifest = tmp_path / "source-manifest.txt"
    source_manifest.write_text("fixture", encoding="utf-8")
    batch_path = tmp_path / "batch-manifest.json"
    batch = BatchManifest(
        manifest=str(source_manifest),
        expected_ids=(job.id,),
        jobs=(job,),
    )
    atomic_write_json(batch_path, batch.to_dict())
    reference = tmp_path / "reference.wav"
    write_sine_wave(reference, seconds=9.05)
    fake = FakeSynthesizer([OutOfMemoryError("CUDA out of memory"), 0.8])
    factories = []
    cache_clears = []

    def factory(model_id, actual_reference, reference_text):
        factories.append((model_id, actual_reference, reference_text))
        return fake

    failures = run_voice_batch(
        batch_path,
        reference=reference,
        reference_text=AUTHORIZED_REFERENCE_TEXT,
        model_id="fixture-model",
        synthesizer_factory=factory,
        clear_cuda_cache=lambda: cache_clears.append(True),
        enforce_authorized_reference=False,
    )

    assert failures == []
    assert len(factories) == 1
    assert fake.calls == [("Текст", None), ("Текст", 1)]
    assert cache_clears == [True]
    assert fake.closed is True
    persisted = BatchManifest.from_dict(json.loads(batch_path.read_text(encoding="utf-8")))
    assert persisted.jobs[0].stages["voice"].status == "completed"


def test_real_qwen_adapter_uses_an_explicit_single_item_batch_on_oom_retry(
    tmp_path, monkeypatch
):
    """The production adapter must turn batch_size=1 into Qwen's list-based batch API."""
    calls = []
    writes = []

    class FakeQwenModel:
        def generate_voice_clone(self, **kwargs):
            calls.append(kwargs)
            return [[0.0]], 24_000

    monkeypatch.setitem(
        sys.modules,
        "soundfile",
        SimpleNamespace(write=lambda *args, **kwargs: writes.append((args, kwargs))),
    )
    synthesizer = object.__new__(QwenSynthesizer)
    synthesizer._model = FakeQwenModel()
    synthesizer._prompt = ["resident-prompt"]

    synthesizer.synthesize("Текст", tmp_path / "clip.wav", batch_size=1)

    assert calls[0]["text"] == ["Текст"]
    assert calls[0]["language"] == ["Russian"]
    assert calls[0]["voice_clone_prompt"] == ["resident-prompt"]
    assert len(writes) == 1


def test_second_cuda_oom_clears_cache_again_and_removes_partial_clip(tmp_path):
    """A failed fallback must release CUDA state before the batch continues."""
    job, artifact_dir = translation_job(
        tmp_path,
        segments=[{"id": 1, "start": 0.0, "end": 1.0, "text_ru": "Текст"}],
    )
    fake = FakeSynthesizer(
        [
            OutOfMemoryError("CUDA out of memory"),
            OutOfMemoryError("CUDA out of memory again"),
        ]
    )
    cache_clears = []

    with pytest.raises(OutOfMemoryError):
        process_voice_job(
            fake,
            job,
            model_id="fixture-model",
            reference=tmp_path / "reference.wav",
            reference_sha256="a" * 64,
            reference_text=AUTHORIZED_REFERENCE_TEXT,
            clear_cuda_cache=lambda: cache_clears.append(True),
        )

    assert cache_clears == [True, True]
    assert list((artifact_dir / "voice" / "clips").glob(".*.wav")) == []
    assert job.stages["voice"].status == "failed"


def test_fully_reusable_batch_does_not_load_model_or_replace_completed_receipt(tmp_path):
    """A restart with complete verified clips must stay reusable through CUDA downtime."""
    job, _artifact_dir = translation_job(
        tmp_path,
        segments=[{"id": 1, "start": 0.0, "end": 1.0, "text_ru": "Текст"}],
    )
    source_manifest = tmp_path / "source-manifest.txt"
    source_manifest.write_text("fixture", encoding="utf-8")
    batch_path = tmp_path / "batch-manifest.json"
    reference = tmp_path / "reference.wav"
    write_sine_wave(reference, seconds=9.05)
    reference_hash = sha256_file(reference)
    process_voice_job(
        FakeSynthesizer(),
        job,
        model_id="fixture-model",
        reference=reference,
        reference_sha256=reference_hash,
        reference_text=AUTHORIZED_REFERENCE_TEXT,
    )
    prior_stage = job.stages["voice"]
    atomic_write_json(
        batch_path,
        BatchManifest(
            manifest=str(source_manifest),
            expected_ids=(job.id,),
            jobs=(job,),
        ).to_dict(),
    )

    def unavailable_factory(*_args):
        raise AssertionError("model must not load for a fully reusable batch")

    assert run_voice_batch(
        batch_path,
        reference=reference,
        reference_text=AUTHORIZED_REFERENCE_TEXT,
        model_id="fixture-model",
        synthesizer_factory=unavailable_factory,
        enforce_authorized_reference=False,
    ) == []
    persisted = BatchManifest.from_dict(json.loads(batch_path.read_text(encoding="utf-8")))
    assert persisted.jobs[0].stages["voice"] == prior_stage


def test_batch_synthesizes_only_requested_job(tmp_path):
    first, _ = translation_job(tmp_path, job_id="111")
    second, _ = translation_job(tmp_path, job_id="222")
    batch_path = tmp_path / "batch-manifest.json"
    source_manifest = tmp_path / "source-manifest.txt"
    source_manifest.write_text("fixture", encoding="utf-8")
    atomic_write_json(
        batch_path,
        BatchManifest(
            manifest=str(source_manifest),
            expected_ids=(first.id, second.id),
            jobs=(first, second),
        ).to_dict(),
    )
    reference = tmp_path / "reference.wav"
    write_sine_wave(reference, seconds=9.05)
    fakes = []

    def factory(*_args):
        fake = FakeSynthesizer()
        fakes.append(fake)
        return fake

    failures = run_voice_batch(
        batch_path,
        reference=reference,
        reference_text=AUTHORIZED_REFERENCE_TEXT,
        model_id="fixture-model",
        synthesizer_factory=factory,
        enforce_authorized_reference=False,
        job_ids={"222"},
    )

    assert failures == []
    persisted = BatchManifest.from_dict(json.loads(batch_path.read_text(encoding="utf-8")))
    assert "voice" not in persisted.jobs[0].stages
    assert persisted.jobs[1].stages["voice"].status == "completed"
    assert len(fakes) == 1


def test_worker_reads_real_translation_contract_and_preserves_other_stage_receipts(tmp_path):
    """Reading an invented field or replacing the stage map would break Task 3 integration."""
    job, _artifact_dir = translation_job(
        tmp_path,
        segments=[{"id": 7, "start": 2.5, "end": 4.0, "text_ru": "Семь"}],
    )
    translation_stage = job.stages["translation"]

    process_voice_job(
        FakeSynthesizer(),
        job,
        model_id="fixture-model",
        reference=tmp_path / "reference.wav",
        reference_sha256="b" * 64,
        reference_text=AUTHORIZED_REFERENCE_TEXT,
    )

    assert job.stages["translation"] == translation_stage
    assert set(job.stages) == {"translation", "voice"}
    manifest_path = Path(job.stages["voice"].outputs["voice"])
    row = json.loads(manifest_path.read_text(encoding="utf-8"))["segments"][0]
    assert (row["id"], row["text"], row["path"]) == (7, "Семь", "clips/0007.wav")


def test_reference_policy_requires_the_authorized_path_text_and_audio_content(
    tmp_path, monkeypatch
):
    """Accepting a different path or transcript would silently clone an unauthorized voice."""
    import localizer.voice as voice_module

    expected = tmp_path / AUTHORIZED_REFERENCE_RELATIVE
    write_sine_wave(expected, seconds=9.05)
    monkeypatch.setattr(
        voice_module,
        "AUTHORIZED_REFERENCE_SHA256",
        sha256_file(expected),
        raising=False,
    )

    assert validate_authorized_reference(
        expected,
        AUTHORIZED_REFERENCE_TEXT,
        project_root=tmp_path,
    ) == expected.resolve()
    with pytest.raises(VoiceError, match="authorized reference path"):
        validate_authorized_reference(
            tmp_path / "other.wav",
            AUTHORIZED_REFERENCE_TEXT,
            project_root=tmp_path,
        )
    with pytest.raises(VoiceError, match="exact authorized reference text"):
        validate_authorized_reference(expected, "Другой текст", project_root=tmp_path)
    write_sine_wave(expected, seconds=9.05, channels=1)
    with expected.open("r+b") as altered:
        altered.seek(100)
        altered.write(b"\x01\x02")
    with pytest.raises(VoiceError, match="authorized reference SHA-256"):
        validate_authorized_reference(
            expected,
            AUTHORIZED_REFERENCE_TEXT,
            project_root=tmp_path,
        )


def test_worker_modules_import_without_torch_or_qwen_tts(monkeypatch):
    """Importing orchestration must not initialize or require the CUDA environment."""
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "torch" or name.startswith("qwen_tts"):
            raise AssertionError(f"GPU package imported eagerly: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    import localizer.voice as voice
    import localizer.qwen_voice_worker as worker

    importlib.reload(voice)
    importlib.reload(worker)
