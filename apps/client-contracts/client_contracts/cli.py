from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import COMMANDS, ClientContracts, ContractError, ContractResult


def parser():
    root=argparse.ArgumentParser(description="Export and validate transport-neutral Studio client contracts."); commands=root.add_subparsers(dest="command",required=True)
    export=commands.add_parser("export"); export.add_argument("--output",type=Path,required=True); export.add_argument("--json",action="store_true")
    show=commands.add_parser("show"); show.add_argument("--json",action="store_true")
    validate=commands.add_parser("validate-command"); validate.add_argument("--input",type=Path,required=True); validate.add_argument("--expected-contract",choices=COMMANDS,required=True); validate.add_argument("--json",action="store_true")
    check=commands.add_parser("check-client"); check.add_argument("--client-version",required=True); check.add_argument("--json",action="store_true")
    doctor=commands.add_parser("doctor"); doctor.add_argument("--json",action="store_true")
    return root


def emit(result,as_json):
    payload={"resultClass":result.result_class,"value":result.value}; print(json.dumps(payload,ensure_ascii=False,separators=(",",":")) if as_json else payload)


def main(argv=None):
    args=parser().parse_args(argv); owner=ClientContracts()
    try:
        if args.command=="export": result=owner.export(args.output)
        elif args.command=="show": result=owner.show()
        elif args.command=="validate-command": result=owner.validate_command(json.loads(args.input.read_text(encoding="utf-8-sig")),args.expected_contract)
        elif args.command=="check-client": result=owner.check_client(args.client_version)
        else: result=ContractResult("COMPLETED",{"contractVersion":"1.0","commands":list(COMMANDS),"persistence":"atomic-json"})
    except (ContractError,OSError,json.JSONDecodeError) as error: result=ContractResult(error.code if isinstance(error,ContractError) else "REJECTED_MALFORMED",{"detail":str(error)})
    emit(result,args.json); return 0 if result.result_class in {"COMPLETED","DUPLICATE_COMPLETED","VALID","COMPATIBLE"} else 2


if __name__=="__main__": raise SystemExit(main())
