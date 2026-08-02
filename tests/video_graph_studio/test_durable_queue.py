from pathlib import Path
import sys
import threading
import time


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult
from studio.contracts import GraphDefinition
from studio.engine import WorkflowEngine
from studio.store import CreateRun, RunStore


GRAPH = GraphDefinition.from_dict(
    {
        "schemaVersion": 1,
        "graphId": "queued-work",
        "revision": 1,
        "nodes": [{"id": "work", "type": "work", "config": {}}],
        "edges": [],
    }
)


def create_run(store: RunStore, operation_id: str) -> str:
    return store.create_run(
        CreateRun(operation_id, f"corr-{operation_id}", GRAPH, {})
    ).value["runId"]


def wait_terminal(store: RunStore, run_id: str, timeout: float = 5) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = store.get_run(run_id)
        if run["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return run
        time.sleep(0.01)
    raise AssertionError(f"run {run_id} did not finish")


def test_queue_is_fifo_idempotent_and_recovers_abandoned_claim(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    first = create_run(store, "first")
    second = create_run(store, "second")

    assert store.enqueue_run(first).result_class == "COMPLETED"
    replay = store.enqueue_run(first)
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert store.enqueue_run(second).result_class == "COMPLETED"
    assert [entry["runId"] for entry in store.queue_snapshot()["entries"]] == [
        first,
        second,
    ]

    assert store.claim_next_run() == first
    assert store.queue_snapshot()["activeRunId"] == first
    assert store.recover_queue() == 1
    assert store.claim_next_run() == first
    store.finish_queue_entry(first)
    assert store.claim_next_run() == second
    store.finish_queue_entry(second)
    assert store.claim_next_run() is None
    assert store.queue_snapshot()["queuedRuns"] == 0


class BlockingAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.first_started = threading.Event()
        self.release_first = threading.Event()
        self.active = 0
        self.maximum_active = 0
        self._lock = threading.Lock()

    def execute(self, node, context, on_log, cancel_event) -> AdapterResult:
        run_id = context["runId"]
        with self._lock:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            self.calls.append(f"start:{run_id}")
        if len(self.calls) == 1:
            self.first_started.set()
            assert self.release_first.wait(timeout=5)
        with self._lock:
            self.calls.append(f"end:{run_id}")
            self.active -= 1
        return AdapterResult(True, {"runId": run_id})


def test_engine_accepts_multiple_runs_and_drains_them_strictly_serially(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    first = create_run(store, "first")
    second = create_run(store, "second")
    adapter = BlockingAdapter()
    engine = WorkflowEngine(store, {"work": adapter})

    assert engine.start(first).result_class == "COMPLETED"
    assert adapter.first_started.wait(timeout=5)
    assert engine.start(second).result_class == "COMPLETED"
    assert store.get_run(second)["status"] == "CREATED"
    assert store.queue_snapshot()["queuedRuns"] == 1

    adapter.release_first.set()
    assert wait_terminal(store, first)["status"] == "COMPLETED"
    assert wait_terminal(store, second)["status"] == "COMPLETED"
    assert adapter.maximum_active == 1
    assert adapter.calls == [
        f"start:{first}",
        f"end:{first}",
        f"start:{second}",
        f"end:{second}",
    ]


def test_new_engine_resumes_durable_start_requests_after_restart(tmp_path):
    database = tmp_path / "studio.db"
    store = RunStore(database)
    first = create_run(store, "first")
    second = create_run(store, "second")
    store.enqueue_run(first)
    store.enqueue_run(second)
    assert store.claim_next_run() == first

    restarted = RunStore(database)
    assert restarted.recover_queue() == 1
    adapter = BlockingAdapter()
    adapter.release_first.set()
    engine = WorkflowEngine(restarted, {"work": adapter})
    engine.resume_pending()

    assert wait_terminal(restarted, first)["status"] == "COMPLETED"
    assert wait_terminal(restarted, second)["status"] == "COMPLETED"
    assert restarted.queue_snapshot()["queuedRuns"] == 0
    assert adapter.maximum_active == 1


def test_cancelling_a_queued_run_does_not_cancel_the_active_run(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    first = create_run(store, "first")
    second = create_run(store, "second")
    adapter = BlockingAdapter()
    engine = WorkflowEngine(store, {"work": adapter})

    engine.start(first)
    assert adapter.first_started.wait(timeout=5)
    engine.start(second)
    cancelled = engine.cancel(second)

    assert cancelled.result_class == "COMPLETED"
    assert store.get_run(second)["status"] == "CANCELLED"
    assert store.get_run(first)["status"] == "RUNNING"
    adapter.release_first.set()
    assert wait_terminal(store, first)["status"] == "COMPLETED"
    assert adapter.calls == [f"start:{first}", f"end:{first}"]


class FakeLease:
    def __init__(self, events, fail_on_start=False):
        self.events = events
        self.fail_on_start = fail_on_start

    def start(self, on_failure):
        self.events.append("lease-start")
        if self.fail_on_start:
            on_failure("lease heartbeat failed")

    def close(self):
        self.events.append("lease-close")


class FakeLeaseCoordinator:
    def __init__(self, denials=0, fail_on_start=False):
        self.denials = denials
        self.fail_on_start = fail_on_start
        self.calls = []

    def acquire(self, run_id):
        self.calls.append(run_id)
        if self.denials:
            self.denials -= 1
            from studio.resource_leases import ResourceLeaseUnavailable
            raise ResourceLeaseUnavailable("REJECTED_BUDGET", "capacity unavailable")
        return FakeLease(self.calls, self.fail_on_start)


class OrderedAdapter:
    def __init__(self, events):
        self.events = events

    def execute(self, node, context, on_log, cancel_event):
        self.events.append("adapter")
        return AdapterResult(True, {})


class FailingAdapter:
    def execute(self, node, context, on_log, cancel_event):
        return AdapterResult(False, {}, "deliberate failure")


def test_engine_acquires_before_running_and_releases_after_completion(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    run_id = create_run(store, "leased")
    coordinator = FakeLeaseCoordinator()
    engine = WorkflowEngine(
        store, {"work": OrderedAdapter(coordinator.calls)}, lease_coordinator=coordinator
    )

    engine.start(run_id)
    assert wait_terminal(store, run_id)["status"] == "COMPLETED"
    assert coordinator.calls == [run_id, "lease-start", "adapter", "lease-close"]


def test_budget_denial_requeues_same_run_then_completes_without_false_failure(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    run_id = create_run(store, "wait-budget")
    coordinator = FakeLeaseCoordinator(denials=1)
    engine = WorkflowEngine(
        store,
        {"work": OrderedAdapter(coordinator.calls)},
        lease_coordinator=coordinator,
        resource_retry_seconds=0.01,
    )

    engine.start(run_id)
    run = wait_terminal(store, run_id)

    assert run["status"] == "COMPLETED"
    assert coordinator.calls.count(run_id) == 2
    assert any("resource wait" in item["message"] for item in run["logs"])


def test_lease_heartbeat_failure_fences_workflow_completion(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    run_id = create_run(store, "lost-lease")
    coordinator = FakeLeaseCoordinator(fail_on_start=True)
    engine = WorkflowEngine(
        store, {"work": OrderedAdapter(coordinator.calls)}, lease_coordinator=coordinator
    )

    engine.start(run_id)
    run = wait_terminal(store, run_id)

    assert run["status"] == "FAILED"
    assert "adapter" not in coordinator.calls
    assert coordinator.calls[-1] == "lease-close"


def test_failed_workflow_also_closes_resource_lease(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    run_id = create_run(store, "failed-lease")
    coordinator = FakeLeaseCoordinator()
    engine = WorkflowEngine(
        store, {"work": FailingAdapter()}, lease_coordinator=coordinator
    )

    engine.start(run_id)
    assert wait_terminal(store, run_id)["status"] == "FAILED"
    assert coordinator.calls[-1] == "lease-close"


def test_cancelled_workflow_also_closes_resource_lease(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    run_id = create_run(store, "cancelled-lease")
    adapter = BlockingAdapter()
    coordinator = FakeLeaseCoordinator()
    engine = WorkflowEngine(
        store, {"work": adapter}, lease_coordinator=coordinator
    )

    engine.start(run_id)
    assert adapter.first_started.wait(timeout=5)
    assert engine.cancel(run_id).result_class == "COMPLETED"
    adapter.release_first.set()

    assert wait_terminal(store, run_id)["status"] == "CANCELLED"
    assert engine.wait_idle(5)
    assert coordinator.calls[-1] == "lease-close"
