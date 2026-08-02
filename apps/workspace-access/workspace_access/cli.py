"""Command-line boundary for Workspace Access."""

from __future__ import annotations

import argparse
from datetime import timedelta
import json
import os
from pathlib import Path
import sys

from .registry import AccessRegistry, AccessResult, KNOWN_SCOPES, RegistryError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workspace identity and access policy MVP.")
    commands = parser.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser("init")
    _registry_argument(initialize)
    initialize.add_argument("--workspace-id", required=True)
    initialize.add_argument("--display-name", required=True)
    initialize.add_argument("--allowed-root", action="append", required=True, type=Path)
    initialize.add_argument("--json", action="store_true")

    issue = commands.add_parser("issue")
    _registry_argument(issue)
    issue.add_argument("--workspace-id", required=True)
    issue.add_argument("--label", required=True)
    issue.add_argument("--scope", action="append", required=True, choices=sorted(KNOWN_SCOPES))
    issue.add_argument("--ttl-hours", required=True, type=float)
    issue.add_argument("--json", action="store_true")

    authorize = commands.add_parser("authorize")
    _registry_argument(authorize)
    authorize.add_argument("--workspace-id", required=True)
    authorize.add_argument("--required-scope", required=True, choices=sorted(KNOWN_SCOPES))
    authorize.add_argument("--token-env", default="VIDEO_GRAPH_ACCESS_TOKEN")
    authorize.add_argument("--json", action="store_true")

    revoke = commands.add_parser("revoke")
    _registry_argument(revoke)
    revoke.add_argument("--workspace-id", required=True)
    revoke.add_argument("--token-id", required=True)
    revoke.add_argument("--json", action="store_true")

    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    return parser


def _registry_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry", required=True, type=Path)


def _print(result: AccessResult, as_json: bool) -> None:
    payload = {"resultClass": result.result_class, "value": result.value}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"{result.result_class}: {json.dumps(result.value, ensure_ascii=False)}")


def _exit_code(result_class: str) -> int:
    if result_class in {"COMPLETED", "DUPLICATE_COMPLETED", "AUTHORIZED"}:
        return 0
    if result_class == "REJECTED_UNAUTHORIZED":
        return 3
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        result = AccessResult(
            "COMPLETED",
            {
                "python": sys.version.split()[0],
                "knownScopes": sorted(KNOWN_SCOPES),
                "secretInput": "environment-only",
            },
        )
        _print(result, args.json)
        return 0
    if args.command == "authorize" and not os.environ.get(args.token_env):
        result = AccessResult(
            "REJECTED_UNAUTHORIZED",
            {"workspaceId": args.workspace_id, "detail": "credential environment variable missing"},
        )
        _print(result, args.json)
        return 3

    registry = AccessRegistry(args.registry)
    try:
        if args.command == "init":
            result = registry.initialize_workspace(
                args.workspace_id, args.display_name, args.allowed_root
            )
        elif args.command == "issue":
            result = registry.issue_token(
                args.workspace_id,
                args.label,
                args.scope,
                ttl=timedelta(hours=args.ttl_hours),
            )
        elif args.command == "authorize":
            result = registry.authorize(
                os.environ[args.token_env], args.workspace_id, args.required_scope
            )
        else:
            result = registry.revoke_token(args.workspace_id, args.token_id)
    except RegistryError as error:
        result = AccessResult(error.code, {"detail": str(error)})
    _print(result, args.json)
    return _exit_code(result.result_class)


if __name__ == "__main__":
    raise SystemExit(main())
