from pathlib import Path
import json
import subprocess
import sys
import threading


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.resource_leases import (  # noqa: E402
    ResourceBudgetCommandAdapter,
    ResourceLeaseCoordinator,
    ResourceLeaseUnavailable,
)


class FakeBudgetCommands:
    def __init__(self):
        self.calls = []
        self.generation = 1
        self.descriptions = {}

    def reserve(self, workspace_id, reservation_id, bytes_requested, slots, ttl_seconds):
        self.calls.append(("reserve", workspace_id, reservation_id, bytes_requested, slots, ttl_seconds))
        return {"resultClass": "COMPLETED", "value": {"generation": self.generation, "status": "ACTIVE"}}

    def renew(self, workspace_id, reservation_id, expected_generation, ttl_seconds):
        self.calls.append(("renew", workspace_id, reservation_id, expected_generation, ttl_seconds))
        self.generation += 1
        return {"resultClass": "COMPLETED", "value": {"generation": self.generation, "status": "ACTIVE"}}

    def release(self, workspace_id, reservation_id, expected_generation):
        self.calls.append(("release", workspace_id, reservation_id, expected_generation))
        return {"resultClass": "COMPLETED", "value": {"generation": expected_generation, "status": "RELEASED"}}

    def describe(self, workspace_id, reservation_id):
        self.calls.append(("describe", workspace_id, reservation_id))
        return self.descriptions.get(reservation_id, {"resultClass": "REJECTED_NOT_FOUND", "value": {}})


def test_coordinator_uses_stable_identity_and_releases_current_generation():
    commands = FakeBudgetCommands()
    coordinator = ResourceLeaseCoordinator(
        commands, workspace_id="alpha", bytes_per_run=4096, ttl_seconds=30
    )

    lease = coordinator.acquire("12345678-1234-1234-1234-123456789abc")
    lease.renew_once()
    lease.close()

    reservation_id = "studio-12345678-1234-1234-1234-123456789abc"
    assert commands.calls == [
        ("reserve", "alpha", reservation_id, 4096, 1, 30),
        ("renew", "alpha", reservation_id, 1, 30),
        ("release", "alpha", reservation_id, 2),
    ]


def test_background_heartbeat_renews_until_lease_is_closed():
    commands = FakeBudgetCommands()
    renewed = threading.Event()
    original = commands.renew

    def renew(*arguments):
        result = original(*arguments)
        renewed.set()
        return result

    commands.renew = renew
    coordinator = ResourceLeaseCoordinator(
        commands, workspace_id="alpha", bytes_per_run=1, ttl_seconds=3
    )
    lease = coordinator.acquire("12345678-1234-1234-1234-123456789abc")

    lease.start(lambda detail: None)
    assert renewed.wait(timeout=2.5)
    lease.close()

    assert [call[0] for call in commands.calls] == ["reserve", "renew", "release"]


def test_coordinator_surfaces_budget_denial_without_claiming_success():
    commands = FakeBudgetCommands()
    commands.reserve = lambda *args: {"resultClass": "REJECTED_BUDGET", "value": {"availableSlots": 0}}
    coordinator = ResourceLeaseCoordinator(commands, workspace_id="alpha", bytes_per_run=1, ttl_seconds=30)

    try:
        coordinator.acquire("12345678-1234-1234-1234-123456789abc")
    except ResourceLeaseUnavailable as error:
        assert error.result_class == "REJECTED_BUDGET"
    else:
        raise AssertionError("budget denial was accepted")


def test_startup_reconciliation_releases_only_terminal_active_run_leases():
    commands = FakeBudgetCommands()
    terminal_id = "studio-12345678-1234-1234-1234-123456789abc"
    queued_id = "studio-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    commands.descriptions = {
        terminal_id: {"resultClass": "COMPLETED", "value": {"status": "ACTIVE", "generation": 4}},
        queued_id: {"resultClass": "COMPLETED", "value": {"status": "ACTIVE", "generation": 2}},
    }
    coordinator = ResourceLeaseCoordinator(commands, workspace_id="alpha", bytes_per_run=1, ttl_seconds=30)

    coordinator.reconcile([
        {"runId": terminal_id.removeprefix("studio-"), "status": "COMPLETED"},
        {"runId": queued_id.removeprefix("studio-"), "status": "INTERRUPTED"},
    ])

    assert ("release", "alpha", terminal_id, 4) in commands.calls
    assert not any(call[0] == "release" and call[2] == queued_id for call in commands.calls)


def test_public_command_adapter_parses_last_json_line_and_redacts_failures(tmp_path, monkeypatch):
    class Completed:
        returncode = 0
        stdout = "diagnostic\n{\"resultClass\":\"COMPLETED\",\"value\":{\"generation\":1}}\n"
        stderr = ""

    monkeypatch.setattr("studio.resource_leases.subprocess.run", lambda *args, **kwargs: Completed())
    adapter = ResourceBudgetCommandAdapter(tmp_path / "run.ps1", tmp_path / "budget.db")

    assert adapter.reserve("alpha", "studio-run", 1, 1, 30)["resultClass"] == "COMPLETED"


def test_real_public_launcher_reserves_renews_and_releases(tmp_path):
    root = Path(__file__).resolve().parents[2]
    launcher = root / "apps" / "resource-budget" / "run.ps1"
    database = tmp_path / "budget.db"
    configured = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(launcher), "configure", "--database", str(database),
            "--workspace-id", "alpha", "--byte-limit", "100",
            "--execution-slots", "1", "--json",
        ],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert configured.returncode == 0
    commands = ResourceBudgetCommandAdapter(launcher, database)
    coordinator = ResourceLeaseCoordinator(
        commands, workspace_id="alpha", bytes_per_run=100, ttl_seconds=3
    )

    lease = coordinator.acquire("12345678-1234-1234-1234-123456789abc")
    lease.renew_once()
    lease.close()

    snapshot = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(launcher), "snapshot", "--database", str(database),
            "--workspace-id", "alpha", "--json",
        ],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    payload = json.loads([line for line in snapshot.stdout.splitlines() if line.strip()][-1])
    assert payload["value"]["activeReservations"] == 0
    assert payload["value"]["availableBytes"] == 100
