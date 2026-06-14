#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fetch_voice.py — 通用下载工具: 把参考音频/模型拉到 voices/ 目录

支持来源:
  - GitHub release/branch  (gh_xxx)
  - HuggingFace hub        (hf_org/name)
  - ModelScope hub         (ms_org/name)
  - 直接 URL               (http/https)

用法:
  python fetch_voice.py gh HarutoLiang/Genshin-Nahida-Japanese-Voice --out voices/nahida_jp/
  python fetch_voice.py hf erythrocyte/sovits-nahida --out voices/sovits_models/
  python fetch_voice.py url https://example.com/nahida.wav --out voices/nahida_jp/ref.wav
"""
import argparse
import sys
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def gh_download(repo: str, out_dir: Path) -> int:
    """抓 GitHub 仓库全部 (含 LFS wav) → out_dir"""
    out_dir.mkdir(parents=True, exist_ok=True)
    # 用 git clone 比 zip 稳: LFS wav 在 zip 里下载不完整
    target = out_dir / "repo"
    if target.exists():
        print(f"[skip] 已存在: {target}")
        return 0
    cmd = ["git", "clone", "--depth=1", f"https://github.com/{repo}.git", str(target)]
    print(f"[run] {' '.join(cmd)}")
    return subprocess.call(cmd)


def hf_download(repo: str, out_dir: Path) -> int:
    """抓 HuggingFace repo → out_dir (用 huggingface_hub Python API)"""
    from huggingface_hub import snapshot_download
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run] snapshot_download({repo}, local_dir={out_dir})")
    snapshot_download(repo_id=repo, local_dir=str(out_dir))
    return 0


def ms_download(model_id: str, out_dir: Path) -> int:
    """抓 ModelScope 模型 → out_dir"""
    from modelscope import snapshot_download
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run] snapshot_download({model_id}, local_dir={out_dir})")
    snapshot_download(model_id, local_dir=str(out_dir))
    return 0


def url_download(url: str, out_path: Path) -> int:
    """单文件 URL → out_path (用 curl 重定向 + 进度条)"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 1024:
        print(f"[skip] 已存在: {out_path} ({out_path.stat().st_size} bytes)")
        return 0
    cmd = ["curl", "-L", "-f", "-o", str(out_path), url]
    print(f"[run] curl {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    p = argparse.ArgumentParser(description="抓音频/模型到 voices/ 目录",
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    p.add_argument("source", choices=["gh", "hf", "ms", "url"],
                   help="gh=GitHub / hf=HuggingFace / ms=ModelScope / url=直接URL")
    p.add_argument("ref", help="repo id 或 URL")
    p.add_argument("--out", required=True, help="目标路径 (目录或文件)")
    p.add_argument("--file", help="hf/ms: 只下某个文件")
    args = p.parse_args()

    out = Path(args.out)

    if args.source == "gh":
        return gh_download(args.ref, out)
    elif args.source == "hf":
        if args.file:
            from huggingface_hub import hf_hub_download
            print(f"[run] hf_hub_download({args.ref}, {args.file})")
            hf_hub_download(repo_id=args.ref, filename=args.file, local_dir=str(out))
            return 0
        return hf_download(args.ref, out)
    elif args.source == "ms":
        if args.file:
            from modelscope import snapshot_download
            snapshot_download(args.ref, allow_file_pattern=[args.file], local_dir=str(out))
            return 0
        return ms_download(args.ref, out)
    elif args.source == "url":
        # 从 URL 推断文件名
        u = urlparse(args.ref)
        name = Path(u.path).name or "downloaded"
        if out.is_dir() or args.out.endswith("/"):
            return url_download(args.ref, out / name)
        return url_download(args.ref, out)

    return 1


if __name__ == "__main__":
    sys.exit(main())
