"""Public command-line boundary for the Transcription MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable

from .adapters import FasterWhisperAdapter
from .operation import TranscriptAdapter, TranscriptLoop


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Transcribe every media item in a Source Intake manifest serially."
    )
    value.add_argument("source_manifest", type=Path)
    value.add_argument("--output-dir", type=Path, required=True)
    value.add_argument("--operation-id", required=True)
    value.add_argument("--language", default="auto")
    value.add_argument("--model", default="small")
    value.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    value.add_argument("--compute-type", default="default")
    value.add_argument("--json", action="store_true")
    return value


def main(
    argv: list[str] | None = None,
    *,
    adapter_factory: Callable[[argparse.Namespace], TranscriptAdapter] | None = None,
) -> int:
    args = parser().parse_args(argv)
    factory = adapter_factory or (
        lambda options: FasterWhisperAdapter(
            options.model,
            device=options.device,
            compute_type=options.compute_type,
        )
    )
    adapter = factory(args)
    result = TranscriptLoop().execute(
        args.source_manifest,
        args.output_dir,
        args.operation_id,
        language=args.language,
        adapter=adapter,
        on_log=lambda message: print(message, file=sys.stderr, flush=True),
    )
    payload = {
        "resultClass": result.result_class,
        "receipt": str(result.receipt_path),
        "manifest": str(result.manifest_path) if result.manifest_path else None,
        "error": result.error,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"{result.result_class}: {result.manifest_path or result.error}")
    return 0 if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"} else 2 if result.result_class == "REJECTED_CONFLICT" else 1


if __name__ == "__main__":
    raise SystemExit(main())

