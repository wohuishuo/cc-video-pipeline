"""Command-line boundary for private YouTube publication."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

from .operation import YouTubePublishOperation


ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Private-only YouTube Data API uploader")
    commands = parser.add_subparsers(dest="operation", required=True)
    upload = commands.add_parser("upload")
    upload.add_argument("video", type=Path)
    upload.add_argument("--metadata", type=Path, required=True)
    upload.add_argument("--credential-env", required=True)
    upload.add_argument("--output-dir", type=Path, required=True)
    upload.add_argument("--operation-id", required=True)
    upload.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor"); doctor.add_argument("--json", action="store_true")
    return parser


def _print(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"{payload['resultClass']}: {json.dumps(payload['value'], ensure_ascii=False)}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.operation == "doctor":
        _print({"resultClass": "COMPLETED", "value": {"python": sys.version.split()[0], "transport": "stdlib-resumable", "visibility": "private-only"}}, args.json)
        return 0
    if not ENVIRONMENT_NAME.fullmatch(args.credential_env):
        payload = {"resultClass": "REJECTED_MALFORMED", "value": {"detail": "invalid credential environment name"}}
        _print(payload, args.json); return 2
    secret = os.environ.get(args.credential_env)
    if not secret:
        payload = {"resultClass": "REJECTED_SECRET", "value": {"detail": "credential environment variable is missing or empty"}}
        _print(payload, args.json); return 2
    try:
        result = YouTubePublishOperation().execute(args.video, args.metadata, args.output_dir, args.operation_id, secret)
    finally:
        secret = ""
    payload = {"resultClass": result.result_class, "value": {"receipt": str(result.receipt_path), "externalId": result.external_id, "privacyStatus": "private", "detail": result.error}}
    _print(payload, args.json)
    return 0 if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"} else (3 if result.result_class in {"UNKNOWN", "REJECTED_UNKNOWN"} else 2)


if __name__ == "__main__":
    raise SystemExit(main())
