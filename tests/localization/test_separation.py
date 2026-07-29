import builtins
import importlib
import json
from pathlib import Path
import sys
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
from localizer.separation import (  # noqa: E402
    ADAPTER,
    MODEL_FILENAME,
    SeparationError,
    map_separator_outputs,
    separation_is_reusable,
    validate_instrumental,
)
from localizer.separator_worker import (  # noqa: E402
    process_separation_job,
    run_separation_batch,
)


def write_sine_wave(
    path: Path,
    *,
    seconds: float = 1.0,
    sample_rate: int = 16_000,
    channels: int = 2,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * sample_rate)
    sample = (512).to_bytes(2, byteorder="little", signed=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(sample * frames * channels)


def make_job(tmp_path: Path, job_id: str = "123") -> JobRecord:
    source = tmp_path / f"[{job_id}] source.mp4"
    source.write_bytes(f"fixture-{job_id}".encode())
    job = JobRecord(id=job_id, source=str(source), source_sha256=sha256_file(source))
    job.stages["transcription"] = StageRecord.completed(
        adapter="fixture-asr",
        inputs={"source_sha256": job.source_sha256},
        outputs={"transcript": str(source)},
    )
    return job


class FakeSeparator:
    def __init__(self, output_dir: Path, outcomes=None):
        self.output_dir = Path(output_dir)
        self.outcomes = list(outcomes or [])
        self.separate_calls: list[str] = []
        self.load_calls: list[str] = []
        self.closed = False

    def load_model(self, filename: str) -> None:
        self.load_calls.append(filename)

    def separate(self, source: str) -> list[str]:
        self.separate_calls.append(source)
        outcome = self.outcomes.pop(0) if self.outcomes else (2.0, 2.0)
        if isinstance(outcome, BaseException):
            partial = self.output_dir / "partial_(Vocals)_model.wav"
            write_sine_wave(partial, seconds=0.2)
            raise outcome
        vocals_seconds, instrumental_seconds = outcome
        source_name = Path(source).stem
        vocals = self.output_dir / f"{source_name}_(Vocals)_MDX23C.wav"
        instrumental = self.output_dir / f"{source_name}_(Instrumental)_MDX23C.wav"
        write_sine_wave(vocals, seconds=vocals_seconds)
        write_sine_wave(instrumental, seconds=instrumental_seconds)
        return [str(instrumental), str(vocals)]

    def close(self) -> None:
        self.closed = True


def test_separation_rejects_missing_short_and_invalid_instrumental(tmp_path):
    """Removing missing, decode, or duration checks would admit an unusable mix bed."""
    source_duration = 10.0
    with pytest.raises(SeparationError, match="missing instrumental"):
        validate_instrumental(tmp_path / "missing.wav", source_duration)

    corrupt = tmp_path / "corrupt.wav"
    corrupt.write_bytes(b"not a wav")
    with pytest.raises(SeparationError, match="invalid instrumental WAV"):
        validate_instrumental(corrupt, source_duration)

    short = tmp_path / "short.wav"
    write_sine_wave(short, seconds=2.0)
    with pytest.raises(SeparationError, match="duration"):
        validate_instrumental(short, source_duration)


def test_instrumental_duration_uses_an_explicit_tenth_second_tolerance(tmp_path):
    """Moving or removing the tolerance would accept truncated stems or reject frame rounding."""
    within = tmp_path / "within.wav"
    outside = tmp_path / "outside.wav"
    write_sine_wave(within, seconds=9.91)
    write_sine_wave(outside, seconds=9.89)

    assert validate_instrumental(within, 10.0).duration == pytest.approx(9.91)
    with pytest.raises(SeparationError, match="duration"):
        validate_instrumental(outside, 10.0)


def test_output_mapping_is_order_independent_and_rejects_ambiguous_names(tmp_path):
    """Depending on list order or accepting two candidates would swap or guess the final bed."""
    vocals = tmp_path / "source_(Vocals)_MDX23C.wav"
    instrumental = tmp_path / "source_(Instrumental)_MDX23C.wav"

    mapped = map_separator_outputs([instrumental.name, vocals.name], base_dir=tmp_path)

    assert mapped.vocals == vocals
    assert mapped.instrumental == instrumental
    with pytest.raises(SeparationError, match="ambiguous instrumental"):
        map_separator_outputs(
            [vocals.name, instrumental.name, "other_(Instrumental)_MDX23C.wav"],
            base_dir=tmp_path,
        )
    with pytest.raises(SeparationError, match="missing vocals"):
        map_separator_outputs([instrumental.name], base_dir=tmp_path)


def test_process_job_retains_both_stems_and_mutates_only_separation_stage(tmp_path):
    """Dropping the QA stem, publishing raw names, or replacing another receipt breaks ownership."""
    job = make_job(tmp_path)
    prior_transcription = job.stages["transcription"]
    workspace = tmp_path / "worker-output"
    workspace.mkdir()
    separator = FakeSeparator(workspace)

    receipt = process_separation_job(
        separator,
        job,
        model_sha256="a" * 64,
        output_dir=workspace,
        duration_probe=lambda _source: 2.0,
    )

    audio_dir = Path(job.source).parent / "russian" / "jobs" / job.id / "audio"
    vocals = audio_dir / "vocals.wav"
    instrumental = audio_dir / "no_vocals.wav"
    manifest = audio_dir / "separation.json"
    assert vocals.is_file() and instrumental.is_file() and manifest.is_file()
    assert receipt["stems"]["vocals"]["path"] == "vocals.wav"
    assert receipt["stems"]["instrumental"]["path"] == "no_vocals.wav"
    assert set(job.stages) == {"transcription", "separation"}
    assert job.stages["transcription"] == prior_transcription
    assert job.stages["separation"].outputs == {
        "vocals": str(vocals),
        "instrumental": str(instrumental),
        "separation": str(manifest),
    }
    assert list(workspace.iterdir()) == []


def test_failed_or_short_separation_cleans_partial_outputs_and_stays_resumable(tmp_path):
    """Publishing one stem or leaving raw partials would make a failed job look consumable."""
    job = make_job(tmp_path)
    prior_transcription = job.stages["transcription"]
    workspace = tmp_path / "worker-output"
    workspace.mkdir()
    separator = FakeSeparator(workspace, outcomes=[(2.0, 0.4)])

    with pytest.raises(SeparationError, match="instrumental duration"):
        process_separation_job(
            separator,
            job,
            model_sha256="b" * 64,
            output_dir=workspace,
            duration_probe=lambda _source: 2.0,
        )

    audio_dir = Path(job.source).parent / "russian" / "jobs" / job.id / "audio"
    assert not (audio_dir / "vocals.wav").exists()
    assert not (audio_dir / "no_vocals.wav").exists()
    assert not (audio_dir / "separation.json").exists()
    assert list(workspace.iterdir()) == []
    assert job.stages["separation"].status == "failed"
    assert job.stages["separation"].outputs == {}
    assert job.stages["transcription"] == prior_transcription


def test_model_error_cleans_undeclared_raw_partial(tmp_path):
    """A separator exception before returning filenames must still clean its workspace."""
    job = make_job(tmp_path)
    workspace = tmp_path / "worker-output"
    workspace.mkdir()

    with pytest.raises(RuntimeError, match="model failed"):
        process_separation_job(
            FakeSeparator(workspace, outcomes=[RuntimeError("model failed")]),
            job,
            model_sha256="c" * 64,
            output_dir=workspace,
            duration_probe=lambda _source: 2.0,
        )

    assert list(workspace.iterdir()) == []
    assert job.stages["separation"].status == "failed"


def test_reuse_requires_stage_inputs_receipt_and_current_stem_fingerprints(tmp_path):
    """A stale source/model or altered stem must schedule separation again."""
    job = make_job(tmp_path)
    workspace = tmp_path / "worker-output"
    workspace.mkdir()
    separator = FakeSeparator(workspace)
    process_separation_job(
        separator,
        job,
        model_sha256="d" * 64,
        output_dir=workspace,
        duration_probe=lambda _source: 2.0,
    )

    assert separation_is_reusable(job, model_sha256="d" * 64)
    assert not separation_is_reusable(job, model_sha256="e" * 64)
    source = Path(job.source)
    original_source = source.read_bytes()
    source.write_bytes(original_source + b"changed")
    assert not separation_is_reusable(job, model_sha256="d" * 64)
    source.write_bytes(original_source)
    assert separation_is_reusable(job, model_sha256="d" * 64)
    Path(job.stages["separation"].outputs["instrumental"]).write_bytes(b"changed")
    assert not separation_is_reusable(job, model_sha256="d" * 64)


def test_batch_loads_one_separator_and_one_model_for_all_pending_jobs(tmp_path):
    """Constructing or loading per job would exhaust an 8 GB GPU and defeat residency."""
    first = make_job(tmp_path, "111")
    second = make_job(tmp_path, "222")
    source_manifest = tmp_path / "source-manifest.txt"
    source_manifest.write_text("fixture", encoding="utf-8")
    batch_path = tmp_path / "batch-manifest.json"
    atomic_write_json(
        batch_path,
        BatchManifest(
            manifest=str(source_manifest),
            expected_ids=(first.id, second.id),
            jobs=(first, second),
        ).to_dict(),
    )
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / MODEL_FILENAME).write_bytes(b"fixture model")
    factories = []

    def factory(**kwargs):
        fake = FakeSeparator(Path(kwargs["output_dir"]))
        factories.append((kwargs, fake))
        return fake

    failures = run_separation_batch(
        batch_path,
        model_dir=model_dir,
        separator_factory=factory,
        duration_probe=lambda _source: 2.0,
    )

    assert failures == []
    assert len(factories) == 1
    kwargs, separator = factories[0]
    assert kwargs == {
        "model_file_dir": str(model_dir),
        "output_dir": str(batch_path.parent / ".separator-worker"),
        "output_format": "WAV",
        "use_autocast": True,
    }
    assert separator.load_calls == [MODEL_FILENAME]
    assert separator.separate_calls == [first.source, second.source]
    assert separator.closed is True
    persisted = BatchManifest.from_dict(json.loads(batch_path.read_text(encoding="utf-8")))
    assert [job.stages["separation"].status for job in persisted.jobs] == [
        "completed",
        "completed",
    ]
    assert all(job.stages["transcription"].adapter == "fixture-asr" for job in persisted.jobs)
    assert not (batch_path.parent / ".separator-worker").exists()


def test_fully_reusable_batch_does_not_import_or_load_separator(tmp_path):
    """A restart with verified fingerprints must survive an unavailable model runtime."""
    job = make_job(tmp_path)
    workspace = tmp_path / "worker-output"
    workspace.mkdir()
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    model = model_dir / MODEL_FILENAME
    model.write_bytes(b"fixture model")
    process_separation_job(
        FakeSeparator(workspace),
        job,
        model_sha256=sha256_file(model),
        output_dir=workspace,
        duration_probe=lambda _source: 2.0,
    )
    source_manifest = tmp_path / "source-manifest.txt"
    source_manifest.write_text("fixture", encoding="utf-8")
    batch_path = tmp_path / "batch-manifest.json"
    atomic_write_json(
        batch_path,
        BatchManifest(
            manifest=str(source_manifest),
            expected_ids=(job.id,),
            jobs=(job,),
        ).to_dict(),
    )

    def unavailable_factory(**_kwargs):
        raise AssertionError("separator must not load for a reusable batch")

    assert run_separation_batch(
        batch_path,
        model_dir=model_dir,
        separator_factory=unavailable_factory,
        duration_probe=lambda _source: 2.0,
    ) == []


def test_batch_interruption_is_persisted_and_propagated_for_resume(tmp_path):
    """Swallowing Ctrl-C as a normal job failure would keep running after operator interruption."""
    job = make_job(tmp_path)
    source_manifest = tmp_path / "source-manifest.txt"
    source_manifest.write_text("fixture", encoding="utf-8")
    batch_path = tmp_path / "batch-manifest.json"
    atomic_write_json(
        batch_path,
        BatchManifest(
            manifest=str(source_manifest),
            expected_ids=(job.id,),
            jobs=(job,),
        ).to_dict(),
    )
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / MODEL_FILENAME).write_bytes(b"fixture model")
    created = []

    def factory(**kwargs):
        separator = FakeSeparator(
            Path(kwargs["output_dir"]), outcomes=[KeyboardInterrupt()]
        )
        created.append(separator)
        return separator

    with pytest.raises(KeyboardInterrupt):
        run_separation_batch(
            batch_path,
            model_dir=model_dir,
            separator_factory=factory,
            duration_probe=lambda _source: 2.0,
        )

    persisted = BatchManifest.from_dict(json.loads(batch_path.read_text(encoding="utf-8")))
    assert persisted.jobs[0].stages["separation"].status == "failed"
    assert created[0].closed is True
    assert not (batch_path.parent / ".separator-worker").exists()


def test_orchestration_modules_import_without_audio_separator(monkeypatch):
    """Importing status/orchestration code must not load or download the real model runtime."""
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "audio_separator" or name.startswith("audio_separator."):
            raise AssertionError(f"separator package imported eagerly: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    import localizer.separation as separation
    import localizer.separator_worker as worker

    importlib.reload(separation)
    importlib.reload(worker)
    assert worker.ADAPTER == ADAPTER
