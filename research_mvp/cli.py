from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .demo_adapters import DemoConnector, DemoEvidenceCollector
from .repository import ConflictError, FileResearchRepository
from .service import ResearchService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research")
    parser.add_argument("--workspace", required=True)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("source")
    create.add_argument("--language", default="auto")

    for name in ("status", "show", "retry"):
        command = commands.add_parser(name)
        command.add_argument("job_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository = FileResearchRepository(Path(args.workspace))
    service = ResearchService(
        repository, DemoConnector(), DemoEvidenceCollector()
    )
    try:
        if args.command == "create":
            result = service.create(
                args.source, {"language": args.language}
            )
        elif args.command == "status":
            result = service.status(args.job_id)
        elif args.command == "show":
            result = service.show(args.job_id)
        else:
            result = service.retry(args.job_id)
        print(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        )
        return 0
    except (ValueError, FileNotFoundError, ConflictError) as error:
        payload = {"status": "failed", "error": str(error)}
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 2
