"""Public CLI for durable creator localization batches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable

from .child_pipeline import PublicMvpItemProcessor
from .contracts import BatchContractError, BatchPolicy, CreatorSource
from .operation import BatchOperation


def _voices(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise BatchContractError("voice policy must be LANGUAGE=VOICE")
        language, voice = (part.strip() for part in value.split("=", 1))
        if not language or not voice or language in result:
            raise BatchContractError("voice policy is empty or duplicated")
        result[language] = voice
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Localize every Creator Manifest item strictly serially")
    commands = root.add_subparsers(dest="command", required=True)
    localize = commands.add_parser("localize")
    localize.add_argument("creator_manifest", type=Path)
    localize.add_argument("--target-language", action="append", required=True)
    localize.add_argument("--voice", action="append", required=True)
    localize.add_argument("--voice-provider", default="edge", choices=("edge", "qwen3", "original"))
    localize.add_argument("--qwen-device", default="auto", choices=("auto", "cuda", "cpu"))
    localize.add_argument("--cookies", type=Path)
    localize.add_argument("--output-dir", type=Path, required=True)
    localize.add_argument("--operation-id", required=True)
    localize.add_argument("--source-language", default="auto")
    localize.add_argument("--asr-model", default="small")
    localize.add_argument("--asr-device", default="auto", choices=("auto", "cpu", "cuda"))
    localize.add_argument("--asr-compute-type", default="default")
    localize.add_argument("--translation-model", default="facebook/nllb-200-distilled-600M")
    localize.add_argument("--translation-provider", default="nllb", choices=("nllb", "deepseek"))
    localize.add_argument("--translation-device", default="auto", choices=("auto", "cpu", "cuda"))
    localize.add_argument("--translation-batch-size", type=int, default=8)
    localize.add_argument("--source-volume", type=float, default=0.12)
    localize.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    return root


def _emit(value: dict, as_json: bool) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")) if as_json else json.dumps(value, ensure_ascii=False), flush=True)


def main(
    argv: list[str] | None = None,
    *,
    processor_factory: Callable[[Path, argparse.Namespace], object] | None = None,
) -> int:
    args = parser().parse_args(argv)
    if args.command == "doctor":
        _emit(
            {
                "resultClass": "COMPLETED",
                "value": {
                    "python": sys.version.split()[0],
                    "maximumActiveItems": 1,
                    "resume": "item-checkpoint",
                    "owners": 5,
                },
            },
            args.json,
        )
        return 0
    repository = Path(__file__).resolve().parents[3]
    try:
        source = CreatorSource.load(args.creator_manifest)
        policy = BatchPolicy.create(
            args.target_language,
            _voices(args.voice),
            voice_provider=args.voice_provider,
            qwen_device=args.qwen_device,
            source_language=args.source_language,
            asr_model=args.asr_model,
            asr_device=args.asr_device,
            asr_compute_type=args.asr_compute_type,
            translation_model=args.translation_model,
            translation_provider=args.translation_provider,
            translation_device=args.translation_device,
            translation_batch_size=args.translation_batch_size,
            source_volume=args.source_volume,
        )
        processor = (processor_factory or (lambda root, _options: PublicMvpItemProcessor(root)))(repository, args)
        result = BatchOperation().execute(
            source,
            policy,
            args.output_dir,
            args.operation_id,
            processor=processor,
            cookies=args.cookies,
            on_log=lambda line: print(line, file=sys.stderr, flush=True),
        )
        payload = {
            "resultClass": result.result_class,
            "receipt": str(result.receipt_path),
            "manifest": str(result.manifest_path) if result.manifest_path is not None else None,
            "error": result.error,
        }
        _emit(payload, args.json)
        if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            return 0
        return 2 if result.result_class in {"REJECTED_MALFORMED", "REJECTED_CONFLICT"} else 1
    except (BatchContractError, OSError, TypeError, ValueError) as error:
        _emit({"resultClass": "REJECTED_MALFORMED", "receipt": None, "manifest": None, "error": str(error)}, args.json)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
