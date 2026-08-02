"""Public command-line boundary for the Translation MVP."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Callable

from .adapters import DeepSeekAdapter, NllbAdapter
from .contracts import TranslationError
from .operation import TranslationAdapter, TranslationLoop


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Translate every transcript item serially into one or more target languages."
    )
    value.add_argument("transcript_manifest", type=Path)
    value.add_argument("--output-dir", type=Path, required=True)
    value.add_argument("--operation-id", required=True)
    value.add_argument("--target-language", action="append", required=True)
    value.add_argument("--provider", default="nllb", choices=("nllb", "deepseek"))
    value.add_argument("--model")
    value.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    value.add_argument("--batch-size", type=int, default=8)
    value.add_argument("--json", action="store_true")
    return value


def main(
    argv: list[str] | None = None,
    *,
    adapter_factory: Callable[[argparse.Namespace], TranslationAdapter] | None = None,
) -> int:
    args = parser().parse_args(argv)
    if args.model is None:
        args.model = "deepseek-v4-flash" if args.provider == "deepseek" else "facebook/nllb-200-distilled-600M"
    factory = adapter_factory or _adapter
    try:
        result = TranslationLoop().execute(
            args.transcript_manifest,
            args.output_dir,
            args.operation_id,
            target_languages=args.target_language,
            adapter=factory(args),
            on_log=lambda message: print(message, file=sys.stderr, flush=True),
        )
    except TranslationError as error:
        payload = {"resultClass": "REJECTED_MALFORMED", "receipt": None, "manifest": None, "error": str(error)}
        print(json.dumps(payload, ensure_ascii=False) if args.json else f"REJECTED_MALFORMED: {error}")
        return 2
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


def _adapter(options: argparse.Namespace):
    if options.provider == "deepseek":
        return DeepSeekAdapter(os.environ.get("DEEPSEEK_API_KEY", ""), model=options.model)
    return NllbAdapter(options.model, device=options.device, batch_size=options.batch_size)


if __name__ == "__main__":
    raise SystemExit(main())
