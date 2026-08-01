"""Public Source Intake CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .contracts import IntakeError, SourceSpec
from .operation import IntakeOperation
from .platform_adapter import PlatformIOTransport


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="source-intake")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in ("folder", "url"):
        child = subparsers.add_parser(mode)
        child.add_argument("source")
        child.add_argument("--output-dir", required=True, type=Path)
        child.add_argument("--operation-id", required=True)
        child.add_argument("--json", action="store_true")
    url = subparsers.choices["url"]
    url.add_argument("--cookies", type=Path)
    url.add_argument("--max-height", type=int, default=1080)
    return parser


def _cookie_key(path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    if not resolved.is_file():
        raise IntakeError("SOURCE_NOT_FOUND", "cookie file does not exist")
    return hashlib.sha256(resolved.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository = Path(__file__).resolve().parents[3]
    try:
        if args.mode == "folder":
            spec = SourceSpec.folder(args.source)
            transport = None
        else:
            key = _cookie_key(args.cookies)
            spec = SourceSpec.url(args.source, max_height=args.max_height, transport_key=key)
            transport = PlatformIOTransport(
                repository / "apps" / "platform-io" / "run.ps1", cookies=args.cookies
            )
        result = IntakeOperation().execute(
            spec,
            args.output_dir,
            args.operation_id,
            transport=transport,
            on_log=lambda line: print(line, flush=True) if not args.json else None,
        )
        payload = {
            "resultClass": result.result_class,
            "receipt": str(result.receipt_path),
            "manifest": str(result.manifest_path) if result.manifest_path else None,
            "error": result.error,
        }
        print(json.dumps(payload, ensure_ascii=True) if args.json else payload)
        return 0 if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"} else 1
    except (IntakeError, OSError, ValueError) as error:
        print(json.dumps({"resultClass": "REJECTED_MALFORMED", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

