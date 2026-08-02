from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult
from studio.contracts import GraphDefinition
from studio.engine import WorkflowEngine
from studio.store import CreateRun, RunStore


GRAPH = GraphDefinition.from_dict(
    {
        "schemaVersion": 1,
        "graphId": "recovery",
        "revision": 1,
        "nodes": [
            {"id": "first", "type": "one", "config": {}},
            {"id": "second", "type": "two", "config": {}},
        ],
        "edges": [
            {"source": "first", "target": "second", "relationship": "Fact"}
        ],
    }
)


class RecordingAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, node, context, on_log, cancel_event) -> AdapterResult:
        self.calls.append(node.id)
        return AdapterResult(True, {"node": node.id})


def test_new_server_generation_fences_and_resumes_first_missing_checkpoint(tmp_path):
    database = tmp_path / "studio.db"
    store = RunStore(database)
    created = store.create_run(CreateRun("op", "corr", GRAPH, {}))
    run_id = created.value["runId"]
    run = store.get_run(run_id)
    store.transition(run_id, expected_version=run["version"], target="RUNNING")
    store.start_step(run_id, "first")
    store.complete_step(run_id, "first", {"committed": True})
    store.start_step(run_id, "second")

    restarted = RunStore(database)
    assert restarted.interrupt_active() == 1
    interrupted = restarted.get_run(run_id)
    assert interrupted["status"] == "INTERRUPTED"
    assert [step["status"] for step in interrupted["steps"]] == [
        "COMPLETED",
        "INTERRUPTED",
    ]
    assert restarted.interrupt_active() == 0

    first = RecordingAdapter()
    second = RecordingAdapter()
    engine = WorkflowEngine(restarted, {"one": first, "two": second})
    assert engine.start(run_id).result_class == "COMPLETED"
    assert engine._thread is not None
    engine._thread.join(timeout=5)

    recovered = restarted.get_run(run_id)
    assert recovered["status"] == "COMPLETED"
    assert first.calls == []
    assert second.calls == ["second"]
    assert recovered["steps"][0]["result"] == {"committed": True}


def test_completed_run_is_not_changed_by_restart_fence(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    graph = GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "one",
            "revision": 1,
            "nodes": [{"id": "only", "type": "one", "config": {}}],
            "edges": [],
        }
    )
    created = store.create_run(CreateRun("op", "corr", graph, {}))
    run_id = created.value["runId"]
    adapter = RecordingAdapter()
    engine = WorkflowEngine(store, {"one": adapter})
    engine.start(run_id)
    assert engine._thread is not None
    engine._thread.join(timeout=5)
    before = store.get_run(run_id)

    assert RunStore(tmp_path / "studio.db").interrupt_active() == 0
    after = store.get_run(run_id)
    assert after["status"] == "COMPLETED"
    assert after["version"] == before["version"]
