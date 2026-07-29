"""Resident Qwen3-TTS CUDA worker with per-segment recovery receipts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import gc
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Protocol

from .contracts import (
    BatchManifest,
    JobRecord,
    StageRecord,
    atomic_write_json,
    sha256_file,
)
from .voice import (
    ADAPTER,
    AUTHORIZED_REFERENCE_TEXT,
    VoiceError,
    VoiceSegment,
    load_voice_manifest,
    plan_voice_segments,
    text_sha256,
    validate_authorized_reference,
    validate_clip,
    voice_segments,
)


MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"


class Synthesizer(Protocol):
    def synthesize(
        self, text: str, destination: str | Path, *, batch_size: int | None = None
    ) -> None: ...

    def close(self) -> None: ...


SynthesizerFactory = Callable[[str, Path, str], Synthesizer]
CacheCleanup = Callable[[], None]


@dataclass(frozen=True)
class VoiceContext:
    model_id: str
    reference: Path
    reference_sha256: str
    reference_text: str

    @property
    def inputs(self) -> dict[str, str]:
        return {
            "model_id": self.model_id,
            "reference": str(self.reference.resolve()),
            "reference_sha256": self.reference_sha256,
            "reference_text_sha256": text_sha256(self.reference_text),
        }

    @property
    def manifest_reference(self) -> dict[str, str]:
        return {
            "path": str(self.reference.resolve()),
            "sha256": self.reference_sha256,
            "text": self.reference_text,
            "text_sha256": text_sha256(self.reference_text),
        }


class QwenSynthesizer:
    """One lazily imported model and clone prompt kept resident for the batch."""

    def __init__(self, model_id: str, reference: Path, reference_text: str):
        import torch
        from qwen_tts import Qwen3TTSModel

        self._torch = torch
        self._model = Qwen3TTSModel.from_pretrained(
            model_id,
            device_map="cuda:0",
            dtype=torch.bfloat16,
            attn_implementation="sdpa",
        )
        self._prompt = self._model.create_voice_clone_prompt(
            ref_audio=str(reference),
            ref_text=reference_text,
            x_vector_only_mode=False,
        )

    def synthesize(
        self, text: str, destination: str | Path, *, batch_size: int | None = None
    ) -> None:
        import soundfile

        if batch_size not in {None, 1}:
            raise VoiceError("Qwen fallback batch size must be one")
        generation_text: str | list[str] = [text] if batch_size == 1 else text
        generation_language: str | list[str] = (
            ["Russian"] if batch_size == 1 else "Russian"
        )
        wavs, sample_rate = self._model.generate_voice_clone(
            text=generation_text,
            language=generation_language,
            voice_clone_prompt=self._prompt,
            non_streaming_mode=True,
            max_new_tokens=4096,
        )
        if not isinstance(wavs, list) or len(wavs) != 1:
            raise VoiceError("Qwen3-TTS must return exactly one waveform per segment")
        soundfile.write(
            str(destination),
            wavs[0],
            sample_rate,
            subtype="PCM_16",
            format="WAV",
        )

    def close(self) -> None:
        self._prompt = None
        self._model = None
        gc.collect()
        if self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()


def _clear_cuda_cache() -> None:
    import torch

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _is_cuda_oom(error: Exception) -> bool:
    name = type(error).__name__.lower()
    message = str(error).lower()
    return "outofmemory" in name or "out of memory" in message and "cuda" in message


def _translation_segments(job: JobRecord) -> tuple[Path, list[VoiceSegment]]:
    stage = job.stages.get("translation")
    if not isinstance(stage, StageRecord) or stage.status != "completed":
        raise VoiceError("completed translation receipt is required")
    output = stage.outputs.get("translation")
    if not output:
        raise VoiceError("translation receipt is missing translation output")
    path = Path(output)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VoiceError(f"cannot read translation: {error}") from error
    if (
        not isinstance(raw, dict)
        or set(raw) != {"schema_version", "segments"}
        or raw.get("schema_version") != 1
        or not isinstance(raw.get("segments"), list)
    ):
        raise VoiceError("translation schema mismatch")
    expected = {"id", "start", "end", "text_ru"}
    for index, row in enumerate(raw["segments"], 1):
        if not isinstance(row, dict) or set(row) != expected:
            raise VoiceError(f"translation segment {index} schema mismatch")
    return path, voice_segments(raw["segments"])


def _manifest_matches_context(value: dict[str, Any], context: VoiceContext) -> bool:
    return (
        value.get("schema_version") == 1
        and value.get("model_id") == context.model_id
        and value.get("reference") == context.manifest_reference
        and isinstance(value.get("segments"), list)
    )


def _base_manifest(
    prior: dict[str, Any],
    context: VoiceContext,
    reusable_ids: set[int],
) -> dict[str, Any]:
    retained: list[dict[str, Any]] = []
    if _manifest_matches_context(prior, context):
        retained = [
            dict(entry)
            for entry in prior["segments"]
            if isinstance(entry, dict)
            and entry.get("id") in reusable_ids
            and entry.get("status") == "completed"
        ]
    return {
        "schema_version": 1,
        "model_id": context.model_id,
        "reference": context.manifest_reference,
        "segments": retained,
    }


def _upsert_entry(
    manifest: dict[str, Any],
    entry: dict[str, Any],
    ordered_ids: list[int],
) -> None:
    by_id = {
        item["id"]: item
        for item in manifest["segments"]
        if isinstance(item, dict) and isinstance(item.get("id"), int)
    }
    by_id[entry["id"]] = entry
    manifest["segments"] = [by_id[identifier] for identifier in ordered_ids if identifier in by_id]


def _completed_entry(
    segment: VoiceSegment, clip: Path, relative_path: str
) -> dict[str, Any]:
    probe = validate_clip(clip, target_duration=segment.target_duration)
    return {
        "id": segment.id,
        "text": segment.text,
        "text_sha256": text_sha256(segment.text),
        "path": relative_path,
        "duration": probe.duration,
        "sha256": probe.sha256,
        "status": "completed",
        "fit": probe.fit,
    }


def _failed_entry(
    segment: VoiceSegment, relative_path: str, error: Exception
) -> dict[str, Any]:
    return {
        "id": segment.id,
        "text": segment.text,
        "text_sha256": text_sha256(segment.text),
        "path": relative_path,
        "duration": None,
        "sha256": None,
        "status": "failed",
        "fit": None,
        "error": {"type": type(error).__name__, "message": str(error)},
    }


def _stage_failed(
    job: JobRecord,
    inputs: dict[str, str],
    manifest_path: Path | None,
    error: Exception,
) -> None:
    outputs = (
        {"voice": str(manifest_path)}
        if manifest_path is not None and manifest_path.is_file()
        else {}
    )
    job.stages["voice"] = StageRecord.failed(
        adapter=ADAPTER,
        inputs=inputs,
        outputs=outputs,
        error={"type": type(error).__name__, "message": str(error)},
    )


def _synthesize_atomic(
    synthesizer: Synthesizer,
    segment: VoiceSegment,
    clip: Path,
    *,
    clear_cuda_cache: CacheCleanup,
) -> None:
    clip.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=clip.parent, prefix=f".{clip.stem}.", suffix=".wav"
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        try:
            synthesizer.synthesize(segment.text, temporary)
        except Exception as error:
            if not _is_cuda_oom(error):
                raise
            clear_cuda_cache()
            if temporary.exists():
                temporary.unlink()
            try:
                synthesizer.synthesize(segment.text, temporary, batch_size=1)
            except Exception as retry_error:
                if _is_cuda_oom(retry_error):
                    clear_cuda_cache()
                raise
        validate_clip(temporary, target_duration=segment.target_duration)
        os.replace(temporary, clip)
    finally:
        if temporary.exists():
            temporary.unlink()


def process_voice_job(
    synthesizer: Synthesizer,
    job: JobRecord,
    *,
    model_id: str,
    reference: str | Path,
    reference_sha256: str,
    reference_text: str,
    clear_cuda_cache: CacheCleanup = _clear_cuda_cache,
) -> dict[str, Any]:
    """Synthesize one translated job and persist every segment before continuing."""

    translation_path, segments = _translation_segments(job)
    context = VoiceContext(
        model_id=model_id,
        reference=Path(reference),
        reference_sha256=reference_sha256,
        reference_text=reference_text,
    )
    inputs = {
        **context.inputs,
        "translation_sha256": sha256_file(translation_path),
    }
    voice_dir = translation_path.parent / "voice"
    clip_dir = voice_dir / "clips"
    manifest_path = voice_dir / "manifest.json"
    prior = load_voice_manifest(manifest_path)
    if not _manifest_matches_context(prior, context):
        prior = {}
    plan = plan_voice_segments(segments, clip_dir, prior)
    reusable_ids = {segment.id for segment in plan.reusable}
    manifest = _base_manifest(prior, context, reusable_ids)
    ordered_ids = [segment.id for segment in segments]
    current_stage = job.stages.get("voice")
    stage_reusable = isinstance(current_stage, StageRecord) and current_stage.is_reusable(
        inputs, adapter=ADAPTER
    )
    if not plan.pending and stage_reusable:
        return manifest

    job.stages["voice"] = StageRecord.running(
        adapter=ADAPTER,
        inputs=inputs,
        outputs={"voice": str(manifest_path)},
    )
    for segment in plan.pending:
        clip = clip_dir / f"{segment.id:04d}.wav"
        relative_path = f"clips/{clip.name}"
        try:
            _synthesize_atomic(
                synthesizer,
                segment,
                clip,
                clear_cuda_cache=clear_cuda_cache,
            )
            _upsert_entry(
                manifest,
                _completed_entry(segment, clip, relative_path),
                ordered_ids,
            )
            atomic_write_json(manifest_path, manifest)
        except Exception as error:
            _upsert_entry(
                manifest,
                _failed_entry(segment, relative_path, error),
                ordered_ids,
            )
            atomic_write_json(manifest_path, manifest)
            _stage_failed(job, inputs, manifest_path, error)
            raise

    atomic_write_json(manifest_path, manifest)
    job.stages["voice"] = StageRecord.completed(
        adapter=ADAPTER,
        inputs=inputs,
        outputs={"voice": str(manifest_path)},
    )
    return manifest


def _load_batch(path: Path) -> BatchManifest:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VoiceError(f"cannot read batch manifest: {error}") from error
    try:
        return BatchManifest.from_dict(value)
    except (KeyError, TypeError, ValueError) as error:
        raise VoiceError(f"invalid batch manifest: {error}") from error


def _voice_manifest_path(job: JobRecord) -> Path | None:
    translation = job.stages.get("translation")
    if not isinstance(translation, StageRecord):
        return None
    output = translation.outputs.get("translation")
    return None if not output else Path(output).parent / "voice" / "manifest.json"


def _job_requires_synthesis(job: JobRecord, context: VoiceContext) -> bool:
    """Finalize clip-complete recovery state without requiring a CUDA model."""

    translation_path, segments = _translation_segments(job)
    inputs = {
        **context.inputs,
        "translation_sha256": sha256_file(translation_path),
    }
    manifest_path = translation_path.parent / "voice" / "manifest.json"
    clip_dir = manifest_path.parent / "clips"
    prior = load_voice_manifest(manifest_path)
    if not _manifest_matches_context(prior, context):
        return True
    plan = plan_voice_segments(segments, clip_dir, prior)
    if plan.pending:
        return True
    stage = job.stages.get("voice")
    if isinstance(stage, StageRecord) and stage.is_reusable(inputs, adapter=ADAPTER):
        return False
    manifest = _base_manifest(
        prior,
        context,
        {segment.id for segment in plan.reusable},
    )
    atomic_write_json(manifest_path, manifest)
    job.stages["voice"] = StageRecord.completed(
        adapter=ADAPTER,
        inputs=inputs,
        outputs={"voice": str(manifest_path)},
    )
    return False


def run_voice_batch(
    batch_manifest: str | Path,
    *,
    reference: str | Path,
    reference_text: str,
    model_id: str = MODEL_ID,
    synthesizer_factory: SynthesizerFactory = QwenSynthesizer,
    clear_cuda_cache: CacheCleanup = _clear_cuda_cache,
    enforce_authorized_reference: bool = True,
    project_root: str | Path | None = None,
) -> list[dict[str, str]]:
    """Load one synthesizer and clone prompt, then resume every translated job."""

    batch_path = Path(batch_manifest)
    batch = _load_batch(batch_path)
    if enforce_authorized_reference:
        resolved_reference = validate_authorized_reference(
            reference,
            reference_text,
            project_root=project_root,
        )
    else:
        resolved_reference = Path(reference).resolve()
        validate_clip(resolved_reference, target_duration=9.05)
    reference_hash = sha256_file(resolved_reference)
    context = VoiceContext(
        model_id=model_id,
        reference=resolved_reference,
        reference_sha256=reference_hash,
        reference_text=reference_text,
    )
    failures: list[dict[str, str]] = []
    pending_jobs: list[JobRecord] = []
    for job in batch.jobs:
        try:
            if _job_requires_synthesis(job, context):
                pending_jobs.append(job)
        except Exception as error:
            _stage_failed(
                job,
                context.inputs,
                _voice_manifest_path(job),
                error,
            )
            failures.append(
                {
                    "job_id": job.id,
                    "type": type(error).__name__,
                    "message": str(error),
                }
            )
        finally:
            atomic_write_json(batch_path, batch.to_dict())
    if not pending_jobs:
        return failures

    synthesizer: Synthesizer | None = None
    try:
        try:
            synthesizer = synthesizer_factory(
                model_id, resolved_reference, reference_text
            )
        except Exception as error:
            for job in pending_jobs:
                _stage_failed(
                    job,
                    context.inputs,
                    _voice_manifest_path(job),
                    error,
                )
                failures.append(
                    {
                        "job_id": job.id,
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                )
            atomic_write_json(batch_path, batch.to_dict())
            return failures

        for job in pending_jobs:
            try:
                process_voice_job(
                    synthesizer,
                    job,
                    model_id=model_id,
                    reference=resolved_reference,
                    reference_sha256=reference_hash,
                    reference_text=reference_text,
                    clear_cuda_cache=clear_cuda_cache,
                )
            except Exception as error:
                failures.append(
                    {
                        "job_id": job.id,
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                )
            finally:
                atomic_write_json(batch_path, batch.to_dict())
    finally:
        if synthesizer is not None:
            synthesizer.close()
    return failures


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resume Qwen3-TTS Russian voice clips for a localization batch."
    )
    parser.add_argument("--batch-manifest", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--model-id", default=MODEL_ID)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    failures = run_voice_batch(
        args.batch_manifest,
        reference=args.reference,
        reference_text=args.reference_text,
        model_id=args.model_id,
    )
    print(json.dumps({"failures": failures}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
