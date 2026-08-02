"""Public command-line boundary for Workspace Storage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .registry import NAMESPACE_KINDS, StorageRegistry, StorageRegistryError, StorageResult


def _registry_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry", required=True, type=Path)


def _workspace_argument(parser: argparse.ArgumentParser) -> None:
    _registry_argument(parser)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--json", action="store_true")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tenant-scoped state, artifact and temporary storage namespaces."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    provision = commands.add_parser("provision")
    _workspace_argument(provision)
    provision.add_argument("--storage-root", required=True, type=Path)
    provision.add_argument("--quota-bytes", required=True, type=int)

    describe = commands.add_parser("describe")
    _workspace_argument(describe)

    resolve = commands.add_parser("resolve")
    _workspace_argument(resolve)
    resolve.add_argument("--kind", required=True, choices=NAMESPACE_KINDS)
    resolve.add_argument("--relative-path", required=True)

    capacity = commands.add_parser("capacity")
    _workspace_argument(capacity)
    capacity.add_argument("--required-bytes", required=True, type=int)

    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    return parser


def _print(result: StorageResult, as_json: bool) -> None:
    payload = {"resultClass": result.result_class, "value": result.value}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"{result.result_class}: {json.dumps(result.value, ensure_ascii=False)}")


def _exit_code(result_class: str) -> int:
    if result_class in {"COMPLETED", "DUPLICATE_COMPLETED", "ALLOWED"}:
        return 0
    if result_class == "REJECTED_QUOTA":
        return 3
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        result = StorageResult(
            "COMPLETED",
            {
                "python": sys.version.split()[0],
                "namespaceKinds": list(NAMESPACE_KINDS),
                "persistence": "atomic-json",
            },
        )
        _print(result, args.json)
        return 0

    registry = StorageRegistry(args.registry)
    try:
        if args.command == "provision":
            result = registry.provision_workspace(
                args.workspace_id,
                args.storage_root,
                quota_bytes=args.quota_bytes,
            )
        elif args.command == "describe":
            result = registry.describe_workspace(args.workspace_id)
        elif args.command == "resolve":
            result = registry.resolve_path(
                args.workspace_id, args.kind, args.relative_path
            )
        else:
            result = registry.check_capacity(
                args.workspace_id, required_bytes=args.required_bytes
            )
    except StorageRegistryError as error:
        result = StorageResult(error.code, {"detail": str(error)})
    _print(result, args.json)
    return _exit_code(result.result_class)


if __name__ == "__main__":
    raise SystemExit(main())
