"""Timeline-safe Russian narration assembly and instrumental mixing."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Literal
import wave

from .contracts import atomic_write_json, sha256_file


class AudioMixError(RuntimeError):
    """The localized audio inputs cannot safely produce a final mix."""


Fit = Literal["fit", "compress", "rewrite"]


@dataclass
class AudioMixSpec:
    segments: list[dict[str, Any]]
    clip_dir: Path
    instrumental_path: Path
    source_duration: float
    output_dir: Path
    max_compression_ratio: float = 1.35


@dataclass(frozen=True)
class AudioMixResult:
    narration_path: Path
    mix_path: Path
    receipt_path: Path
    overflow_ids: tuple[int, ...]
    published: bool


def classify_fit(*, tts_seconds: float, slot_seconds: float, max_compression_ratio: float = 1.35) -> Fit:
    if not all(math.isfinite(value) and value > 0 for value in (tts_seconds, slot_seconds)):
        raise AudioMixError("clip and slot durations must be positive finite numbers")
    if tts_seconds <= slot_seconds:
        return "fit"
    if not math.isfinite(max_compression_ratio) or max_compression_ratio < 1:
        raise AudioMixError("max compression ratio must be at least 1")
    if tts_seconds <= slot_seconds * max_compression_ratio:
        return "compress"
    return "rewrite"


def _clip_duration(path: Path) -> float:
    if not path.is_file() or path.stat().st_size <= 0:
        raise AudioMixError(f"missing or empty voice clip: {path}")
    try:
        with wave.open(str(path), "rb") as source:
            if source.getnframes() <= 0 or source.getframerate() <= 0:
                raise AudioMixError(f"invalid voice clip: {path}")
            return source.getnframes() / source.getframerate()
    except (wave.Error, EOFError) as error:
        raise AudioMixError(f"invalid voice clip: {path}") from error


def _validate(spec: AudioMixSpec) -> list[dict[str, Any]]:
    if not math.isfinite(spec.source_duration) or spec.source_duration <= 0:
        raise AudioMixError("source duration must be positive")
    if not spec.instrumental_path.is_file() or spec.instrumental_path.stat().st_size <= 0:
        raise AudioMixError("missing instrumental bed")
    rows: list[dict[str, Any]] = []
    previous_end = 0.0
    for raw in spec.segments:
        try:
            identifier = int(raw["id"])
            start = float(raw["start"])
            end = float(raw["end"])
        except (KeyError, TypeError, ValueError) as error:
            raise AudioMixError("invalid segment") from error
        if not all(math.isfinite(value) for value in (start, end)) or start < 0 or end <= start:
            raise AudioMixError(f"invalid timing for segment {identifier}")
        if start < previous_end:
            raise AudioMixError("segments overlap")
        if end > spec.source_duration + 0.001:
            raise AudioMixError("segment exceeds source duration")
        clip = spec.clip_dir / f"{identifier:04d}.wav"
        duration = _clip_duration(clip)
        slot = end - start
        fit = classify_fit(
            tts_seconds=duration,
            slot_seconds=slot,
            max_compression_ratio=spec.max_compression_ratio,
        )
        rows.append({
            "id": identifier,
            "start": start,
            "end": end,
            "clip": clip,
            "duration": duration,
            "fit": fit,
            "tempo": duration / slot if fit == "compress" else 1.0,
        })
        previous_end = end
    if not rows:
        raise AudioMixError("mix requires at least one segment")
    return rows


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command, check=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except FileNotFoundError as error:
        raise AudioMixError(f"missing media tool: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        raise AudioMixError(f"FFmpeg failed: {detail[-1200:]}") from error


def _atempo_filters(ratio: float) -> list[str]:
    """Split an extreme speed-up into FFmpeg-supported atempo stages."""
    filters: list[str] = []
    remaining = ratio
    while remaining > 100.0:
        filters.append("atempo=100.000000000")
        remaining /= 100.0
    filters.append(f"atempo={remaining:.9f}")
    return filters


def _build_narration(rows: list[dict[str, Any]], duration: float, target: Path) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for row in rows:
        command += ["-i", str(row["clip"])]
    filters = [f"anullsrc=r=48000:cl=stereo,atrim=duration={duration:.6f}[sil]"]
    labels = ["[sil]"]
    for index, row in enumerate(rows):
        slot = row["end"] - row["start"]
        chain = (
            f"[{index}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo"
        )
        if row["fit"] == "compress":
            chain += "," + ",".join(_atempo_filters(row["tempo"]))
        delay = round(row["start"] * 1000)
        chain += f",apad,atrim=duration={slot:.6f},adelay={delay}|{delay}[v{index}]"
        filters.append(chain)
        labels.append(f"[v{index}]")
    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=first:normalize=0,atrim=duration={duration:.6f}[out]"
    )
    command += [
        "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000",
        "-ac", "2", "-c:a", "pcm_s16le", str(target),
    ]
    _run(command)


def _final_mix_filter(duration: float) -> str:
    return (
        f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration:.6f}[bedraw];"
        f"[1:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration:.6f},asplit[sidechain][voiceraw];"
        "[bedraw][sidechain]sidechaincompress=threshold=0.015:ratio=10:attack=15:release=350,volume=0.25[bed];"
        "[voiceraw]volume=2.5[voice];"
        "[bed][voice]amix=inputs=2:duration=first:normalize=0,"
        f"loudnorm=I=-16:TP=-1.5:LRA=9,apad=whole_dur={duration:.6f},"
        f"atrim=duration={duration:.6f}[mix]"
    )


def _build_final_mix(instrumental: Path, narration: Path, duration: float, target: Path) -> None:
    graph = _final_mix_filter(duration)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(instrumental), "-i", str(narration),
        "-filter_complex", graph, "-map", "[mix]", "-ar", "48000", "-ac", "2",
        "-c:a", "pcm_s16le", str(target),
    ])


def _measure_loudness(path: Path) -> dict[str, float]:
    completed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
         "loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if completed.returncode != 0:
        raise AudioMixError("could not measure final loudness")
    matches = re.findall(r"\{\s*\"input_i\".*?\}", completed.stderr, re.DOTALL)
    if not matches:
        raise AudioMixError("FFmpeg did not return loudness JSON")
    payload = json.loads(matches[-1])
    return {
        "integrated_lufs": float(payload["input_i"]),
        "true_peak_dbtp": float(payload["input_tp"]),
        "loudness_range_lu": float(payload["input_lra"]),
    }


def build_mix(spec: AudioMixSpec) -> AudioMixResult:
    """Build atomically published narration and final stereo mix."""

    rows = _validate(spec)
    output_dir = Path(spec.output_dir)
    narration = output_dir / "narration.wav"
    mix = output_dir / "mix.wav"
    receipt = output_dir / "mix.json"
    overflow = tuple(row["id"] for row in rows if row["fit"] == "rewrite")
    if overflow:
        return AudioMixResult(narration, mix, receipt, overflow, False)

    output_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".mix-staging-", dir=output_dir))
    try:
        staged_narration = staging / "narration.wav"
        staged_mix = staging / "mix.wav"
        staged_receipt = staging / "mix.json"
        _build_narration(rows, spec.source_duration, staged_narration)
        _build_final_mix(spec.instrumental_path, staged_narration, spec.source_duration, staged_mix)
        loudness = _measure_loudness(staged_mix)
        data = {
            "schema_version": 1,
            "source_duration": spec.source_duration,
            "segments": [
                {key: row[key] for key in ("id", "start", "end", "duration", "fit", "tempo")}
                for row in rows
            ],
            "loudness": loudness,
            "outputs": {
                "narration": {"path": str(narration), "sha256": sha256_file(staged_narration)},
                "mix": {"path": str(mix), "sha256": sha256_file(staged_mix)},
            },
        }
        atomic_write_json(staged_receipt, data)
        for source, target in (
            (staged_narration, narration), (staged_mix, mix), (staged_receipt, receipt)
        ):
            os.replace(source, target)
        return AudioMixResult(narration, mix, receipt, (), True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
