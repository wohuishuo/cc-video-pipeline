"""Public command-line boundary for Resource Budget."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .budget import BudgetError, BudgetResult, ResourceBudget


def _common(parser):
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--json", action="store_true")


def _reservation(parser):
    _common(parser)
    parser.add_argument("--reservation-id", required=True)


def _parser():
    root = argparse.ArgumentParser(description="Durable workspace resource reservation leases.")
    commands = root.add_subparsers(dest="command", required=True)
    configure = commands.add_parser("configure"); _common(configure)
    configure.add_argument("--byte-limit", required=True, type=int)
    configure.add_argument("--execution-slots", required=True, type=int)
    reserve = commands.add_parser("reserve"); _reservation(reserve)
    reserve.add_argument("--bytes", required=True, type=int)
    reserve.add_argument("--slots", required=True, type=int)
    reserve.add_argument("--ttl-seconds", required=True, type=int)
    renew = commands.add_parser("renew"); _reservation(renew)
    renew.add_argument("--expected-generation", required=True, type=int)
    renew.add_argument("--ttl-seconds", required=True, type=int)
    release = commands.add_parser("release"); _reservation(release)
    release.add_argument("--expected-generation", required=True, type=int)
    describe = commands.add_parser("describe"); _reservation(describe)
    snapshot = commands.add_parser("snapshot"); _common(snapshot)
    doctor = commands.add_parser("doctor"); doctor.add_argument("--json", action="store_true")
    return root


def _emit(result, as_json):
    payload = {"resultClass": result.result_class, "value": result.value}
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) if as_json else payload)


def _exit_code(result_class):
    if result_class in {"COMPLETED", "DUPLICATE_COMPLETED"}: return 0
    if result_class == "REJECTED_BUDGET": return 3
    return 2


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        result = BudgetResult("COMPLETED", {"python": sys.version.split()[0], "persistence": "sqlite", "transaction": "BEGIN IMMEDIATE"})
        _emit(result, args.json); return 0
    try:
        budget = ResourceBudget(args.database)
        if args.command == "configure": result = budget.configure(args.workspace_id, byte_limit=args.byte_limit, execution_slots=args.execution_slots)
        elif args.command == "reserve": result = budget.reserve(args.workspace_id, args.reservation_id, bytes_requested=args.bytes, slots=args.slots, ttl_seconds=args.ttl_seconds)
        elif args.command == "renew": result = budget.renew(args.workspace_id, args.reservation_id, expected_generation=args.expected_generation, ttl_seconds=args.ttl_seconds)
        elif args.command == "release": result = budget.release(args.workspace_id, args.reservation_id, expected_generation=args.expected_generation)
        elif args.command == "describe": result = budget.describe_reservation(args.workspace_id, args.reservation_id)
        else: result = budget.snapshot(args.workspace_id)
    except BudgetError as error:
        result = BudgetResult(error.code, {"detail": str(error)})
    except (OSError, sqlite3.Error) as error:
        result = BudgetResult("REJECTED_STORAGE", {"detail": f"budget database unavailable: {error}"})
    _emit(result, args.json)
    return _exit_code(result.result_class)


if __name__ == "__main__": raise SystemExit(main())
