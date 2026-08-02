"""Public CLI for strict-serial Publication Batch planning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable

from .child_planner import PublicPublicationPlanner
from .contracts import BatchContractError, BatchPolicy, load_localization_manifest, load_metadata_template, sha256_file
from .operation import PublicationBatchOperation


def _targets(values: list[str]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise BatchContractError("target must be PLATFORM=ACCOUNT")
        platform, account = (part.strip() for part in value.split("=", 1))
        rows.append((platform, account))
    return rows


def _credentials(values: list[str]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise BatchContractError("credential must be PLATFORM=CREDENTIAL_ID")
        platform, credential_id = (part.strip() for part in value.split("=", 1))
        if not platform or not credential_id or platform in rows:
            raise BatchContractError("credential reference is empty or duplicated")
        rows[platform] = credential_id
    return rows


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Plan every localized derivative strictly serially")
    commands = root.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("localization_manifest", type=Path)
    plan.add_argument("--metadata-template", type=Path, required=True)
    plan.add_argument("--target", action="append", required=True)
    plan.add_argument("--credential", action="append", default=[])
    plan.add_argument("--output-dir", type=Path, required=True)
    plan.add_argument("--operation-id", required=True)
    plan.add_argument("--json", action="store_true")
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
                    "childOwner": "publication",
                },
            },
            args.json,
        )
        return 0
    repository = Path(__file__).resolve().parents[3]
    try:
        localization = load_localization_manifest(args.localization_manifest)
        metadata_template = load_metadata_template(args.metadata_template)
        policy = BatchPolicy.create(_targets(args.target), _credentials(args.credential))
        processor = (processor_factory or (lambda root, _options: PublicPublicationPlanner(root / "apps" / "publication" / "run.ps1")))(
            repository, args
        )
        result = PublicationBatchOperation().execute(
            localization,
            metadata_template,
            policy,
            args.output_dir,
            args.operation_id,
            processor,
            on_log=lambda line: print(line, file=sys.stderr, flush=True),
        )
        receipt = json.loads(result.receipt_path.read_text(encoding="utf-8-sig")) if result.receipt_path.is_file() else {}
        manifest_sha = sha256_file(result.manifest_path) if result.manifest_path is not None else None
        payload = {
            "resultClass": result.result_class,
            "receipt": str(result.receipt_path),
            "manifest": str(result.manifest_path) if result.manifest_path is not None else None,
            "manifestSha256": manifest_sha,
            "itemCount": int(receipt.get("itemCount", 0)),
            "jobCount": sum(int(row.get("jobCount", 0)) for row in receipt.get("items", []) if isinstance(row, dict)),
            "error": result.error,
        }
        _emit(payload, args.json)
        if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            return 0
        return 2 if result.result_class.startswith("REJECTED_") else 1
    except (BatchContractError, OSError, TypeError, ValueError) as error:
        _emit(
            {
                "resultClass": "REJECTED_MALFORMED",
                "receipt": None,
                "manifest": None,
                "manifestSha256": None,
                "itemCount": 0,
                "jobCount": 0,
                "error": str(error),
            },
            args.json,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
