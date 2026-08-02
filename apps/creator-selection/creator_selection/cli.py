"""Creator Selection CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import SelectionError, SelectionSpec
from .operation import SelectionOperation


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="creator-selection",
        description="Select an exact ordered subset from a verified Creator Manifest.",
    )
    commands = root.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select")
    select.add_argument("creator_manifest", type=Path)
    select.add_argument("--video-id", action="append", required=True)
    select.add_argument("--output-dir", type=Path, required=True)
    select.add_argument("--operation-id", required=True)
    select.add_argument("--json", action="store_true")
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        spec = SelectionSpec.load(args.creator_manifest, args.video_id)
        result = SelectionOperation().execute(spec, args.output_dir, args.operation_id)
        payload = {
            "resultClass": result.result_class,
            "receipt": str(result.receipt_path),
            "manifest": str(result.manifest_path) if result.manifest_path else None,
            "error": result.error,
        }
        print(json.dumps(payload, ensure_ascii=True) if args.json else payload)
        if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            return 0
        return 2 if result.result_class == "REJECTED_CONFLICT" else 1
    except (SelectionError, OSError, ValueError) as error:
        print(
            json.dumps(
                {
                    "resultClass": "REJECTED_MALFORMED",
                    "errorCode": getattr(error, "code", "INVALID_INPUT"),
                    "error": str(error),
                },
                ensure_ascii=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
