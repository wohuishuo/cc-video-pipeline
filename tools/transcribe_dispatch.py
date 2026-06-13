#!/usr/bin/env python
"""统一转录入口：按语言自动路由。

中文 → FunASR（Paraformer，高准确率 + 标点）
其他语言 → faster-whisper（多语言 + 抗噪音）
auto 检测 → 中/英/日用 FunASR SenseVoiceSmall，其余用 faster-whisper

用法:
    python transcribe_dispatch.py <音/视频文件> [--lang auto] [--outdir DIR]

输出(与 transcribe.py 同 schema):
    *.srt  — 字幕
    *.json — 段级 + 词级时间戳
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

# 支持 FunASR 的语言 → 用 SenseVoiceSmall
FUNASR_LANGS = {"zh", "en", "ja", "ko", "yue", "auto"}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="统一转录入口——智能路由 FunASR / faster-whisper"
    )
    ap.add_argument("input")
    ap.add_argument("--lang", default="auto")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--model", default=None, help="覆盖：FunASR 中文模型 或 faster-whisper 模型")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"[err] 文件不存在: {src}", file=sys.stderr)
        return 1

    outdir = Path(args.outdir) if args.outdir else src.parent
    outdir.mkdir(parents=True, exist_ok=True)
    tools_dir = Path(__file__).resolve().parent
    venv_python = tools_dir / ".venv" / "Scripts" / "python.exe"

    # 决定路由
    if args.lang in FUNASR_LANGS or args.lang == "auto":
        # 优先尝试 FunASR（中文场景质量更好）
        script = tools_dir / "transcribe_funasr.py"
        if script.exists():
            print(f"[*] 路由: FunASR (lang={args.lang})", file=sys.stderr)
            cmd = [str(venv_python), str(script), str(src), "--lang", args.lang]
            if args.model:
                cmd += ["--model", args.model]
            cmd += ["--outdir", str(outdir)]
            result = subprocess.run(cmd)
            if result.returncode == 0:
                return 0
            print("[warn] FunASR 失败，回退 faster-whisper…", file=sys.stderr)

    # 回退：faster-whisper（多语言/抗噪音/词级时间戳）
    script = tools_dir / "transcribe.py"
    print(f"[*] 路由: faster-whisper (lang={args.lang})", file=sys.stderr)
    cmd = [str(venv_python), str(script), str(src), "--lang", args.lang]
    if args.model:
        cmd += ["--model", args.model]
    cmd += ["--outdir", str(outdir)]
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
