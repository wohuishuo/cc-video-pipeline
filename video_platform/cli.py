from __future__ import annotations

import argparse
import json
import shutil
import sys
import hashlib
from dataclasses import asdict
from pathlib import Path

from .download import DownloadRequest, PlatformDownloader, YtDlpDownloader
from .f2_download import F2Downloader
from .models import Platform
from .receipts import write_receipt
from .process import ProcessRunner
from .upload import UploadLedger, UploadRequest, build_upload_adapters


def _json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _print(payload: object, json_output: bool) -> None:
    if json_output:
        print(_json_text(payload))
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
    upload = subparsers.add_parser("upload")
    upload.add_argument("platform", choices=[item.value for item in Platform])
    upload.add_argument("video", type=Path)
    upload.add_argument("--metadata", type=Path, required=True)
    upload.add_argument("--account", required=True)
    upload.add_argument("--execute", action="store_true", help="Run the upstream uploader; without this flag only prepares the command")
    upload.add_argument("--public", action="store_true", help="Allow public visibility where supported; default is private/draft")
    upload.add_argument("--json", action="store_true")
    login = subparsers.add_parser("login")
    login.add_argument("platform", choices=[item.value for item in Platform])
    login.add_argument("--account", required=True)
    login.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return _doctor(args.json)
    if args.command == "capabilities":
        return _capabilities(args.json)
    project_root = Path(__file__).resolve().parents[1]
    if args.command == "login":
        adapter = build_upload_adapters(project_root)[Platform(args.platform)]
        command = adapter.login_command(args.account)
        result = ProcessRunner().run(command, cwd=adapter.checkout)
        _print({"platform": args.platform, "status": "ok" if result.exit_code == 0 else "failed", "exit_code": result.exit_code}, args.json)
        return result.exit_code
    if args.command == "upload":
        try:
            platform = Platform(args.platform)
            request = UploadRequest(platform, args.video, args.metadata, args.account, draft=not args.public)
            adapter = build_upload_adapters(project_root)[platform]
            prepared = adapter.prepare(request)
            payload = {
                "platform": platform.value,
                "status": prepared.status,
                "command": prepared.command,
                "profile_dir": str(prepared.profile_dir),
                "executed": False,
            }
            if args.execute:
                digest = hashlib.sha256(args.video.resolve().read_bytes() + args.metadata.resolve().read_bytes()).hexdigest()
                UploadLedger(project_root / "receipts" / "uploads.jsonl").reserve(digest, platform)
                result = ProcessRunner().run(prepared.command, cwd=adapter.checkout)
                payload.update({"status": "ok" if result.exit_code == 0 else "failed", "executed": True, "exit_code": result.exit_code})
                _print(payload, args.json)
                return result.exit_code
            _print(payload, args.json)
            return 0
        except (ValueError, OSError) as error:
            _print({"error": str(error)}, args.json)
            return 2
    try:
        request = DownloadRequest(Platform(args.platform), args.url, args.output_dir, args.max_height, args.cookies)
        f2_executable = project_root / ".tools" / "f2" / ".venv" / "Scripts" / "f2.exe"
        fallback = F2Downloader(f2_executable) if f2_executable.is_file() else None
        receipt = PlatformDownloader(YtDlpDownloader(), fallback).download(request)
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
