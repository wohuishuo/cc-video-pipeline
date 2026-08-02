"""Public CLI for local YouTube account connection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .operation import OAuthBootstrapOperation
from .vault_writer import VaultWriter


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Connect one YouTube account through desktop OAuth")
    commands = root.add_subparsers(dest="operation", required=True)
    connect = commands.add_parser("connect")
    connect.add_argument("--client-config", type=Path, required=True)
    connect.add_argument("--vault", type=Path, required=True)
    connect.add_argument("--credential-id", required=True)
    connect.add_argument("--label", required=True)
    connect.add_argument("--output-dir", type=Path, required=True)
    connect.add_argument("--operation-id", required=True)
    connect.add_argument("--timeout", type=float, default=300)
    connect.add_argument("--no-open", action="store_true")
    connect.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor"); doctor.add_argument("--json", action="store_true")
    return root


def emit(payload: dict, as_json: bool) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) if as_json else json.dumps(payload, ensure_ascii=False), flush=True)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.operation == "doctor":
        emit({"resultClass": "COMPLETED", "value": {"python": sys.version.split()[0], "callback": "127.0.0.1:ephemeral", "pkce": "S256", "scope": "youtube.upload"}}, args.json); return 0
    repository = Path(__file__).resolve().parents[3]
    opener = (lambda url: False) if args.no_open else __import__("webbrowser").open
    operation = OAuthBootstrapOperation(vault_writer=VaultWriter(repository / "apps" / "credential-vault" / "run.ps1"), browser_opener=opener)
    result = operation.execute(args.client_config, args.vault, args.credential_id, args.label, args.output_dir, args.operation_id, timeout=args.timeout, on_event=lambda value: emit(value, args.json))
    emit({"resultClass": result.result_class, "value": {**result.value, "receipt": str(result.receipt_path), "detail": result.error}}, args.json)
    return 0 if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
