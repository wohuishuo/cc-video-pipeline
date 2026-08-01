from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.contracts import GraphDefinition  # noqa: E402
from studio.store import CreateRun, RunStore  # noqa: E402


GRAPH = GraphDefinition.from_dict(
    {
        "schemaVersion": 1,
        "graphId": "test-flow",
        "revision": 1,
        "nodes": [
            {"id": "source", "type": "prepared-folder", "config": {}},
            {"id": "render", "type": "edge-localize", "config": {}},
        ],
        "edges": [
            {"source": "source", "target": "render", "relationship": "Fact"}
        ],
    }
)


def command(operation_id: str, source: str = "C:/media") -> CreateRun:
    return CreateRun(
        operation_id=operation_id,
        correlation_id="corr-1",
        graph=GRAPH,
        parameters={"sourceRoot": source, "languages": ["ru-RU"]},
    )


def test_same_operation_and_input_returns_original_run(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    first = store.create_run(command("op-1"))
    replay = store.create_run(command("op-1"))
    assert first.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert replay.value["runId"] == first.value["runId"]


def test_same_operation_with_different_input_is_conflict(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    store.create_run(command("op-1"))
    conflict = store.create_run(command("op-1", source="C:/other"))
    assert conflict.result_class == "REJECTED_CONFLICT"


def test_transition_rejects_stale_version_and_terminal_replay_is_idempotent(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    run_id = store.create_run(command("op-1")).value["runId"]
    running = store.transition(run_id, expected_version=0, target="RUNNING")
    stale = store.transition(run_id, expected_version=0, target="FAILED")
    completed = store.transition(run_id, expected_version=1, target="COMPLETED")
    replay = store.transition(run_id, expected_version=2, target="COMPLETED")
    assert running.result_class == "COMPLETED"
    assert stale.result_class == "REJECTED_CONFLICT"
    assert completed.value["status"] == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert replay.value == completed.value


def test_steps_and_logs_keep_graph_and_append_order(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    run_id = store.create_run(command("op-1")).value["runId"]
    assert [step["nodeId"] for step in store.get_run(run_id)["steps"]] == [
        "source",
        "render",
    ]
    first = store.append_log(run_id, "first")
    second = store.append_log(run_id, "second")
    assert (first, second) == (1, 2)
    assert [row["message"] for row in store.get_run(run_id)["logs"]] == [
        "first",
        "second",
    ]

