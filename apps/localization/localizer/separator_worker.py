"""Resident audio-separator worker for resumable localization batches."""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Protocol

from .contracts import (
    BatchManifest,
    JobRecord,
    StageRecord,
    atomic_write_json,
    sha256_file,
)
from .separation import (
    ADAPTER,
    MODEL_FILENAME,
    SeparationError,
    load_separation_receipt,
    map_separator_outputs,
    separation_inputs,
    separation_is_reusable,
    validate_instrumental,
    validate_vocals,
)


class SeparatorAdapter(Protocol):
    def load_model(self, filename: str) -> Any: ...

    def separate(self, source: str) -> list[str]: ...


SeparatorFactory = Callable[..., SeparatorAdapter]
DurationProbe = Callable[[str | Path], float]


def _positive_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def _stream_duration(stream: dict[str, Any]) -> float | None:
    duration = _positive_float(stream.get("duration"))
    if duration is not None:
        return duration
    duration_ticks = _positive_float(stream.get("duration_ts"))
    time_base = stream.get("time_base")
    if duration_ticks is None or not isinstance(time_base, str):
        return None
    try:
        duration = duration_ticks * float(Fraction(time_base))
    except (ValueError, ZeroDivisionError):
        return None
    return _positive_float(duration)


def _decoded_audio_duration(path: str | Path) -> float:
    try:
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-v",
                "error",
                "-progress",
                "pipe:1",
                "-nostats",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-vn",
                "-f",
                "null",
                "-",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SeparationError(f"cannot decode source audio duration: {error}") from error
    durations = [
        _positive_float(line.partition("=")[2])
        for line in completed.stdout.splitlines()
        if line.startswith("out_time_us=")
    ]
    decoded = [value / 1_000_000 for value in durations if value is not None]
    if not decoded:
        raise SeparationError("cannot decode source audio duration")
    return max(decoded)


def probe_media_duration(path: str | Path) -> float:
    """Read the selected audio timeline, decoding only when stream metadata is absent."""

    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=duration,duration_ts,time_base",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        value = json.loads(completed.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise SeparationError(f"cannot probe source audio duration: {error}") from error
    streams = value.get("streams") if isinstance(value, dict) else None
    if (
        not isinstance(streams, list)
        or len(streams) != 1
        or not isinstance(streams[0], dict)
    ):
        raise SeparationError("source requires exactly one selected audio stream")
    duration = _stream_duration(streams[0])
    return _decoded_audio_duration(path) if duration is None else duration


def _artifact_dir(job: JobRecord) -> Path:
    translation = job.stages.get("translation")
    if isinstance(translation, StageRecord):
        translated = translation.outputs.get("translation")
        if translated:
            return Path(translated).parent
    return Path(job.source).parent / "russian" / "jobs" / job.id


def _clear_workspace(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _remove_paths(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def _separation_final_paths(job: JobRecord) -> tuple[Path, Path, Path]:
    audio_dir = _artifact_dir(job) / "audio"
    return (
        audio_dir / "vocals.wav",
        audio_dir / "no_vocals.wav",
        audio_dir / "separation.json",
    )


def _mark_failed(
    job: JobRecord,
    inputs: dict[str, str],
    error: BaseException,
) -> None:
    job.stages["separation"] = StageRecord.failed(
        adapter=ADAPTER,
        inputs=inputs,
        outputs={},
        error={"type": type(error).__name__, "message": str(error)},
    )


def _fallback_inputs(job: JobRecord, model_sha256: str) -> dict[str, str]:
    return {
        "source_sha256": job.source_sha256,
        "model_filename": MODEL_FILENAME,
        "model_sha256": model_sha256,
    }


def _copy_to_temporary(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.stem}.",
        suffix=".wav",
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        shutil.copyfile(source, temporary)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    return temporary


def process_separation_job(
    separator: SeparatorAdapter,
    job: JobRecord,
    *,
    model_sha256: str,
    output_dir: str | Path,
    duration_probe: DurationProbe = probe_media_duration,
) -> dict[str, Any]:
    """Separate and atomically publish one job while preserving stage ownership."""

    try:
        inputs = separation_inputs(job, model_sha256)
    except BaseException as error:
        _remove_paths(_separation_final_paths(job))
        _mark_failed(job, _fallback_inputs(job, model_sha256), error)
        raise
    if separation_is_reusable(job, model_sha256=model_sha256):
        return load_separation_receipt(job.stages["separation"].outputs["separation"])

    workspace = Path(output_dir)
    workspace.mkdir(parents=True, exist_ok=True)
    _clear_workspace(workspace)
    audio_dir = _artifact_dir(job) / "audio"
    vocals_path = audio_dir / "vocals.wav"
    instrumental_path = audio_dir / "no_vocals.wav"
    receipt_path = audio_dir / "separation.json"
    final_paths = (vocals_path, instrumental_path, receipt_path)
    temporary_paths: list[Path] = []
    job.stages["separation"] = StageRecord.running(
        adapter=ADAPTER,
        inputs=inputs,
        outputs={
            "vocals": str(vocals_path),
            "instrumental": str(instrumental_path),
            "separation": str(receipt_path),
        },
    )
    try:
        source_duration = duration_probe(job.source)
        output_files = separator.separate(job.source)
        mapped = map_separator_outputs(output_files, base_dir=workspace)
        vocals_probe = validate_vocals(mapped.vocals, source_duration)
        instrumental_probe = validate_instrumental(mapped.instrumental, source_duration)

        temporary_vocals = _copy_to_temporary(mapped.vocals, vocals_path)
        temporary_paths.append(temporary_vocals)
        temporary_instrumental = _copy_to_temporary(
            mapped.instrumental, instrumental_path
        )
        temporary_paths.append(temporary_instrumental)
        validate_vocals(temporary_vocals, source_duration)
        validate_instrumental(temporary_instrumental, source_duration)
        os.replace(temporary_vocals, vocals_path)
        temporary_paths.remove(temporary_vocals)
        os.replace(temporary_instrumental, instrumental_path)
        temporary_paths.remove(temporary_instrumental)

        receipt = {
            "schema_version": 1,
            "adapter": ADAPTER,
            "source_sha256": inputs["source_sha256"],
            "source_duration": float(source_duration),
            "model_filename": MODEL_FILENAME,
            "model_sha256": model_sha256,
            "stems": {
                "vocals": {
                    "path": vocals_path.name,
                    "duration": vocals_probe.duration,
                    "sha256": vocals_probe.sha256,
                },
                "instrumental": {
                    "path": instrumental_path.name,
                    "duration": instrumental_probe.duration,
                    "sha256": instrumental_probe.sha256,
                },
            },
        }
        atomic_write_json(receipt_path, receipt)
        job.stages["separation"] = StageRecord.completed(
            adapter=ADAPTER,
            inputs=inputs,
            outputs={
                "vocals": str(vocals_path),
                "instrumental": str(instrumental_path),
                "separation": str(receipt_path),
            },
        )
        return receipt
    except BaseException as error:
        _remove_paths(final_paths)
        _mark_failed(job, inputs, error)
        raise
    finally:
        _remove_paths(tuple(temporary_paths))
        _clear_workspace(workspace)


def _load_batch(path: Path) -> BatchManifest:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SeparationError(f"cannot read batch manifest: {error}") from error
    try:
        return BatchManifest.from_dict(value)
    except (KeyError, TypeError, ValueError) as error:
        raise SeparationError(f"invalid batch manifest: {error}") from error


def _default_separator_factory(**kwargs: Any) -> SeparatorAdapter:
    from audio_separator.separator import Separator

    return Separator(**kwargs)


def _failure(job: JobRecord, error: BaseException) -> dict[str, str]:
    return {
        "job_id": job.id,
        "type": type(error).__name__,
        "message": str(error),
    }


def run_separation_batch(
    batch_manifest: str | Path,
    *,
    model_dir: str | Path,
    separator_factory: SeparatorFactory | None = None,
    duration_probe: DurationProbe = probe_media_duration,
) -> list[dict[str, str]]:
    """Load one exact model and resume every job requiring separation."""

    batch_path = Path(batch_manifest)
    batch = _load_batch(batch_path)
    models = Path(model_dir)
    model_path = models / MODEL_FILENAME
    if not model_path.is_file() or model_path.stat().st_size <= 0:
        raise SeparationError(f"missing separator model: {model_path}")
    model_sha256 = sha256_file(model_path)
    failures: list[dict[str, str]] = []
    pending: list[JobRecord] = []
    for job in batch.jobs:
        try:
            separation_inputs(job, model_sha256)
        except Exception as error:
            _remove_paths(_separation_final_paths(job))
            _mark_failed(job, _fallback_inputs(job, model_sha256), error)
            failures.append(_failure(job, error))
            atomic_write_json(batch_path, batch.to_dict())
            continue
        if separation_is_reusable(job, model_sha256=model_sha256):
            continue
        pending.append(job)
    if not pending:
        return failures

    workspace = batch_path.parent / ".separator-worker"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    factory = _default_separator_factory if separator_factory is None else separator_factory
    separator: SeparatorAdapter | None = None
    try:
        try:
            separator = factory(
                model_file_dir=str(models),
                output_dir=str(workspace),
                output_format="WAV",
                use_autocast=True,
            )
            separator.load_model(MODEL_FILENAME)
        except Exception as error:
            for job in pending:
                try:
                    inputs = separation_inputs(job, model_sha256)
                except BaseException:
                    inputs = _fallback_inputs(job, model_sha256)
                _mark_failed(job, inputs, error)
                failures.append(_failure(job, error))
            atomic_write_json(batch_path, batch.to_dict())
            return failures

        for job in pending:
            try:
                process_separation_job(
                    separator,
                    job,
                    model_sha256=model_sha256,
                    output_dir=workspace,
                    duration_probe=duration_probe,
                )
            except Exception as error:
                failures.append(_failure(job, error))
            finally:
                atomic_write_json(batch_path, batch.to_dict())
    finally:
        if separator is not None:
            close = getattr(separator, "close", None)
            if callable(close):
                close()
        if workspace.exists():
            shutil.rmtree(workspace)
    return failures


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resume two-stem source separation for a localization batch."
    )
    parser.add_argument("--batch-manifest", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    failures = run_separation_batch(
        args.batch_manifest,
        model_dir=args.model_dir,
    )
    print(json.dumps({"failures": failures}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
