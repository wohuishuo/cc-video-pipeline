"""Real Resource Budget CLI + Studio lifecycle evidence drill."""

from __future__ import annotations

import hashlib
import gc
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def last_json(output: str) -> dict:
    return json.loads([line for line in output.splitlines() if line.strip()][-1])


def main() -> int:
    repository = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repository / "apps" / "video-graph-studio"))
    from studio.adapters import CommandAdapter
    from studio.contracts import GraphDefinition
    from studio.engine import WorkflowEngine
    from studio.resource_leases import ResourceBudgetCommandAdapter, ResourceLeaseCoordinator
    from studio.store import CreateRun, RunStore

    with tempfile.TemporaryDirectory(prefix="resource-aware-studio-") as directory:
        root = Path(directory)
        database = root / "budget.db"
        launcher = repository / "apps" / "resource-budget" / "run.ps1"
        common = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(launcher),
        ]
        configured = subprocess.run(
            [*common, "configure", "--database", str(database), "--workspace-id", "alpha",
             "--byte-limit", "4096", "--execution-slots", "1", "--json"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        marker = root / "child-completed.txt"
        graph = GraphDefinition.from_dict({
            "schemaVersion": 1,
            "graphId": "resource-aware-proof",
            "revision": 1,
            "nodes": [{
                "id": "real-child",
                "type": "command",
                "config": {"argv": [sys.executable, "-c", f"from pathlib import Path; Path(r'{marker}').write_text('completed', encoding='utf-8')"]},
            }],
            "edges": [],
        })
        store = RunStore(root / "studio.db")
        run_id = store.create_run(CreateRun("resource-proof", "resource-proof-correlation", graph, {})).value["runId"]
        coordinator = ResourceLeaseCoordinator(
            ResourceBudgetCommandAdapter(launcher, database),
            workspace_id="alpha",
            bytes_per_run=4096,
            ttl_seconds=3,
        )
        engine = WorkflowEngine(store, {"command": CommandAdapter()}, lease_coordinator=coordinator)
        engine.start(run_id)
        deadline = time.monotonic() + 30
        while store.get_run(run_id)["status"] not in {"COMPLETED", "FAILED", "CANCELLED"}:
            if time.monotonic() >= deadline:
                raise TimeoutError("Studio run did not become terminal")
            time.sleep(0.05)
        run = store.get_run(run_id)
        if not engine.wait_idle(10):
            raise TimeoutError("Studio worker did not become idle")
        snapshot_process = subprocess.run(
            [*common, "snapshot", "--database", str(database), "--workspace-id", "alpha", "--json"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        snapshot = last_json(snapshot_process.stdout)
        receipt = {
            "configure": last_json(configured.stdout)["resultClass"],
            "runId": run_id,
            "runStatus": run["status"],
            "stepStatus": run["steps"][0]["status"],
            "childMarker": marker.read_text(encoding="utf-8"),
            "activeReservationsAfterTerminal": snapshot["value"]["activeReservations"],
            "availableBytesAfterTerminal": snapshot["value"]["availableBytes"],
            "availableSlotsAfterTerminal": snapshot["value"]["availableSlots"],
            "budgetDatabaseSha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        }
        del engine, store, coordinator
        gc.collect()
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0 if run["status"] == "COMPLETED" and snapshot["value"]["activeReservations"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
