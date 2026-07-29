"""Pure stem validation and reuse checks for two-stem source separation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable
import wave

from .contracts import JobRecord, StageRecord, sha256_file


MODEL_FILENAME = "MDX23C-8KFFT-InstVoc_HQ.ckpt"
ADAPTER = f"audio-separator[gpu]@0.44.5/{MODEL_FILENAME}"
DURATION_TOLERANCE_SECONDS = 0.1
_SHA256 = re.compile(r"[0-9a-f]{64}")


class SeparationError(ValueError):
    """A separator input, output, or receipt violates the two-stem contract."""


@dataclass(frozen=True)
class StemProbe:
    """Independently decoded facts about a retained WAV stem."""

    duration: float
    sha256: str


@dataclass(frozen=True)
class SeparatorOutputs:
    """The unambiguous vocals/instrumental pair returned by audio-separator."""

    vocals: Path
    instrumental: Path


def separation_inputs(job: JobRecord, model_sha256: str) -> dict[str, str]:
    """Bind a stage receipt to the current source bytes and exact separator model."""

    if _SHA256.fullmatch(model_sha256) is None:
        raise SeparationError("model SHA-256 must be 64 lowercase hexadecimal characters")
    return {
        "source_sha256": sha256_file(job.source),
        "model_filename": MODEL_FILENAME,
        "model_sha256": model_sha256,
    }


def _validate_stem(
    path: str | Path,
    source_duration: float,
    *,
    label: str,
) -> StemProbe:
    stem = Path(path)
    if not stem.is_file() or stem.stat().st_size <= 0:
        raise SeparationError(f"missing {label}: {stem}")
    if (
        isinstance(source_duration, bool)
        or not isinstance(source_duration, (int, float))
        or not math.isfinite(source_duration)
        or source_duration <= 0
    ):
        raise SeparationError("source duration must be a positive finite number")
    try:
        with wave.open(str(stem), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frames = source.getnframes()
    except (EOFError, OSError, wave.Error) as error:
        raise SeparationError(f"invalid {label} WAV: {stem}") from error
    if channels <= 0 or sample_width <= 0 or sample_rate <= 0 or frames <= 0:
        raise SeparationError(f"invalid {label} WAV: {stem}")
    duration = frames / sample_rate
    if abs(duration - float(source_duration)) > DURATION_TOLERANCE_SECONDS + 1e-9:
        raise SeparationError(
            f"{label} duration {duration:.6f}s does not span "
            f"source duration {float(source_duration):.6f}s"
        )
    return StemProbe(duration=duration, sha256=sha256_file(stem))


def validate_instrumental(
    path: str | Path, source_duration: float
) -> StemProbe:
    """Require a nonempty WAV instrumental spanning the source duration."""

    return _validate_stem(path, source_duration, label="instrumental")


def validate_vocals(path: str | Path, source_duration: float) -> StemProbe:
    """Require the retained QA vocals WAV to span the source duration."""

    return _validate_stem(path, source_duration, label="vocals")


def _candidate_kind(name: str) -> str | None:
    normalized = name.casefold().replace("-", "_")
    if (
        "(instrumental)" in normalized
        or "(no vocals)" in normalized
        or "(no_vocals)" in normalized
        or "no_vocals" in normalized
    ):
        return "instrumental"
    if "(vocals)" in normalized:
        return "vocals"
    return None


def map_separator_outputs(
    output_files: Iterable[str | Path],
    *,
    base_dir: str | Path | None = None,
) -> SeparatorOutputs:
    """Map audio-separator names by stem label, never by return-list ordering."""

    root = None if base_dir is None else Path(base_dir)
    candidates: dict[str, list[Path]] = {"vocals": [], "instrumental": []}
    try:
        values = list(output_files)
    except TypeError as error:
        raise SeparationError("separator outputs must be an iterable of paths") from error
    for raw in values:
        if not isinstance(raw, (str, Path)):
            raise SeparationError("separator output paths must be strings or paths")
        path = Path(raw)
        if root is not None and not path.is_absolute():
            path = root / path
        kind = _candidate_kind(path.name)
        if kind is not None:
            candidates[kind].append(path)
    for kind in ("vocals", "instrumental"):
        if not candidates[kind]:
            raise SeparationError(f"missing {kind} separator output")
        if len(candidates[kind]) != 1:
            raise SeparationError(f"ambiguous {kind} separator outputs")
    return SeparatorOutputs(
        vocals=candidates["vocals"][0],
        instrumental=candidates["instrumental"][0],
    )


def load_separation_receipt(path: str | Path) -> dict[str, Any]:
    """Load only the exact schema emitted by this adapter."""

    target = Path(path)
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SeparationError(f"cannot read separation receipt: {error}") from error
    expected = {
        "schema_version",
        "adapter",
        "source_sha256",
        "source_duration",
        "model_filename",
        "model_sha256",
        "stems",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise SeparationError("separation receipt schema mismatch")
    if value.get("schema_version") != 1 or value.get("adapter") != ADAPTER:
        raise SeparationError("separation receipt adapter mismatch")
    stems = value.get("stems")
    if not isinstance(stems, dict) or set(stems) != {"vocals", "instrumental"}:
        raise SeparationError("separation receipt stem schema mismatch")
    stem_fields = {"path", "duration", "sha256"}
    if any(not isinstance(row, dict) or set(row) != stem_fields for row in stems.values()):
        raise SeparationError("separation receipt stem schema mismatch")
    return value


def separation_is_reusable(job: JobRecord, *, model_sha256: str) -> bool:
    """Reuse only exact input, output-path, duration, and content fingerprints."""

    try:
        inputs = separation_inputs(job, model_sha256)
    except (OSError, SeparationError):
        return False
    stage = job.stages.get("separation")
    if not isinstance(stage, StageRecord) or not stage.is_reusable(
        inputs, adapter=ADAPTER
    ):
        return False
    if set(stage.outputs) != {"vocals", "instrumental", "separation"}:
        return False
    try:
        receipt_path = Path(stage.outputs["separation"])
        receipt = load_separation_receipt(receipt_path)
        if (
            receipt["source_sha256"] != inputs["source_sha256"]
            or receipt["model_filename"] != MODEL_FILENAME
            or receipt["model_sha256"] != model_sha256
        ):
            return False
        source_duration = receipt["source_duration"]
        if (
            isinstance(source_duration, bool)
            or not isinstance(source_duration, (int, float))
            or not math.isfinite(source_duration)
            or source_duration <= 0
        ):
            return False
        for key, validator in (
            ("vocals", validate_vocals),
            ("instrumental", validate_instrumental),
        ):
            declared = receipt["stems"][key]
            output_path = Path(stage.outputs[key])
            if declared["path"] != output_path.name:
                return False
            if (receipt_path.parent / declared["path"]).resolve() != output_path.resolve():
                return False
            probe = validator(output_path, float(source_duration))
            declared_duration = declared["duration"]
            if (
                isinstance(declared_duration, bool)
                or not isinstance(declared_duration, (int, float))
                or abs(float(declared_duration) - probe.duration) > 1e-9
                or declared["sha256"] != probe.sha256
            ):
                return False
    except (KeyError, OSError, SeparationError, TypeError, ValueError):
        return False
    return True
