#!/usr/bin/env python
import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

try:
    import audioop
except ImportError:  # pragma: no cover
    audioop = None


def run_text(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout)
    return proc.stdout


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def media_duration(path: Path) -> float:
    out = run_text([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]).strip()
    return float(out)


def extract_audio(video: Path, out: Path) -> None:
    subprocess.run([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "44100",
        str(out),
    ], check=True)


def mono_chunk(data: bytes, sample_width: int, channels: int) -> bytes:
    if channels == 1:
        return data
    if audioop is None:
        raise RuntimeError("audioop is required for multi-channel RMS checks")
    return audioop.tomono(data, sample_width, 0.5, 0.5)


def rms_delta_ratio(voice: Path, mixed: Path) -> dict:
    if audioop is None:
        return {"skipped": "audioop unavailable"}
    frames = 44100
    delta_sq = 0.0
    mixed_sq = 0.0
    sample_count = 0
    with wave.open(str(voice), "rb") as vf, wave.open(str(mixed), "rb") as mf:
        if vf.getframerate() != mf.getframerate() or vf.getsampwidth() != mf.getsampwidth():
            raise RuntimeError("voice and mixed audio must share sample rate and sample width")
        sample_width = vf.getsampwidth()
        while True:
            v = vf.readframes(frames)
            m = mf.readframes(frames)
            if not v or not m:
                break
            v_mono = mono_chunk(v, sample_width, vf.getnchannels())
            m_mono = mono_chunk(m, sample_width, mf.getnchannels())
            frame_count = min(len(v_mono), len(m_mono)) // sample_width
            if frame_count <= 0:
                break
            v_mono = v_mono[: frame_count * sample_width]
            m_mono = m_mono[: frame_count * sample_width]
            delta = audioop.add(m_mono, audioop.mul(v_mono, sample_width, -1.0), sample_width)
            delta_rms = audioop.rms(delta, sample_width)
            mixed_rms = audioop.rms(m_mono, sample_width)
            delta_sq += (delta_rms ** 2) * frame_count
            mixed_sq += (mixed_rms ** 2) * frame_count
            sample_count += frame_count
    if sample_count == 0 or mixed_sq <= 0:
        raise RuntimeError("no audio samples found")
    delta_rms = math.sqrt(delta_sq / sample_count)
    mixed_rms = math.sqrt(mixed_sq / sample_count)
    return {
        "delta_rms": round(delta_rms, 3),
        "mixed_rms": round(mixed_rms, 3),
        "delta_to_mixed": round(delta_rms / mixed_rms, 4),
    }


def silence_events(audio: Path, duration: float, threshold: str, min_duration: float) -> list[dict]:
    out = run_text([
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(audio),
        "-af",
        f"silencedetect=n={threshold}:d={min_duration}",
        "-f",
        "null",
        "-",
    ])
    starts: list[float] = []
    events: list[dict] = []
    for line in out.splitlines():
        start = re.search(r"silence_start:\s*([0-9.]+)", line)
        if start:
            starts.append(float(start.group(1)))
            continue
        end = re.search(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)", line)
        if end:
            s = starts.pop(0) if starts else None
            e = float(end.group(1))
            d = float(end.group(2))
            if s is not None and s < 1.0:
                continue
            if e > duration - 2.0:
                continue
            events.append({"start": s, "end": e, "duration": d})
    return events


def remotion_checks(path: Path, mixed_duration: float, tolerance: float) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"informationGapNarrationSeconds\s*=\s*([0-9.]+)", text)
    if not m:
        raise RuntimeError("informationGapNarrationSeconds not found")
    declared = float(m.group(1))
    return {
        "declared_seconds": declared,
        "duration_delta": round(abs(declared - mixed_duration), 4),
        "uses_scaled_opening_time": "baseSeconds = seconds / sceneScale" in text,
        "passes": abs(declared - mixed_duration) <= tolerance and "baseSeconds = seconds / sceneScale" in text,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", required=True)
    parser.add_argument("--mixed", required=True)
    parser.add_argument("--remotion", required=True)
    parser.add_argument("--video")
    parser.add_argument("--duration-tolerance", type=float, default=0.35)
    parser.add_argument("--min-music-ratio", type=float, default=0.08)
    parser.add_argument("--silence-threshold", default="-45dB")
    parser.add_argument("--max-hard-silence", type=float, default=0.35)
    args = parser.parse_args()

    voice = Path(args.voice).resolve()
    mixed = Path(args.mixed).resolve()
    remotion = Path(args.remotion).resolve()
    if not voice.exists():
        raise SystemExit(f"missing voice: {voice}")
    if not mixed.exists():
        raise SystemExit(f"missing mixed audio: {mixed}")
    if not remotion.exists():
        raise SystemExit(f"missing remotion source: {remotion}")

    mixed_duration = wav_duration(mixed)
    report = {
        "voice_duration": round(wav_duration(voice), 3),
        "mixed_duration": round(mixed_duration, 3),
        "music_delta": rms_delta_ratio(voice, mixed),
        "remotion": remotion_checks(remotion, mixed_duration, args.duration_tolerance),
        "mixed_hard_silences": silence_events(mixed, mixed_duration, args.silence_threshold, args.max_hard_silence),
    }

    if args.video:
        video = Path(args.video).resolve()
        with tempfile.TemporaryDirectory() as tmp:
            extracted = Path(tmp) / "video_audio.wav"
            extract_audio(video, extracted)
            video_duration = media_duration(video)
            report["video_duration"] = round(video_duration, 3)
            report["video_hard_silences"] = silence_events(extracted, video_duration, args.silence_threshold, args.max_hard_silence)

    failures = []
    if report["music_delta"].get("delta_to_mixed", 0) < args.min_music_ratio:
        failures.append(f"music delta too low: {report['music_delta']}")
    if report["mixed_hard_silences"]:
        failures.append(f"hard silences in mixed audio: {report['mixed_hard_silences'][:5]}")
    if not report["remotion"]["passes"]:
        failures.append(f"remotion timing check failed: {report['remotion']}")
    if report.get("video_hard_silences"):
        failures.append(f"hard silences in rendered video: {report['video_hard_silences'][:5]}")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        print("\nFAIL:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("\nOK: information-gap audio/timing audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
