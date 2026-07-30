"""One-command resumable Chinese-video to Russian-video batch pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from . import asr
from .audio import AudioMixSpec, build_mix
from .contracts import BatchManifest, JobRecord, Segment, StageRecord, atomic_write_json, sha256_file
from .inventory import discover_jobs
from .fast_translation import ADAPTER as FAST_TRANSLATION_ADAPTER, translate_job_fast
from .render import probe_video, render_localized_video
from .subtitles import write_ass
from .translation import (
    ADAPTER as TRANSLATION_ADAPTER,
    MODEL as TRANSLATION_MODEL,
    TranslationSegment,
    rewrite_overflow_segments,
    translate_job,
)
from .voice import AUTHORIZED_REFERENCE_RELATIVE, AUTHORIZED_REFERENCE_TEXT


def _log(message: str) -> None:
    print(message, flush=True)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_inventory(source_root: Path, batch_path: Path) -> BatchManifest:
    fresh = discover_jobs(source_root / "video-urls.txt", source_root / "videos")
    if not batch_path.is_file():
        return fresh
    try:
        prior = BatchManifest.from_dict(_load_json(batch_path))
    except Exception:
        return fresh
    prior_by_id = {job.id: job for job in prior.jobs}
    jobs: list[JobRecord] = []
    for job in fresh.jobs:
        old = prior_by_id.get(job.id)
        stages = dict(old.stages) if old and old.source_sha256 == job.source_sha256 else {}
        jobs.append(JobRecord(job.id, job.source, job.source_sha256, stages))
    return BatchManifest(fresh.manifest, fresh.expected_ids, tuple(jobs))


def _save(batch_path: Path, batch: BatchManifest) -> None:
    atomic_write_json(batch_path, batch.to_dict())


def _transcribe(batch: BatchManifest, output_root: Path, batch_path: Path) -> None:
    pending = []
    for job in batch.jobs:
        inputs = {"source_sha256": sha256_file(job.source)}
        stage = job.stages.get("transcription")
        recovered_json = output_root / "jobs" / job.id / "transcript.zh.json"
        recovered_srt = output_root / "jobs" / job.id / "transcript.zh.srt"
        if (
            (not isinstance(stage, StageRecord) or stage.status != "completed")
            and recovered_json.is_file() and recovered_json.stat().st_size > 0
            and recovered_srt.is_file() and recovered_srt.stat().st_size > 0
        ):
            job.stages["transcription"] = StageRecord.completed(
                asr.ADAPTER, inputs, {"transcript": str(recovered_json), "srt": str(recovered_srt)}
            )
            _save(batch_path, batch)
            stage = job.stages["transcription"]
        if not isinstance(stage, StageRecord) or not stage.is_reusable(inputs, adapter=asr.ADAPTER):
            pending.append(job)
    if not pending:
        _log("[ASR] 已全部完成，跳过")
        return
    _log(f"[ASR] 开始识别 {len(pending)} 条视频（GPU 模型只加载一次）")
    from faster_whisper import WhisperModel

    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    try:
        for index, job in enumerate(pending, 1):
            _log(f"[ASR {index}/{len(pending)}] {job.id}")
            try:
                asr.transcribe_job(model, job, output_root=output_root)
            finally:
                _save(batch_path, batch)
    finally:
        close = getattr(model, "close", None)
        if callable(close):
            close()


def _translate(batch: BatchManifest, output_root: Path, batch_path: Path) -> None:
    for index, job in enumerate(batch.jobs, 1):
        transcript = job.stages.get("transcription")
        if not isinstance(transcript, StageRecord) or transcript.status != "completed":
            raise RuntimeError(f"missing transcript for {job.id}")
        transcript_path = Path(transcript.outputs["transcript"])
        inputs = {"source_sha256": job.source_sha256, "transcript_sha256": sha256_file(transcript_path)}
        stage = job.stages.get("translation")
        if isinstance(stage, StageRecord) and stage.is_reusable(inputs, adapter=FAST_TRANSLATION_ADAPTER):
            continue
        _log(f"[翻译 {index}/{len(batch.jobs)}] {job.id}")
        translate_job_fast(job, output_root=output_root)
        _save(batch_path, batch)


def _run_worker(executable: Path, module: str, arguments: list[str], app_root: Path) -> None:
    if not executable.is_file():
        raise RuntimeError(f"missing worker runtime: {executable}")
    environment = dict(__import__("os").environ)
    environment["PYTHONPATH"] = str(app_root)
    command = [str(executable), "-m", module, *arguments]
    subprocess.run(command, check=True, env=environment, cwd=executable.parents[3])


def _prepare_fast_beds(batch: BatchManifest, batch_path: Path) -> None:
    """Quickly suppress center-panned narration without an AI separation model."""
    for index, job in enumerate(batch.jobs, 1):
        job_dir = Path(job.stages["translation"].outputs["translation"]).parent
        audio_dir = job_dir / "audio"
        bed = audio_dir / "no_vocals.wav"
        stage = job.stages.get("separation")
        inputs = {"source_sha256": job.source_sha256, "method": "ffmpeg-center-cancel@1"}
        if isinstance(stage, StageRecord) and stage.is_reusable(inputs, adapter="ffmpeg-center-cancel@1"):
            continue
        audio_dir.mkdir(parents=True, exist_ok=True)
        partial = audio_dir / ".no_vocals.partial.wav"
        _log(f"[快速去人声 {index}/{len(batch.jobs)}] {job.id}")
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", job.source,
            "-vn", "-af", "pan=stereo|c0=0.7*c0-0.7*c1|c1=0.7*c1-0.7*c0",
            "-ar", "48000", "-c:a", "pcm_s16le", str(partial),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True)
            partial.replace(bed)
            job.stages["separation"] = StageRecord.completed(
                "ffmpeg-center-cancel@1", inputs, {"instrumental": str(bed)}
            )
            _save(batch_path, batch)
        finally:
            if partial.exists():
                partial.unlink()


def _rewrite_job(job: JobRecord, overflow_ids: tuple[int, ...]) -> None:
    transcript_path = Path(job.stages["transcription"].outputs["transcript"])
    translation_path = Path(job.stages["translation"].outputs["translation"])
    source = [Segment.from_dict(row) for row in _load_json(transcript_path)["segments"]]
    current = [
        TranslationSegment(int(row["id"]), float(row["start"]), float(row["end"]), row["text_ru"])
        for row in _load_json(translation_path)["segments"]
    ]
    rewritten = rewrite_overflow_segments(source, overflow_ids, current)
    atomic_write_json(
        translation_path,
        {"schema_version": 1, "segments": [segment.to_dict() for segment in rewritten]},
    )


def _mix_all(batch: BatchManifest) -> dict[str, tuple[int, ...]]:
    overflow: dict[str, tuple[int, ...]] = {}
    for index, job in enumerate(batch.jobs, 1):
        translation_path = Path(job.stages["translation"].outputs["translation"])
        segments = _load_json(translation_path)["segments"]
        voice_manifest = Path(job.stages["voice"].outputs["voice"])
        instrumental = Path(job.stages["separation"].outputs["instrumental"])
        duration = float(probe_video(job.source)["format"]["duration"])
        _log(f"[混音 {index}/{len(batch.jobs)}] {job.id}")
        result = build_mix(
            AudioMixSpec(segments, voice_manifest.parent / "clips", instrumental, duration, translation_path.parent / "audio")
        )
        if result.overflow_ids:
            overflow[job.id] = result.overflow_ids
        else:
            job.stages["mix"] = StageRecord.completed(
                "ffmpeg-mix@1",
                {"translation_sha256": sha256_file(translation_path), "voice_sha256": sha256_file(voice_manifest), "instrumental_sha256": sha256_file(instrumental)},
                {"narration": str(result.narration_path), "mix": str(result.mix_path), "receipt": str(result.receipt_path)},
            )
    return overflow


def _render_all(batch: BatchManifest, final_root: Path, batch_path: Path) -> None:
    for index, job in enumerate(batch.jobs, 1):
        translation_path = Path(job.stages["translation"].outputs["translation"])
        job_dir = translation_path.parent
        media = probe_video(job.source)
        video = next(stream for stream in media["streams"] if stream["codec_type"] == "video")
        ass = write_ass(
            _load_json(translation_path)["segments"],
            job_dir / "subtitles.ru.ass",
            play_res=(int(video["width"]), int(video["height"])),
        )
        output = final_root / f"{Path(job.source).stem}.ru.mp4"
        _log(f"[渲染 {index}/{len(batch.jobs)}] {output.name}")
        render_localized_video(job.source, job.stages["mix"].outputs["mix"], ass, output)
        job.stages["render"] = StageRecord.completed(
            "ffmpeg-russian-render@1",
            {"source_sha256": job.source_sha256, "mix_sha256": sha256_file(job.stages["mix"].outputs["mix"]), "subtitle_sha256": sha256_file(ass)},
            {"video": str(output)},
        )
        _save(batch_path, batch)


def run(args: argparse.Namespace) -> None:
    source_root = args.source_root.resolve()
    runtime_root = args.runtime_root.resolve()
    app_root = Path(__file__).resolve().parents[1]
    output_root = source_root / "russian"
    final_root = output_root / "final"
    batch_path = output_root / "batch-manifest.json"
    output_root.mkdir(parents=True, exist_ok=True)
    final_root.mkdir(parents=True, exist_ok=True)
    batch = _merge_inventory(source_root, batch_path)
    _save(batch_path, batch)
    _log(f"已载入 {len(batch.jobs)} 条视频，状态文件：{batch_path}")

    _transcribe(batch, output_root, batch_path)
    _translate(batch, output_root, batch_path)

    if not args.skip_separation:
        _log("[分轨] 开始整批分离中文人声与背景音乐")
        _run_worker(
            runtime_root / "tools" / "audio-separator-env" / "Scripts" / "python.exe",
            "localizer.separator_worker",
            ["--batch-manifest", str(batch_path), "--model-dir", str(runtime_root / "tools" / "audio-separator-models")],
            app_root,
        )
    else:
        _prepare_fast_beds(batch, batch_path)

    _log("[配音] 开始整批生成俄语克隆声音")
    _run_worker(
        runtime_root / "tools" / "qwen3tts-env" / "Scripts" / "python.exe",
        "localizer.qwen_voice_worker",
        ["--batch-manifest", str(batch_path), "--reference", str(runtime_root / AUTHORIZED_REFERENCE_RELATIVE), "--reference-text", AUTHORIZED_REFERENCE_TEXT],
        app_root,
    )
    batch = BatchManifest.from_dict(_load_json(batch_path))

    overflow = _mix_all(batch)
    if overflow:
        _log(f"[重写] {sum(map(len, overflow.values()))} 个俄语段落过长，自动压缩文案后重新配音")
        for job in batch.jobs:
            if job.id in overflow:
                _rewrite_job(job, overflow[job.id])
        _save(batch_path, batch)
        _run_worker(
            runtime_root / "tools" / "qwen3tts-env" / "Scripts" / "python.exe",
            "localizer.qwen_voice_worker",
            ["--batch-manifest", str(batch_path), "--reference", str(runtime_root / AUTHORIZED_REFERENCE_RELATIVE), "--reference-text", AUTHORIZED_REFERENCE_TEXT],
            app_root,
        )
        batch = BatchManifest.from_dict(_load_json(batch_path))
        overflow = _mix_all(batch)
        if overflow:
            raise RuntimeError(f"Russian text still too long after rewrite: {overflow}")
    _save(batch_path, batch)

    if not args.skip_render:
        _render_all(batch, final_root, batch_path)
    _log(f"完成。俄语视频输出：{final_root}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch clone-dub Chinese videos into Russian.")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--skip-separation", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        run(_parser().parse_args(argv))
        return 0
    except KeyboardInterrupt:
        _log("已中断；再次运行同一命令会从断点继续。")
        return 130
    except Exception as error:
        _log(f"失败：{type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
