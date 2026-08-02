"""Public CLI for manifest-driven localized video composition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .ffmpeg import FfmpegCompositionAdapter
from .operation import LocalizationLoop


def parser():
    value=argparse.ArgumentParser(description="Compose localized MP4 derivatives from Source, Translation and Voice manifests.")
    value.add_argument("source_manifest",type=Path); value.add_argument("translation_manifest",type=Path); value.add_argument("voice_manifest",type=Path)
    value.add_argument("--output-dir",type=Path,required=True); value.add_argument("--operation-id",required=True); value.add_argument("--source-volume",type=float,default=0.12); value.add_argument("--json",action="store_true")
    return value


def main(argv=None,*,adapter_factory=None):
    args=parser().parse_args(argv); adapter=(adapter_factory or (lambda _args:FfmpegCompositionAdapter()))(args)
    result=LocalizationLoop().execute(args.source_manifest,args.translation_manifest,args.voice_manifest,args.output_dir,args.operation_id,adapter=adapter,source_volume=args.source_volume,on_log=lambda message:print(message,file=sys.stderr,flush=True))
    payload={"resultClass":result.result_class,"receipt":str(result.receipt_path),"manifest":str(result.manifest_path) if result.manifest_path else None,"error":result.error}
    print(json.dumps(payload,ensure_ascii=False) if args.json else f"{result.result_class}: {result.manifest_path or result.error}")
    return 0 if result.result_class in {"COMPLETED","DUPLICATE_COMPLETED"} else 2 if result.result_class=="REJECTED_CONFLICT" else 1


if __name__=="__main__": raise SystemExit(main())
