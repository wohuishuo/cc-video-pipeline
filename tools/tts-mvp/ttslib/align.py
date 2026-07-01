#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SRT / 逐行稿子 解析 + 时间轴对齐 + ffmpeg 合成。引擎无关，dub.py 与 server 共用。

对齐策略（借鉴 jianshuo/wjs-dubbing-video）：按时间轴重建音轨——间隙补静音，
每段 TTS 超长用 atempo 加速、偏短且空档 >0.5s 轻拉伸、否则补静音；concat 后 mux。
"""
import re
import subprocess
from pathlib import Path

MIN_ATEMPO = 0.82
STRETCH_GAP = 0.5


def ts_to_sec(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.replace(".", ",").split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(text: str):
    """-> [(idx, start, end, spoken)]"""
    out = []
    for b in re.split(r"\n\s*\n", text.strip()):
        lines = b.strip().splitlines()
        if len(lines) < 3:
            continue
        m0 = re.match(r"\d+", lines[0])
        m = re.match(r"(\S+)\s+-->\s+(\S+)", lines[1])
        if not (m0 and m):
            continue
        spoken = " ".join(lines[2:]).replace("——", "，").replace("—", "，")
        out.append((int(m0.group()), ts_to_sec(m.group(1)), ts_to_sec(m.group(2)), spoken))
    return out


def parse_lines(text: str):
    """逐行稿子 -> [(idx, None, None, spoken)]（时间留空，按合成时长顺序排）。"""
    rows = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return [(i + 1, None, None, ln) for i, ln in enumerate(rows)]


def _run_ff(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def probe_dur(p) -> float:
    r = _run_ff(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(p)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def build_filtergraph(seg_meta, total_dur):
    """seg_meta: [(idx, start, end, wav_path, real_dur)] -> (inputs, filter_str, n_audio).
    n_audio = 音频输入个数（视频在它之后作为最后一路 input）。"""
    pipeline, prev = [], 0.0
    for idx, start, end, wav, dur in seg_meta:
        if start > prev + 0.01:
            pipeline.append(("silence", start - prev))
        pipeline.append(("tts", idx, end - start, wav, dur))
        prev = end
    if total_dur > prev + 0.01:
        pipeline.append(("silence", total_dur - prev))

    inputs, filt, labels, ti = [], [], [], 0
    for i, seg in enumerate(pipeline):
        if seg[0] == "silence":
            filt.append(f"anullsrc=r=44100:cl=mono:d={seg[1]:.3f}[s{i}]")
            labels.append(f"[s{i}]")
            continue
        _, idx, target, wav, tts_dur = seg
        inputs.extend(["-i", str(wav)])
        chain = f"[{ti}:a]"
        ti += 1
        if target <= 0:
            target = tts_dur
        if tts_dur > target:
            r = tts_dur / target
            steps = []
            while r > 2.0:
                steps.append(2.0); r /= 2.0
            steps.append(r)
            chain += "".join(f"atempo={s:.4f}," for s in steps)
            chain += f"apad=whole_dur={target:.3f},atrim=duration={target:.3f}[a{i}]"
        elif target - tts_dur > STRETCH_GAP and tts_dur > 0:
            stretch = max(MIN_ATEMPO, tts_dur / target)
            chain += (f"atempo={stretch:.4f},apad=whole_dur={target:.3f},"
                      f"atrim=duration={target:.3f}[a{i}]")
        else:
            chain += f"apad=whole_dur={target:.3f},atrim=duration={target:.3f}[a{i}]"
        filt.append(chain)
        labels.append(f"[a{i}]")

    filt.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1,aresample=44100[outa]")
    return inputs, ";".join(filt), ti


def mux(seg_meta, total_dur, out_path, video_path=None):
    """合成对齐音轨；给了 video_path 就 mux 回视频（画面 stream-copy）。"""
    inputs, filt, ti = build_filtergraph(seg_meta, total_dur)
    if video_path:
        cmd = ["ffmpeg", "-y", *inputs, "-i", str(video_path),
               "-filter_complex", filt, "-map", f"{ti}:v", "-map", "[outa]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_path)]
    else:
        cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filt,
               "-map", "[outa]", str(out_path)]
    r = _run_ff(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 合成失败:\n{r.stderr[-2000:]}")
    return Path(out_path)
