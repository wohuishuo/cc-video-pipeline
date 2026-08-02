"""Public CLI for confirmed strict-serial Publication Batch execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable

from .child_executor import PublicPublicationExecutor
from .contracts import BatchExecutionContractError, load_batch_plan, sha256_file
from .operation import PublicationBatchExecution


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Execute a confirmed Publication Batch Plan strictly serially")
    commands = root.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("execute")
    execute.add_argument("batch_plan", type=Path)
    execute.add_argument("--confirmation", required=True)
    execute.add_argument("--credential-vault", type=Path, required=True)
    execute.add_argument("--output-dir", type=Path, required=True)
    execute.add_argument("--operation-id", required=True)
    execute.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor"); doctor.add_argument("--json", action="store_true")
    return root


def _emit(value: dict, as_json: bool) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")) if as_json else json.dumps(value, ensure_ascii=False), flush=True)


def main(
    argv: list[str] | None = None,
    *,
    executor_factory: Callable[[Path, argparse.Namespace], object] | None = None,
) -> int:
    args = parser().parse_args(argv)
    if args.command == "doctor":
        _emit(
            {
                "resultClass": "COMPLETED",
                "value": {
                    "python": sys.version.split()[0], "maximumActiveItems": 1,
                    "resume": "item-checkpoint", "childOwner": "publication",
                    "platformPolicy": "credential-backed-private-youtube",
                },
            },
            args.json,
        )
        return 0
    repository = Path(__file__).resolve().parents[3]
    try:
        batch = load_batch_plan(args.batch_plan, args.confirmation.lower(), args.credential_vault)
        executor = (executor_factory or (lambda root, _args: PublicPublicationExecutor(root / "apps" / "publication" / "run.ps1")))(repository, args)
        result = PublicationBatchExecution().execute(
            batch, args.output_dir, args.operation_id, executor,
            on_log=lambda line: print(line, file=sys.stderr, flush=True),
        )
        receipt = json.loads(result.receipt_path.read_text(encoding="utf-8-sig")) if result.receipt_path.is_file() else {}
        payload = {
            "resultClass": result.result_class,
            "receipt": str(result.receipt_path),
            "artifact": str(result.manifest_path) if result.manifest_path else None,
            "artifactSha256": sha256_file(result.manifest_path) if result.manifest_path else None,
            "itemCount": int(receipt.get("itemCount", 0)),
            "completedCount": int(receipt.get("completedCount", 0)),
            "unknownCount": int(receipt.get("unknownCount", 0)),
            "error": result.error,
        }
        _emit(payload, args.json)
        if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            return 0
        if result.result_class in {"UNKNOWN", "REJECTED_UNKNOWN"}:
            return 3
        return 2 if result.result_class.startswith("REJECTED_") else 1
    except BatchExecutionContractError as error:
        _emit(
            {
                "resultClass": error.code, "receipt": None, "artifact": None,
                "artifactSha256": None, "itemCount": 0, "completedCount": 0,
                "unknownCount": 0, "error": str(error),
            },
            args.json,
        )
        return 3 if error.code == "REJECTED_UNKNOWN" else 2
    except (OSError, TypeError, ValueError) as error:
        _emit(
            {
                "resultClass": "REJECTED_MALFORMED", "receipt": None, "artifact": None,
                "artifactSha256": None, "itemCount": 0, "completedCount": 0,
                "unknownCount": 0, "error": str(error),
            },
            args.json,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
