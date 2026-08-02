"""Creator Profile Discovery CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .adapters import F2DouyinEnumerator, YtDlpProfileEnumerator
from .contracts import DiscoveryError, ProfileSpec
from .operation import DiscoveryOperation


def parser():
    root=argparse.ArgumentParser(prog="creator-discovery",epilog="Example: profile URL --max-items 20 --output-dir PATH --operation-id ID")
    commands=root.add_subparsers(dest="command",required=True); profile=commands.add_parser("profile")
    profile.add_argument("url"); profile.add_argument("--output-dir",type=Path,required=True); profile.add_argument("--operation-id",required=True)
    profile.add_argument("--max-items",type=int,default=0,help="Maximum videos; 0 discovers all available videos")
    profile.add_argument("--cookies",type=Path); profile.add_argument("--json",action="store_true")
    return root


def _cookie_key(path):
    if path is None: return None
    resolved=Path(path).resolve()
    if not resolved.is_file(): raise DiscoveryError("authentication material file does not exist")
    return hashlib.sha256(resolved.read_bytes()).hexdigest()


def main(argv=None):
    args=parser().parse_args(argv); repository=Path(__file__).resolve().parents[3]
    try:
        spec=ProfileSpec.from_url(args.url,max_items=args.max_items,cookie_key=_cookie_key(args.cookies))
        if spec.platform=="douyin":
            candidates=(repository/".tools"/"f2"/".venv"/"Scripts"/"python.exe",repository.parents[1]/".tools"/"f2"/".venv"/"Scripts"/"python.exe")
            python=next((path for path in candidates if path.is_file()),candidates[0])
            adapter=F2DouyinEnumerator(python,Path(__file__).with_name("f2_helper.py"))
        else: adapter=YtDlpProfileEnumerator()
        result=DiscoveryOperation().execute(spec,args.output_dir,args.operation_id,enumerator=adapter,cookies=args.cookies,on_log=lambda line:print(line,flush=True) if not args.json else None)
        payload={"resultClass":result.result_class,"receipt":str(result.receipt_path),"manifest":str(result.manifest_path) if result.manifest_path else None,"error":result.error}
        print(json.dumps(payload,ensure_ascii=True) if args.json else payload)
        return 0 if result.result_class in {"COMPLETED","DUPLICATE_COMPLETED"} else 2 if result.result_class=="REJECTED_CONFLICT" else 1
    except (DiscoveryError,OSError,ValueError) as error:
        print(json.dumps({"resultClass":"REJECTED_MALFORMED","error":str(error)},ensure_ascii=True)); return 2


if __name__=="__main__": raise SystemExit(main())
