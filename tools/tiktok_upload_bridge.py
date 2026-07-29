from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    root.add_argument("--checkout", required=True, type=Path)
    root.add_argument("operation", choices=("login", "check", "upload-video"))
    root.add_argument("--account", required=True)
    root.add_argument("--file", type=Path)
    root.add_argument("--title")
    root.add_argument("--desc", default="")
    root.add_argument("--tags", default="")
    return root


def main() -> int:
    args = parser().parse_args()
    checkout = args.checkout.resolve()
    sys.path.insert(0, str(checkout))
    from uploader.tk_uploader.main_chrome import TiktokVideo, cookie_auth, tiktok_setup

    account = checkout / "cookies" / "tk_uploader" / f"{args.account}.json"
    account.parent.mkdir(parents=True, exist_ok=True)
    if args.operation == "login":
        return 0 if asyncio.run(tiktok_setup(str(account), handle=True)) else 1
    if args.operation == "check":
        return 0 if account.exists() and asyncio.run(cookie_auth(str(account))) else 1
    if not args.file or not args.title:
        raise SystemExit("upload-video requires --file and --title")
    application = TiktokVideo(args.title, args.file.resolve(), [tag for tag in args.tags.split(",") if tag], 0, account)
    asyncio.run(application.main(), debug=False)
    return 0


raise SystemExit(main())
