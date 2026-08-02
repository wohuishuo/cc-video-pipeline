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
