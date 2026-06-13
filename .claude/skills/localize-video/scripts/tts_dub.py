#!/usr/bin/env python
"""SRT → 时间对齐配音，mux 回原视频。Edge TTS（免费/本地/中俄英日）。

对齐策略（借鉴 jianshuo/wjs-dubbing-video）：
  按 SRT 时间轴重建音轨——字幕间隙填静音，每段 TTS 若超长用 atempo 加速、
  若偏短且空档 >0.5s 做轻微拉伸、否则补静音；concat 后整体 mux 到视频。
  原视频画面 stream-copy 不重编码。

用法:
  python tts_dub.py --video in.mp4 --srt in.ja.srt --lang ja [--voice ...] [--out out.mp4]
  python tts_dub.py --video in.mp4 --srt in.ru.srt --lang ru --gender male

支持语言: zh / en / ru / ja（你的优势语种）。--voice 可覆盖预设。
"""
import argparse
import asyncio
import re
import subprocess
import sys
from pathlib import Path

import edge_tts

# 各语种默认音色（female, male）。多语种音色对中英混排更稳。
VOICE_PRESETS = {
    "zh": ("zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"),
    "en": ("en-US-AvaMultilingualNeural", "en-US-AndrewMultilingualNeural"),
    "ru": ("ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"),
    "ja": ("ja-JP-NanamiNeural", "ja-JP-KeitaNeural"),
}

MIN_ATEMPO = 0.82   # 低于这个拉伸声音会发飘
STRETCH_GAP = 0.5   # 空档 >0.5s 才做慢拉伸


def ts_to_sec(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(text: str):
    blocks = re.split(r"\n\s*\n", text.strip())
    out = []
    for b in blocks:
        lines = b.strip().splitlines()
        if len(lines) < 3:
            continue
        idx = int(re.match(r"\d+", lines[0]).group())
        m = re.match(r"(\S+)\s+-->\s+(\S+)", lines[1])
        start, end = ts_to_sec(m.group(1)), ts_to_sec(m.group(2))
        spoken = " ".join(lines[2:]).replace("——", "，").replace("—", "，")
        out.append((idx, start, end, spoken))
    return out


def probe_dur(p: Path) -> float:
    # Windows 中文系统默认 gbk 解码 ffmpeg 输出会炸，显式 utf-8 + 容错
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(p)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return float(r.stdout.strip())


async def synth_all(segs, voice, rate, pitch, work: Path):
    for idx, start, end, text in segs:
        mp3 = work / f"seg_{idx:04d}.mp3"
        if mp3.exists() and mp3.stat().st_size > 0:
            continue
        if not text.strip():
            # 空台词：写一段极短静音占位（用 ffmpeg 生成）
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i",
                 "anullsrc=r=24000:cl=mono", "-t", "0.1", str(mp3)],
                check=True, stderr=subprocess.DEVNULL,
            )
            continue
        for attempt in range(6):
            try:
                comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
                await comm.save(str(mp3))
                if mp3.exists() and mp3.stat().st_size > 0:
                    break
            except Exception as e:
                print(f"  seg{idx:04d} 尝试{attempt+1}失败: {e}", file=sys.stderr)
                await asyncio.sleep(1.5 * (attempt + 1))
        else:
            sys.exit(f"[err] seg {idx} TTS 生成失败")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--lang", choices=list(VOICE_PRESETS), required=True)
    ap.add_argument("--gender", choices=["female", "male"], default="female")
    ap.add_argument("--voice", default=None, help="覆盖预设音色（Edge TTS 名）")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--pitch", default="+0Hz")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    video, srt = Path(args.video), Path(args.srt)
    if not video.exists():
        sys.exit(f"[err] 视频不存在: {video}")
    if not srt.exists():
        sys.exit(f"[err] SRT 不存在: {srt}")
    voice = args.voice or VOICE_PRESETS[args.lang][0 if args.gender == "female" else 1]
    out = Path(args.out) if args.out else video.with_name(f"{video.stem}_{args.lang}_dub.mp4")
    work = video.parent / f"_dub_{args.lang}"
    work.mkdir(exist_ok=True)

    segs = parse_srt(srt.read_text(encoding="utf-8"))
    video_dur = probe_dur(video)
    print(f"[*] 视频 {video_dur:.1f}s, {len(segs)} 段, 音色={voice}")

    asyncio.run(synth_all(segs, voice, args.rate, args.pitch, work))

    # 按时间轴重建：间隙静音 + TTS段（超长加速/偏短拉伸/补静音）
    pipeline, prev = [], 0.0
    for idx, start, end, text in segs:
        if start > prev + 0.01:
            pipeline.append(("silence", start - prev))
        pipeline.append(("tts", idx, end - start))
        prev = end
    if video_dur > prev + 0.01:
        pipeline.append(("silence", video_dur - prev))

    inputs, filt, labels, tts_i = [], [], [], 0
    for i, seg in enumerate(pipeline):
        if seg[0] == "silence":
            filt.append(f"anullsrc=r=44100:cl=mono:d={seg[1]:.3f}[s{i}]")
            labels.append(f"[s{i}]")
            continue
        _, idx, target = seg
        mp3 = work / f"seg_{idx:04d}.mp3"
        tts_dur = probe_dur(mp3)
        inputs.extend(["-i", str(mp3)])
        chain = f"[{tts_i}:a]"
        tts_i += 1
        if tts_dur > target and target > 0:
            r = tts_dur / target
            steps = []
            while r > 2.0:
                steps.append(2.0); r /= 2.0
            steps.append(r)
            chain += "".join(f"atempo={s:.4f}," for s in steps)
            chain = chain.rstrip(",")
            chain += f",apad=whole_dur={target:.3f},atrim=duration={target:.3f}[a{i}]"
            mode = "加速"
        elif target - tts_dur > STRETCH_GAP and tts_dur > 0:
            stretch = max(MIN_ATEMPO, tts_dur / target)
            chain += f"atempo={stretch:.4f},apad=whole_dur={target:.3f},atrim=duration={target:.3f}[a{i}]"
            mode = f"拉伸×{stretch:.2f}"
        else:
            chain += f"apad=whole_dur={target:.3f},atrim=duration={target:.3f}[a{i}]"
            mode = "补静音"
        filt.append(chain)
        labels.append(f"[a{i}]")
        print(f"  seg{idx:04d}: tts={tts_dur:.2f}s 目标={target:.2f}s {mode}")

    filt.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1,aresample=44100[outa]")
    cmd = ["ffmpeg", "-y", *inputs, "-i", str(video),
           "-filter_complex", ";".join(filt),
           "-map", f"{tts_i}:v", "-map", "[outa]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
           "-shortest", str(out)]
    print("[*] 合成中…")
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-2500:], file=sys.stderr)
        sys.exit("[err] ffmpeg 合成失败")
    print(f"[ok] 配音版 -> {out}  ({probe_dur(out):.1f}s)")


if __name__ == "__main__":
    main()
