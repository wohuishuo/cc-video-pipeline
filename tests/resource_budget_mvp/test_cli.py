import json
import os
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "resource-budget"


def command(*arguments):
    return [sys.executable, "-m", "resource_budget.cli", *map(str, arguments)]


def environment():
    return {**os.environ, "PYTHONPATH": str(APP), "PYTHONUTF8": "1"}


def run_cli(*arguments):
    return subprocess.run(
        command(*arguments),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment(),
    )


def test_cli_configure_reserve_snapshot_release_lifecycle(tmp_path):
    database = tmp_path / "budget.db"
    configured = run_cli(
        "configure", "--database", database, "--workspace-id", "alpha",
        "--byte-limit", 100, "--execution-slots", 1, "--json",
    )
    reserved = run_cli(
        "reserve", "--database", database, "--workspace-id", "alpha",
        "--reservation-id", "run-one", "--bytes", 60, "--slots", 1,
        "--ttl-seconds", 30, "--json",
    )
    snapshot = run_cli(
        "snapshot", "--database", database, "--workspace-id", "alpha", "--json",
    )
    released = run_cli(
        "release", "--database", database, "--workspace-id", "alpha",
        "--reservation-id", "run-one", "--expected-generation", 1, "--json",
    )

    assert configured.returncode == reserved.returncode == snapshot.returncode == released.returncode == 0
    assert json.loads(reserved.stdout)["value"]["generation"] == 1
    assert json.loads(snapshot.stdout)["value"]["availableSlots"] == 0
    assert json.loads(released.stdout)["value"]["status"] == "RELEASED"


def test_two_real_processes_cannot_oversubscribe_one_slot(tmp_path):
    database = tmp_path / "budget.db"
    assert run_cli(
        "configure", "--database", database, "--workspace-id", "alpha",
        "--byte-limit", 100, "--execution-slots", 1, "--json",
    ).returncode == 0
    common = (
        "--database", database, "--workspace-id", "alpha", "--bytes", 100,
        "--slots", 1, "--ttl-seconds", 30, "--json",
    )
    processes = [
        subprocess.Popen(
            command("reserve", *common, "--reservation-id", reservation_id),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=environment(),
        )
        for reservation_id in ("run-one", "run-two")
    ]
    completed = [process.communicate(timeout=20) + (process.returncode,) for process in processes]
    payloads = [json.loads(stdout) for stdout, _, _ in completed]

    assert sorted(item["resultClass"] for item in payloads) == ["COMPLETED", "REJECTED_BUDGET"]
    assert sorted(code for _, _, code in completed) == [0, 3]
    snapshot = json.loads(run_cli(
        "snapshot", "--database", database, "--workspace-id", "alpha", "--json",
    ).stdout)
    assert snapshot["value"]["activeReservations"] == 1
    assert snapshot["value"]["reservedSlots"] == 1
