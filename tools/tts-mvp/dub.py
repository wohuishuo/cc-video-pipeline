#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
dub.py — 整段配音 / SRT 时间对齐配音 / 视频换音（基于 ttslib，引擎可切换）

把"单句出 wav"补成"整条视频换音"：引擎只加载一次，逐句合成后按时间轴对齐
（间隙补静音 / 超长 atempo 加速 / 偏短轻拉伸），最后 mux 回视频（画面 stream-copy）。

声线来源:
  预设音色  --speaker Vivian/Ono_Anna/Ryan...
  跨语言克隆 --clone --ref xx.wav --ref_text "…"

输入:
  --srt in.ja.srt --lang ja --speaker anna --video in.mp4   # SRT 对齐换音
  --srt in.ru.srt --lang ru --speaker ryan                  # 只出对齐音轨
  --lines script.txt --lang zh --speaker vivian --gap 0.35  # 逐行稿子配音

引擎: --engine qwen (默认) / gpt-sovits(待接入)
依赖: tools/tts-mvp/.venv + PATH 上 ffmpeg/ffprobe
"""
import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from ttslib import get_engine                      # noqa: E402
from ttslib.align import parse_srt, parse_lines, probe_dur, mux  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="整段/SRT 配音 + 视频换音",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--srt")
    src.add_argument("--lines")
    ap.add_argument("--lang", required=True)
    ap.add_argument("--engine", default="qwen")
    ap.add_argument("--speaker", default="Vivian")
    ap.add_argument("--instruct", default="")
    ap.add_argument("--clone", action="store_true")
    ap.add_argument("--ref")
    ap.add_argument("--ref_text")
    ap.add_argument("--ref_lang", default="auto")
    ap.add_argument("--video")
    ap.add_argument("--out")
    ap.add_argument("--gap", type=float, default=0.35)
    ap.add_argument("--device", default="cpu", choices=["cpu", "xpu", "cuda"])
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    timed = bool(args.srt)
    if args.clone and not (args.ref and args.ref_text):
        sys.exit("[err] --clone 需要 --ref 和 --ref_text")

    if args.srt:
        p = Path(args.srt)
        if not p.exists():
            sys.exit(f"[err] SRT 不存在: {p}")
        segs = parse_srt(p.read_text(encoding="utf-8"))
        base_name, base_dir = p.with_suffix("").name, p.parent
    else:
        p = Path(args.lines)
        if not p.exists():
            sys.exit(f"[err] 稿子不存在: {p}")
        segs = parse_lines(p.read_text(encoding="utf-8"))
        base_name, base_dir = p.with_suffix("").name, p.parent
    if not segs:
        sys.exit("[err] 没解析到任何台词")

    if args.video:
        v = Path(args.video)
        if not v.exists():
            sys.exit(f"[err] 视频不存在: {v}")
        base_dir, base_name = v.parent, v.stem

    import soundfile as sf
    eng = get_engine(args.engine, device=args.device)
    print(f"[*] {len(segs)} 段 | 引擎={args.engine} | "
          f"{'克隆' if args.clone else args.speaker} | lang={args.lang}")
    try:
        eng.load()
    except NotImplementedError as e:
        sys.exit(f"[err] {e}")

    ref_lang = None if args.ref_lang == "auto" else args.ref_lang
    work = Path(tempfile.mkdtemp(prefix="dub_", dir=str(base_dir)))

    seg_meta = []
    for n, (idx, start, end, text) in enumerate(segs, 1):
        wav_p = work / f"seg_{idx:04d}.wav"
        if text.strip():
            try:
                if args.clone:
                    wav, sr = eng.synth_clone(text, args.lang, args.ref, args.ref_text, ref_lang)
                else:
                    wav, sr = eng.synth_preset(text, args.lang, args.speaker, args.instruct)
                sf.write(str(wav_p), wav, sr)
            except Exception as e:
                sys.exit(f"[err] seg{idx} 合成失败: {e}")
        else:
            import numpy as np
            sf.write(str(wav_p), np.zeros(2400, dtype="float32"), 24000)
        dur = probe_dur(wav_p)
        seg_meta.append((idx, start, end, wav_p, dur))
        print(f"  [{n}/{len(segs)}] seg{idx:04d} -> {dur:.2f}s  {text[:28]}")

    if not timed:  # 逐行：据实测时长生成顺序时间轴
        t, rebuilt = 0.0, []
        for idx, _, _, wav_p, dur in seg_meta:
            rebuilt.append((idx, t, t + dur, wav_p, dur))
            t += dur + args.gap
        seg_meta, total = rebuilt, t
    else:
        total = max(e for _, _, e, _, _ in seg_meta)
    if args.video:
        total = probe_dur(args.video)

    if args.video:
        out = Path(args.out) if args.out else base_dir / f"{base_name}_{args.lang}_dub.mp4"
    else:
        out = Path(args.out) if args.out else base_dir / f"{base_name}_{args.lang}_dub.wav"

    print("[*] 对齐 + 合成中…")
    try:
        mux(seg_meta, total, out, video_path=args.video)
    except RuntimeError as e:
        sys.exit(f"[err] {e}")

    if not args.keep_temp:
        for _, _, _, wav_p, _ in seg_meta:
            wav_p.unlink(missing_ok=True)
        try:
            work.rmdir()
        except OSError:
            pass
    print(f"[ok] 配音 -> {out}  ({probe_dur(out):.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
