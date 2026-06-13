#!/usr/bin/env python
"""faster-whisper 转录核心。

用法:
    python transcribe.py <音/视频文件> [--model large-v3] [--lang auto] [--outdir DIR]

输出（与输入同名，写到 --outdir，默认输入文件目录）:
    *.srt   — 字幕（烧录/校对用）
    *.json  — 段级 + 词级时间戳（给分析脚本消费）

说明:
    - 无 NVIDIA，默认 CPU + int8，255H 上对 10 分钟视频约几分钟。
    - 想更快可换更小模型（small / medium）。large-v3 质量最好。
"""
import argparse
import json
import sys
from pathlib import Path


def fmt_ts(seconds: float) -> str:
    """秒 -> SRT 时间戳 HH:MM:SS,mmm"""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--lang", default="auto", help="auto / zh / en / ru / ja ...")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--compute", default="int8", help="int8 / int8_float32 / float32")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"[err] 文件不存在: {src}", file=sys.stderr)
        return 1
    outdir = Path(args.outdir) if args.outdir else src.parent
    outdir.mkdir(parents=True, exist_ok=True)
    stem = src.stem

    from faster_whisper import WhisperModel

    print(f"[*] 加载模型 {args.model} (CPU/{args.compute})…", file=sys.stderr)
    model = WhisperModel(args.model, device="cpu", compute_type=args.compute)

    lang = None if args.lang == "auto" else args.lang
    print(f"[*] 转录 {src.name} …", file=sys.stderr)
    segments, info = model.transcribe(
        str(src), language=lang, word_timestamps=True, vad_filter=True
    )

    seg_list = []
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        words = [
            {"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word}
            for w in (seg.words or [])
        ]
        seg_list.append(
            {
                "id": i,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": words,
            }
        )
        srt_lines.append(
            f"{i}\n{fmt_ts(seg.start)} --> {fmt_ts(seg.end)}\n{seg.text.strip()}\n"
        )
        # 实时打印进度
        print(f"  [{fmt_ts(seg.start)}] {seg.text.strip()}", file=sys.stderr)

    (outdir / f"{stem}.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    payload = {
        "source": src.name,
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 2),
        "segments": seg_list,
    }
    (outdir / f"{stem}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[ok] 语言={info.language} 时长={info.duration:.1f}s "
        f"段数={len(seg_list)} -> {outdir/stem}.srt / .json",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
