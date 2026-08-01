"""Pure planning and validation for resumable Russian voice synthesis."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence
import wave

from .contracts import sha256_file


ADAPTER = "qwen3-tts-base@1"
SAMPLE_RATE = 24_000
MAX_COMPRESSION_RATIO = 1.35
AUTHORIZED_REFERENCE_RELATIVE = Path(
    "projects/game-design-course/voice/reference-ru.wav"
)
AUTHORIZED_REFERENCE_SHA256 = (
    "3ff903a4148870387395e3f7e41168b0a75fe026649e38d81ff11198cdf8bc67"
)
AUTHORIZED_REFERENCE_TEXT = (
    "Сейчас я покажу, как превратить игровую идею в модель, которую можно "
    "рассчитать, объяснить команде и проверить на данных."
)

FitClass = Literal["fit", "compress", "overflow"]


class VoiceError(ValueError):
    """Voice input or an output clip violates the synthesis contract."""


@dataclass(frozen=True)
class VoiceSegment:
    """Russian text attached to Task 3's immutable identity and timing."""

    id: int
    start: float
    end: float
    text: str

    @property
    def target_duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class ClipProbe:
    """Validated facts used to bind a manifest entry to a WAV."""

    duration: float
    sha256: str
    fit: FitClass


@dataclass(frozen=True)
class VoicePlan:
    """Verified reuse and the smallest remaining synthesis set."""

    reusable: list[VoiceSegment]
    pending: list[VoiceSegment]


def text_sha256(text: str) -> str:
    """Fingerprint the exact UTF-8 text sent to the synthesizer."""

    if not isinstance(text, str) or not text.strip():
        raise VoiceError("voice text must be non-empty")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify_duration(clip_duration: float, target_duration: float) -> FitClass:
    """Classify a clip without silently allowing compression above 35 percent."""

    if (
        isinstance(clip_duration, bool)
        or isinstance(target_duration, bool)
        or not math.isfinite(clip_duration)
        or not math.isfinite(target_duration)
        or clip_duration <= 0
        or target_duration <= 0
    ):
        raise VoiceError("clip and target durations must be positive finite numbers")
    if clip_duration <= target_duration:
        return "fit"
    if clip_duration <= target_duration * MAX_COMPRESSION_RATIO:
        return "compress"
    return "overflow"


def validate_clip(path: str | Path, *, target_duration: float) -> ClipProbe:
    """Require a nonempty 24 kHz mono WAV and return independently probed facts."""

    clip = Path(path)
    if not clip.is_file() or clip.stat().st_size <= 0:
        raise VoiceError(f"missing or empty voice clip: {clip}")
    try:
        with wave.open(str(clip), "rb") as source:
            channels = source.getnchannels()
            sample_rate = source.getframerate()
            frames = source.getnframes()
    except (EOFError, OSError, wave.Error) as error:
        raise VoiceError(f"invalid voice WAV: {clip}") from error
    if channels != 1:
        raise VoiceError(f"voice clip must be mono: {clip}")
    if sample_rate != SAMPLE_RATE:
        raise VoiceError(f"voice clip must be 24000 Hz: {clip}")
    if frames <= 0:
        raise VoiceError(f"voice clip contains no audio frames: {clip}")
    duration = frames / sample_rate
    return ClipProbe(
        duration=duration,
        sha256=sha256_file(clip),
        fit=classify_duration(duration, target_duration),
    )


def _normalize_segment(value: Any, index: int) -> VoiceSegment:
    if isinstance(value, Mapping):
        identifier = value.get("id")
        start = value.get("start")
        end = value.get("end")
        text = value.get("text")
        if text is None:
            text = value.get("text_ru")
    else:
        identifier = getattr(value, "id", None)
        start = getattr(value, "start", None)
        end = getattr(value, "end", None)
        text = getattr(value, "text", None)
    if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0:
        raise VoiceError(f"voice segment {index} requires a positive integer id")
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, (int, float))
        or not isinstance(end, (int, float))
        or not math.isfinite(start)
        or not math.isfinite(end)
        or end <= start
    ):
        raise VoiceError(f"voice segment {identifier} requires positive finite timing")
    if not isinstance(text, str) or not text.strip():
        raise VoiceError(f"voice segment {identifier} requires non-empty Russian text")
    return VoiceSegment(identifier, float(start), float(end), text)


def voice_segments(values: Sequence[Any]) -> list[VoiceSegment]:
    """Normalize Task 3 rows while preserving its authoritative ordering."""

    segments = [_normalize_segment(value, index) for index, value in enumerate(values, 1)]
    if not segments:
        raise VoiceError("translation contains no voice segments")
    identifiers = [segment.id for segment in segments]
    duplicates = sorted(
        {identifier for identifier in identifiers if identifiers.count(identifier) > 1}
    )
    if duplicates:
        raise VoiceError("duplicate voice segment ids: " + ", ".join(map(str, duplicates)))
    previous_end = -math.inf
    for segment in segments:
        if segment.start < previous_end:
            raise VoiceError("voice segments must be ordered without overlap")
        previous_end = segment.end
    return segments


def _manifest_entries(prior_manifest: Mapping[str, Any] | None) -> dict[int, Mapping[str, Any]]:
    if not isinstance(prior_manifest, Mapping):
        return {}
    raw_entries = prior_manifest.get("segments", [])
    if not isinstance(raw_entries, list):
        return {}
    entries: dict[int, Mapping[str, Any]] = {}
    for entry in raw_entries:
        if not isinstance(entry, Mapping):
            continue
        identifier = entry.get("id")
        if isinstance(identifier, bool) or not isinstance(identifier, int):
            continue
        if identifier in entries:
            entries.pop(identifier, None)
            continue
        entries[identifier] = entry
    return entries


def _entry_reuses(
    segment: VoiceSegment,
    clip_dir: Path,
    entry: Mapping[str, Any] | None,
) -> bool:
    if entry is None or entry.get("status") != "completed":
        return False
    filename = f"{segment.id:04d}.wav"
    canonical_path = f"clips/{filename}" if clip_dir.name == "clips" else filename
    declared_path = entry.get("path")
    if declared_path != canonical_path:
        return False
    if entry.get("text") != segment.text:
        return False
    if entry.get("text_sha256") != text_sha256(segment.text):
        return False
    try:
        probe = validate_clip(clip_dir / filename, target_duration=segment.target_duration)
    except VoiceError:
        return False
    declared_duration = entry.get("duration")
    if (
        isinstance(declared_duration, bool)
        or not isinstance(declared_duration, (int, float))
        or abs(float(declared_duration) - probe.duration) > 1 / SAMPLE_RATE
    ):
        return False
    return entry.get("sha256") == probe.sha256 and entry.get("fit") == probe.fit


def plan_voice_segments(
    segments: Sequence[Any],
    clip_dir: str | Path,
    prior_manifest: Mapping[str, Any] | None,
) -> VoicePlan:
    """Reuse only clips whose text, content hash, format, and duration still agree."""

    normalized = voice_segments(segments)
    entries = _manifest_entries(prior_manifest)
    reusable: list[VoiceSegment] = []
    pending: list[VoiceSegment] = []
    clips = Path(clip_dir)
    for segment in normalized:
        target = reusable if _entry_reuses(segment, clips, entries.get(segment.id)) else pending
        target.append(segment)
    return VoicePlan(reusable=reusable, pending=pending)


def load_voice_manifest(path: str | Path) -> dict[str, Any]:
    """Return a usable schema-v1 manifest or an empty recovery state."""

    target = Path(path)
    if not target.is_file():
        return {}
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return {}
    return value


def validate_authorized_reference(
    reference: str | Path,
    reference_text: str,
    *,
    project_root: str | Path | None = None,
) -> Path:
    """Lock production synthesis to the authorized reference path and transcript."""

    root = Path.cwd() if project_root is None else Path(project_root)
    expected = (root / AUTHORIZED_REFERENCE_RELATIVE).resolve()
    actual = Path(reference).resolve()
    if actual != expected:
        raise VoiceError(f"authorized reference path is required: {expected}")
    if reference_text != AUTHORIZED_REFERENCE_TEXT:
        raise VoiceError("exact authorized reference text is required")
    probe = validate_clip(actual, target_duration=9.05)
    if abs(probe.duration - 9.05) > 1 / SAMPLE_RATE:
        raise VoiceError("authorized reference WAV must be exactly 9.05 seconds")
    if probe.sha256 != AUTHORIZED_REFERENCE_SHA256:
        raise VoiceError("authorized reference SHA-256 does not match")
    return actual
