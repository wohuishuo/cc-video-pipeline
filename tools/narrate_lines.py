#!/usr/bin/env python
"""把分句脚本逐句 TTS，拼成整条配音，并输出每句时间轴（给字幕/动画对齐）。

用法:
  python narrate_lines.py --lines lines.json --voice zh-CN-XiaoxiaoNeural \
      --gap 0.35 --rate -4% --out-wav narration.wav --out-timings timings.json

lines.json = ["第一句", "第二句", ...]
timings.json = {"duration":.., "lines":[{"i":0,"text":..,"start":..,"end":..}, ...]}
"""
import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return float(r.stdout.strip())


async def synth(text, voice, rate, out):
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", required=True)
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--gap", type=float, default=0.35)
    ap.add_argument("--out-wav", required=True)
    ap.add_argument("--out-timings", required=True)
    args = ap.parse_args()

    lines = json.loads(Path(args.lines).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        segs, timings, t = [], [], 0.0
        for i, text in enumerate(lines):
            mp3 = td / f"l{i:02d}.mp3"
            asyncio.run(synth(text, args.voice, args.rate, mp3))
            d = dur(mp3)
            timings.append({"i": i, "text": text, "start": round(t, 3), "end": round(t + d, 3)})
            t += d + args.gap
            segs.append(mp3)
        # 拼接：每段后接 gap 静音
        concat_parts, filt, idx = [], [], 0
        inputs = []
        for i, mp3 in enumerate(segs):
            inputs += ["-i", str(mp3)]
            filt.append(f"[{i}:a]aresample=44100[a{i}]")
        # 用 concat + 中间插静音：改用逐段 apad
        # 简单做法：每段后补 gap 静音再 concat
        parts = []
        for i in range(len(segs)):
            parts.append(f"[a{i}]")
            sil = f"anullsrc=r=44100:cl=stereo:d={args.gap}"
            filt.append(f"{sil}[s{i}]")
            parts.append(f"[s{i}]")
        filt.append("".join(parts) + f"concat=n={len(parts)}:v=0:a=1[out]")
        cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filt),
               "-map", "[out]", str(args.out_wav)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            sys.stderr.write(r.stderr[-2000:]); sys.exit("拼接失败")

    total = dur(args.out_wav)
    Path(args.out_timings).write_text(
        json.dumps({"duration": round(total, 3), "voice": args.voice, "lines": timings},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 配音 {total:.1f}s, {len(lines)}句 -> {args.out_wav} / {args.out_timings}", file=sys.stderr)
    for ln in timings:
        print(f"  [{ln['start']:5.1f}-{ln['end']:5.1f}] {ln['text'][:30]}", file=sys.stderr)


if __name__ == "__main__":
    main()
