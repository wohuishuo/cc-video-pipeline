"""Burn Russian ASS captions after replacing the source lower caption band."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any


class RenderError(RuntimeError):
    pass


def _filter_path(path: str | Path) -> str:
    value = Path(path).resolve().as_posix().replace("'", r"\'")
    if len(value) > 2 and value[1] == ":":
        value = value[0] + r"\:" + value[2:]
    return value


def build_video_filter(*, width: int, height: int, ass_path: str | Path) -> str:
    band = max(1, round(140 * height / 720))
    y = height - band
    ass = _filter_path(ass_path)
    return (
        f"[0:v]split[base][region];"
        f"[region]crop={width}:{band}:0:{y},boxblur=12:2[blurred];"
        f"[base][blurred]overlay=0:H-h,"
        f"drawbox=x=0:y={y}:w=iw:h={band}:color=black@0.42:t=fill,"
        f"ass='{ass}'[v]"
    )


def probe_video(path: str | Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return json.loads(completed.stdout)


def _has_nvenc() -> bool:
    completed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return "h264_nvenc" in completed.stdout


def render_localized_video(
    source: str | Path,
    mix: str | Path,
    ass: str | Path,
    output: str | Path,
) -> Path:
    source = Path(source)
    mix = Path(mix)
    output = Path(output)
    if not source.is_file() or not mix.is_file() or not Path(ass).is_file():
        raise RenderError("render input is missing")
    probe = probe_video(source)
    videos = [stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"]
    if len(videos) != 1:
        raise RenderError("source requires exactly one video stream")
    width, height = int(videos[0]["width"]), int(videos[0]["height"])
    graph = build_video_filter(width=width, height=height, ass_path=ass)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(f".{output.stem}.partial.mp4")
    if partial.exists():
        partial.unlink()
    encoder = ["-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr", "-cq", "19", "-b:v", "0"] if _has_nvenc() else ["-c:v", "libx264", "-preset", "medium", "-crf", "19"]
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-i", str(mix), "-filter_complex", graph, "-map", "[v]", "-map", "1:a:0",
        *encoder, "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        str(partial),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        rendered = probe_video(partial)
        if partial.stat().st_size <= 0 or not any(s.get("codec_type") == "video" for s in rendered["streams"]) or not any(s.get("codec_type") == "audio" for s in rendered["streams"]):
            raise RenderError("rendered media validation failed")
        os.replace(partial, output)
        return output
    except (OSError, subprocess.CalledProcessError, KeyError) as error:
        raise RenderError(str(error)) from error
    finally:
        if partial.exists():
            partial.unlink()
