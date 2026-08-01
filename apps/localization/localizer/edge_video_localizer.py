"""Strictly serial Edge-TTS Russian dubbing and hard-subtitle publisher."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Callable, Iterable
import wave

from .audio import AudioMixSpec, build_mix
from .contracts import BatchManifest, JobRecord, atomic_write_json, sha256_file
from .render import probe_video, render_localized_video
from .subtitles import write_ass


DEFAULT_VOICE = "ru-RU-DmitryNeural"
ADAPTER = "edge-tts@7"
DEFAULT_RETRIES = 6
DEFAULT_TIMEOUT_SECONDS = 45
DEFAULT_SEGMENT_DELAY_SECONDS = 2.0


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_serial_jobs(
    job_ids: Iterable[str], process: Callable[[str], None]
) -> list[dict[str, str]]:
    """Finish each job before entering the next and isolate failures."""
    failures: list[dict[str, str]] = []
    for job_id in job_ids:
        try:
            process(job_id)
        except Exception as error:
            failures.append({"job_id": job_id, "error": str(error)})
            print(f"[FAILED] {job_id}: {type(error).__name__}: {error}", flush=True)
    return failures


def _valid_wav(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb") as source:
            return source.getnframes() > 0 and source.getframerate() > 0
    except (OSError, wave.Error, EOFError):
        return False


def retry_delays(
    attempts: int, *, initial_seconds: int = 5, maximum_seconds: int = 60
) -> list[int]:
    """Return bounded exponential delays between attempts."""
    return [min(initial_seconds * (2**index), maximum_seconds) for index in range(attempts - 1)]


async def _edge_save(
    text: str, voice: str, destination: Path, timeout_seconds: int
) -> None:
    import edge_tts

    await asyncio.wait_for(
        edge_tts.Communicate(text=text, voice=voice).save(str(destination)),
        timeout=timeout_seconds,
    )


def _synthesize_clip(
    text: str,
    voice: str,
    destination: Path,
    retries: int = DEFAULT_RETRIES,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial_mp3 = destination.with_name(f".{destination.stem}.partial.mp3")
    partial_wav = destination.with_name(f".{destination.stem}.partial.wav")
    delays = retry_delays(retries)
    for attempt in range(1, retries + 1):
        try:
            for partial in (partial_mp3, partial_wav):
                if partial.exists():
                    partial.unlink()
            asyncio.run(_edge_save(text, voice, partial_mp3, timeout_seconds))
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(partial_mp3), "-ar", "24000", "-ac", "1",
                    "-c:a", "pcm_s16le", str(partial_wav),
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if not _valid_wav(partial_wav):
                raise RuntimeError("Edge-TTS produced an invalid WAV")
            os.replace(partial_wav, destination)
            return
        except Exception as error:
            if attempt == retries:
                raise
            delay = delays[attempt - 1]
            print(
                f"    Edge attempt {attempt}/{retries} failed: "
                f"{type(error).__name__}; retrying in {delay}s",
                flush=True,
            )
            time.sleep(delay)
        finally:
            for partial in (partial_mp3, partial_wav):
                if partial.exists():
                    partial.unlink()


def _voice_clips(
    job_dir: Path,
    segments: list[dict],
    voice: str,
    segment_delay_seconds: float = DEFAULT_SEGMENT_DELAY_SECONDS,
) -> Path:
    voice_dir = job_dir / "edge-voice"
    clip_dir = voice_dir / "clips"
    manifest_path = voice_dir / "manifest.json"
    prior = _load_json(manifest_path) if manifest_path.is_file() else {"segments": []}
    reusable = {int(row["id"]): row for row in prior.get("segments", [])}
    completed: list[dict] = []

    for index, row in enumerate(segments, 1):
        identifier = int(row["id"])
        text = str(row["text_ru"]).strip()
        clip = clip_dir / f"{identifier:04d}.wav"
        text_hash = __import__("hashlib").sha256(text.encode("utf-8")).hexdigest()
        old = reusable.get(identifier)
        if not (
            isinstance(old, dict)
            and old.get("text_sha256") == text_hash
            and old.get("voice") == voice
            and _valid_wav(clip)
        ):
            print(f"  [Edge {index}/{len(segments)}] {identifier}", flush=True)
            _synthesize_clip(text, voice, clip)
        completed.append(
            {
                "id": identifier,
                "text_sha256": text_hash,
                "voice": voice,
                "path": str(clip),
                "sha256": sha256_file(clip),
            }
        )
        atomic_write_json(
            manifest_path,
            {"schema_version": 1, "adapter": ADAPTER, "voice": voice, "segments": completed},
        )
        if index < len(segments) and segment_delay_seconds > 0:
            time.sleep(segment_delay_seconds)
    return manifest_path


def _background_bed(job: JobRecord, job_dir: Path) -> Path:
    separation = job.stages.get("separation")
    if separation is not None:
        candidate = Path(separation.outputs.get("instrumental", ""))
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    audio_dir = job_dir / "edge-audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    bed = audio_dir / "no_vocals.wav"
    if bed.is_file() and bed.stat().st_size > 0:
        return bed
    partial = audio_dir / ".no_vocals.partial.wav"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", job.source,
            "-vn", "-af", "pan=stereo|c0=0.7*c0-0.7*c1|c1=0.7*c1-0.7*c0",
            "-ar", "48000", "-c:a", "pcm_s16le", str(partial),
        ],
        check=True,
        capture_output=True,
    )
    os.replace(partial, bed)
    return bed


def _process_job(job: JobRecord, *, voice: str, output_root: Path) -> None:
    translation_path = Path(job.stages["translation"].outputs["translation"])
    job_dir = translation_path.parent
    segments = _load_json(translation_path)["segments"]
    translation_hash = sha256_file(translation_path)
    receipt_path = job_dir / "edge-receipt.json"
    output = output_root / f"{Path(job.source).stem}.edge.ru.mp4"
    if receipt_path.is_file() and output.is_file():
        receipt = _load_json(receipt_path)
        if (
            receipt.get("translation_sha256") == translation_hash
            and receipt.get("voice") == voice
            and receipt.get("output_sha256") == sha256_file(output)
        ):
            print(f"[SKIP] {job.id} already complete", flush=True)
            return

    print(f"[VOICE] {job.id}", flush=True)
    voice_manifest = _voice_clips(job_dir, segments, voice)
    bed = _background_bed(job, job_dir)
    duration = float(probe_video(job.source)["format"]["duration"])
    print(f"[MIX] {job.id}", flush=True)
    mix = build_mix(
        AudioMixSpec(
            segments,
            voice_manifest.parent / "clips",
            bed,
            duration,
            job_dir / "edge-audio",
            max_compression_ratio=100.0,
        )
    )
    if not mix.published:
        raise RuntimeError(f"Edge voice exceeds timeline: {mix.overflow_ids}")
    media = probe_video(job.source)
    video = next(stream for stream in media["streams"] if stream["codec_type"] == "video")
    ass = write_ass(
        segments,
        job_dir / "subtitles.edge.ru.ass",
        play_res=(int(video["width"]), int(video["height"])),
    )
    print(f"[RENDER] {job.id}", flush=True)
    render_localized_video(job.source, mix.mix_path, ass, output)
    atomic_write_json(
        receipt_path,
        {
            "schema_version": 1,
            "adapter": ADAPTER,
            "voice": voice,
            "translation_sha256": translation_hash,
            "voice_manifest_sha256": sha256_file(voice_manifest),
            "mix_sha256": sha256_file(mix.mix_path),
            "subtitle_sha256": sha256_file(ass),
            "output": str(output),
            "output_sha256": sha256_file(output),
        },
    )
    print(f"[DONE] {output.name}", flush=True)


def run_edge_batch(
    batch_manifest: Path,
    *,
    voice: str,
    output_root: Path,
    job_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    batch = BatchManifest.from_dict(_load_json(batch_manifest))
    output_root.mkdir(parents=True, exist_ok=True)
    jobs = {job.id: job for job in batch.jobs}
    selected = [job.id for job in batch.jobs if job_ids is None or job.id in job_ids]
    if job_ids is not None and set(selected) != job_ids:
        raise ValueError(f"unknown job ids: {sorted(job_ids - set(selected))}")
    failures = run_serial_jobs(
        selected,
        lambda job_id: _process_job(jobs[job_id], voice=voice, output_root=output_root),
    )
    atomic_write_json(output_root / "edge-failures.json", {"failures": failures})
    return failures


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serial Edge-TTS Russian video localizer.")
    parser.add_argument("--batch-manifest", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--job-id", action="append", dest="job_ids")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    failures = run_edge_batch(
        args.batch_manifest,
        voice=args.voice,
        output_root=args.output_root,
        job_ids=set(args.job_ids) if args.job_ids else None,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
