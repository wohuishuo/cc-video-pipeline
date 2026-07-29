"""Resident faster-whisper transcription for immutable localization jobs."""

from __future__ import annotations

import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Iterable, Protocol

from .contracts import JobRecord, Segment, StageRecord, atomic_write_json, sha256_file


ADAPTER = "faster-whisper@large-v3"


class TranscriptionError(ValueError):
    """The model output cannot safely become a localization transcript."""


class WhisperModel(Protocol):
    def transcribe(self, source: str, **kwargs: Any) -> tuple[Iterable[Any], Any]: ...


ModelFactory = Callable[..., WhisperModel]


def _job_artifact_dir(job: JobRecord, output_root: str | Path | None) -> Path:
    if output_root is None:
        return Path(job.source).parent / "russian" / "jobs" / job.id
    return Path(output_root) / "jobs" / job.id


def _source_inputs(job: JobRecord) -> dict[str, str]:
    return {"source_sha256": sha256_file(job.source)}


def _as_float(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise TranscriptionError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise TranscriptionError(f"{label} must be a finite number") from error
    if not math.isfinite(result):
        raise TranscriptionError(f"{label} must be a finite number")
    return result


def _validate_segments(raw_segments: Iterable[Any]) -> list[Segment]:
    segments: list[Segment] = []
    previous_end = 0.0
    for index, raw in enumerate(raw_segments, 1):
        start = _as_float(raw.start, f"segment {index} start")
        end = _as_float(raw.end, f"segment {index} end")
        text = raw.text
        if end <= start:
            raise TranscriptionError(f"segment {index} requires a positive duration")
        if start < previous_end:
            raise TranscriptionError("segments must be ordered without overlap")
        if not isinstance(text, str) or not text.strip():
            raise TranscriptionError(f"segment {index} requires non-empty text")

        words: list[dict[str, Any]] = []
        previous_word_end = start
        for word_index, raw_word in enumerate(raw.words, 1):
            word_start = _as_float(raw_word.start, f"segment {index} word {word_index} start")
            word_end = _as_float(raw_word.end, f"segment {index} word {word_index} end")
            word_text = raw_word.word
            if word_end <= word_start:
                raise TranscriptionError(
                    f"segment {index} word {word_index} requires a positive duration"
                )
            if word_start < start or word_end > end:
                raise TranscriptionError(
                    f"segment {index} word {word_index} must be within segment timing"
                )
            if word_start < previous_word_end:
                raise TranscriptionError(f"segment {index} words must be ordered")
            if not isinstance(word_text, str) or not word_text.strip():
                raise TranscriptionError(f"segment {index} word {word_index} requires text")
            words.append({"start": word_start, "end": word_end, "word": word_text})
            previous_word_end = word_end

        segments.append(Segment(id=index, start=start, end=end, text=text, words=words))
        previous_end = end

    if not segments:
        raise TranscriptionError("empty transcript")
    return segments


def _srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def _srt(segments: list[Segment]) -> str:
    return "".join(
        f"{segment.id}\n{_srt_timestamp(segment.start)} --> {_srt_timestamp(segment.end)}\n"
        f"{segment.text}\n\n"
        for segment in segments
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _mark_failed(job: JobRecord, inputs: dict[str, str], error: Exception) -> None:
    job.stages["transcription"] = StageRecord.failed(
        adapter=ADAPTER,
        inputs=inputs,
        outputs={},
        error={"type": type(error).__name__, "message": str(error)},
    )


def transcribe_job(
    model: WhisperModel, job: JobRecord, *, output_root: str | Path | None = None
) -> dict[str, Any]:
    """Transcribe one job with an already-resident model and persist ASR artifacts."""

    inputs: dict[str, str]
    try:
        inputs = _source_inputs(job)
    except Exception as error:
        inputs = {"source_sha256": job.source_sha256}
        _mark_failed(job, inputs, error)
        raise

    artifact_dir = _job_artifact_dir(job, output_root)
    transcript_path = artifact_dir / "transcript.zh.json"
    srt_path = artifact_dir / "transcript.zh.srt"
    try:
        raw_segments, _info = model.transcribe(
            str(Path(job.source)),
            language="zh",
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=True,
        )
        segments = _validate_segments(raw_segments)
        transcript = {"schema_version": 1, "segments": [segment.to_dict() for segment in segments]}
        atomic_write_json(transcript_path, transcript)
        _atomic_write_text(srt_path, _srt(segments))
        job.stages["transcription"] = StageRecord.completed(
            adapter=ADAPTER,
            inputs=inputs,
            outputs={"transcript": str(transcript_path), "srt": str(srt_path)},
        )
        return transcript
    except Exception as error:
        for output in (transcript_path, srt_path):
            if output.exists():
                output.unlink()
        _mark_failed(job, inputs, error)
        raise


def transcribe_batch(
    jobs: list[JobRecord],
    *,
    output_root: str | Path | None = None,
    model_name: str = "large-v3",
    device: str = "cuda",
    compute_type: str = "float16",
    model_factory: ModelFactory | None = None,
) -> list[dict[str, Any]]:
    """Load one CUDA model, process every job, and leave failed jobs retryable."""

    if model_factory is None:
        from faster_whisper import WhisperModel as FasterWhisperModel

        model_factory = FasterWhisperModel
    model = model_factory(model_name, device=device, compute_type=compute_type)
    results: list[dict[str, Any]] = []
    try:
        for job in jobs:
            try:
                transcript = transcribe_job(model, job, output_root=output_root)
            except Exception:
                continue
            results.append({"job_id": job.id, **transcript})
    finally:
        close = getattr(model, "close", None)
        if callable(close):
            close()
    return results
