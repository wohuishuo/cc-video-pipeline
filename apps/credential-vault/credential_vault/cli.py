"""Public command-line boundary for Credential Vault."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .vault import CredentialVault, VaultError, VaultResult


ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _vault_credential(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--credential-id", required=True)


def _secret_env(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--secret-env", required=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CurrentUser-protected local credential custody and child injection."
    )
    commands = parser.add_subparsers(dest="operation", required=True)

    put = commands.add_parser("put")
    _vault_credential(put)
    put.add_argument("--provider", required=True)
    put.add_argument("--label", required=True)
    _secret_env(put)
    put.add_argument("--json", action="store_true")

    rotate = commands.add_parser("rotate")
    _vault_credential(rotate)
    _secret_env(rotate)
    rotate.add_argument("--json", action="store_true")

    for name in ("describe", "revoke"):
        command = commands.add_parser(name)
        _vault_credential(command)
        command.add_argument("--json", action="store_true")

    run = commands.add_parser("run")
    _vault_credential(run)
    run.add_argument("--target-env", required=True)
    run.add_argument("--executable", required=True)
    run.add_argument("--argument", action="append", default=[])
    run.add_argument("--json", action="store_true")

    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    return parser


def _print(result: VaultResult, as_json: bool) -> None:
    payload = {"resultClass": result.result_class, "value": result.value}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"{result.result_class}: {json.dumps(result.value, ensure_ascii=False)}")


def _secret_from_environment(name: str) -> str:
    if not ENVIRONMENT_NAME.fullmatch(name):
        raise VaultError("REJECTED_MALFORMED", "invalid secret environment name")
    value = os.environ.get(name)
    if not value:
        raise VaultError("REJECTED_SECRET", "secret environment variable is missing or empty")
    return value


def _exit_code(result_class: str) -> int:
    return 0 if result_class in {"COMPLETED", "DUPLICATE_COMPLETED"} else 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.operation == "doctor":
        result = VaultResult(
            "COMPLETED",
            {
                "python": sys.version.split()[0],
                "platform": "windows" if os.name == "nt" else os.name,
                "protection": "dpapi-current-user",
                "persistence": "atomic-json",
            },
        )
        _print(result, args.json)
        return 0

    try:
        vault = CredentialVault(args.vault)
        if args.operation == "put":
            result = vault.put(
                args.credential_id,
                args.provider,
                args.label,
                _secret_from_environment(args.secret_env),
            )
        elif args.operation == "rotate":
            result = vault.rotate(
                args.credential_id, _secret_from_environment(args.secret_env)
            )
        elif args.operation == "describe":
            result = vault.describe(args.credential_id)
        elif args.operation == "revoke":
            result = vault.revoke(args.credential_id)
        else:
            if not ENVIRONMENT_NAME.fullmatch(args.target_env):
                raise VaultError("REJECTED_MALFORMED", "invalid target environment name")
            child_argv = [args.executable, *args.argument]
            secret = vault.resolve_secret(args.credential_id)
            child_environment = {**os.environ, args.target_env: secret}
            try:
                try:
                    completed = subprocess.run(
                        child_argv, env=child_environment, shell=False
                    )
                except OSError as error:
                    raise VaultError(
                        "REJECTED_CHILD", f"could not start child process: {error}"
                    ) from error
                return completed.returncode
            finally:
                child_environment.pop(args.target_env, None)
                secret = ""
    except VaultError as error:
        result = VaultResult(error.code, {"detail": str(error)})
    _print(result, args.json)
    return _exit_code(result.result_class)


if __name__ == "__main__":
    raise SystemExit(main())
