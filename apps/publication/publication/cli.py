"""Two-phase Guarded Publication CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import PLATFORMS, PlanSpec, PublicationError
from .execution import PlatformIOExecutionAdapter, PublicationExecution
from .planning import PublicationPlanner


def parser():
    root=argparse.ArgumentParser(prog="publication"); commands=root.add_subparsers(dest="command",required=True)
    plan=commands.add_parser("plan"); plan.add_argument("video",type=Path); plan.add_argument("--metadata",type=Path,required=True); plan.add_argument("--target",action="append",required=True,help="platform=account"); plan.add_argument("--public",action="store_true"); plan.add_argument("--output-dir",type=Path,required=True); plan.add_argument("--operation-id",required=True); plan.add_argument("--json",action="store_true")
    execute=commands.add_parser("execute"); execute.add_argument("plan",type=Path); execute.add_argument("--confirmation",required=True); execute.add_argument("--output-dir",type=Path,required=True); execute.add_argument("--operation-id",required=True); execute.add_argument("--json",action="store_true")
    return root


def targets(values):
    result={}
    for value in values:
        platform,separator,account=value.partition("=")
        if not separator or platform not in PLATFORMS or platform in result: raise PublicationError("each --target must be a unique platform=account")
        result[platform]=account
    return result


def main(argv=None):
    args=parser().parse_args(argv); repository=Path(__file__).resolve().parents[3]
    try:
        if args.command=="plan":
            result=PublicationPlanner().execute(PlanSpec.create(args.video,args.metadata,targets(args.target),public=args.public),args.output_dir,args.operation_id); artifact=result.plan_path
        else:
            result=PublicationExecution().execute(args.plan,args.output_dir,args.operation_id,confirmation=args.confirmation,adapter=PlatformIOExecutionAdapter(repository/"apps"/"platform-io"/"run.ps1"),on_log=lambda line:print(line,flush=True) if not args.json else None); artifact=result.manifest_path
        payload={"resultClass":result.result_class,"receipt":str(result.receipt_path),"artifact":str(artifact) if artifact else None,"error":result.error}; print(json.dumps(payload,ensure_ascii=True) if args.json else payload)
        return 0 if result.result_class in {"COMPLETED","DUPLICATE_COMPLETED"} else 2 if result.result_class.startswith("REJECTED") else 1
    except (PublicationError,OSError,ValueError) as error:
        print(json.dumps({"resultClass":"REJECTED_MALFORMED","error":str(error)},ensure_ascii=True)); return 2


if __name__=="__main__": raise SystemExit(main())
