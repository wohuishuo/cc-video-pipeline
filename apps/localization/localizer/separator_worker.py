"""Resident audio-separator worker for resumable localization batches."""

from __future__ import annotations

import argparse
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


def probe_media_duration(path: str | Path) -> float:
    """Read container duration through ffprobe without decoding the source in Python."""

    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        duration = float(completed.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        raise SeparationError(f"cannot probe source duration: {error}") from error
    if not math.isfinite(duration) or duration <= 0:
        raise SeparationError("source duration must be a positive finite number")
    return duration


def _artifact_dir(job: JobRecord) -> Path:
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

    inputs = separation_inputs(job, model_sha256)
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
                    inputs = {
                        "source_sha256": job.source_sha256,
                        "model_filename": MODEL_FILENAME,
                        "model_sha256": model_sha256,
                    }
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
