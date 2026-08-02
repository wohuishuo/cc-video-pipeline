"""Public CLI for serial voice rendering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .adapters import EdgeTtsAdapter, OriginalAudioAdapter, Qwen3TtsAdapter
from .operation import VoiceRenderingLoop


def parse_voices(values):
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError("voice policy must be LANGUAGE=VOICE")
        language, voice = (part.strip() for part in value.split("=", 1))
        if not language or not voice or language in result:
            raise ValueError("voice policy is empty or duplicated")
        result[language] = voice
    return result


def parser():
    value = argparse.ArgumentParser(description="Render one provider-selected clip per translated segment serially.")
    value.add_argument("translation_manifest", type=Path)
    value.add_argument("--output-dir", type=Path, required=True)
    value.add_argument("--operation-id", required=True)
    value.add_argument("--voice", action="append", required=True, help="LANGUAGE=VOICE_ID")
    value.add_argument("--provider", choices=("edge", "qwen3", "original"), default="edge")
    value.add_argument("--qwen-device", choices=("cpu", "cuda", "xpu"), default="cpu")
    value.add_argument("--rate", default="+0%")
    value.add_argument("--volume", default="+0%")
    value.add_argument("--json", action="store_true")
    return value


def main(argv=None, *, adapter_factory=None):
    args = parser().parse_args(argv)
    voices = parse_voices(args.voice)
    def default_factory(options):
        if options.provider == "qwen3":
            return Qwen3TtsAdapter(device=options.qwen_device)
        if options.provider == "original":
            return OriginalAudioAdapter()
        return EdgeTtsAdapter(rate=options.rate, volume=options.volume)

    adapter = (adapter_factory or default_factory)(args)
    result = VoiceRenderingLoop().execute(args.translation_manifest, args.output_dir, args.operation_id, voices=voices, adapter=adapter, on_log=lambda message: print(message, file=sys.stderr, flush=True))
    payload = {"resultClass": result.result_class, "receipt": str(result.receipt_path), "manifest": str(result.manifest_path) if result.manifest_path else None, "error": result.error}
    print(json.dumps(payload, ensure_ascii=False) if args.json else f"{result.result_class}: {result.manifest_path or result.error}")
    return 0 if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"} else 2 if result.result_class == "REJECTED_CONFLICT" else 1


if __name__ == "__main__": raise SystemExit(main())
