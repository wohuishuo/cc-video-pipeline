"""Real Client Contracts CLI to unauthenticated Studio loopback evidence."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
from urllib.request import urlopen


class RejectingApplication:
    def handle(self, method, path, query, body):
        return 403, {"resultClass": "REJECTED_UNAUTHORIZED"}


class RejectingAdmission:
    workspace_id = "proof"

    def authorize(self, workspace_id, token, scope):
        raise AssertionError("public contract discovery reached workspace admission")


def main() -> int:
    repository = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repository / "apps" / "video-graph-studio"))
    from studio.client_contracts import ClientContractsCommandAdapter
    from studio.server import create_server

    contracts = ClientContractsCommandAdapter(
        repository / "apps" / "client-contracts" / "run.ps1"
    )
    server = create_server(
        "127.0.0.1",
        0,
        RejectingApplication(),
        web_root=repository / "apps" / "video-graph-studio" / "web",
        admission=RejectingAdmission(),
        client_contracts=contracts,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/contracts"
        with urlopen(url, timeout=10) as response:
            first_status = response.status
            first = json.loads(response.read())
        with urlopen(url, timeout=10) as response:
            second_status = response.status
            second = json.loads(response.read())
        bundle = first["value"]["bundle"]
        receipt = {
            "firstHttpStatus": first_status,
            "secondHttpStatus": second_status,
            "sameServerGenerationResult": first == second,
            "contractVersion": bundle["contractVersion"],
            "commands": sorted(bundle["commands"]),
            "discoveryScope": bundle["endpoints"]["GET /api/v1/contracts"]["scope"],
            "bundleSha256": first["value"]["sha256"],
        }
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0 if first_status == second_status == 200 and first == second else 1
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
