from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from .download import DownloadRequest, YtDlpDownloader
from .models import Platform
from .receipts import write_receipt


def _print(payload: object, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if isinstance(payload, dict):
            for key, value in payload.items():
                print(f"{key}: {value}")
        else:
            print(payload)


def _doctor(json_output: bool) -> int:
    dependencies = {
        "python": sys.executable,
        "yt-dlp": shutil.which("yt-dlp"),
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "git": shutil.which("git"),
    }
    ok = all(dependencies.values())
    _print({"ok": ok, "dependencies": dependencies}, json_output)
    return 0 if ok else 1


def _capabilities(json_output: bool) -> int:
    downloader_ready = bool(shutil.which("yt-dlp") and shutil.which("ffprobe"))
    checkout = Path(__file__).resolve().parents[1] / ".tools" / "social-auto-upload"
    platforms = {
        platform.value: {
            "download": "adapter-ready" if downloader_ready else "dependency-missing",
            "upload": "dependency-installed" if checkout.is_dir() else "not-installed",
        }
        for platform in Platform
    }
    _print({"platforms": platforms}, json_output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-platform")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("doctor", "capabilities"):
        child = subparsers.add_parser(command)
        child.add_argument("--json", action="store_true")
    download = subparsers.add_parser("download")
    download.add_argument("platform", choices=[item.value for item in Platform])
    download.add_argument("url")
    download.add_argument("--output-dir", type=Path, default=Path("downloads"))
    download.add_argument("--max-height", type=int, default=1080)
    download.add_argument("--cookies", type=Path)
    download.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return _doctor(args.json)
    if args.command == "capabilities":
        return _capabilities(args.json)
    try:
        request = DownloadRequest(Platform(args.platform), args.url, args.output_dir, args.max_height, args.cookies)
        receipt = YtDlpDownloader().download(request)
        receipt_path = args.output_dir.resolve() / "download-receipt.json"
        write_receipt(receipt, receipt_path)
        payload = asdict(receipt)
        payload["platform"] = receipt.platform.value
        payload["receipt"] = str(receipt_path)
        _print(payload, args.json)
        return 0 if receipt.status == "ok" else 1
    except (ValueError, OSError) as error:
        _print({"error": str(error)}, args.json)
        return 2
