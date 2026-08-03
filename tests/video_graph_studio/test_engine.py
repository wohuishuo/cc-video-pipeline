from pathlib import Path
import sys
import time


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import CommandAdapter  # noqa: E402
from studio.adapters import AdapterResult  # noqa: E402
from studio.contracts import GraphDefinition  # noqa: E402
from studio.engine import WorkflowEngine  # noqa: E402
from studio.store import CreateRun, RunStore  # noqa: E402


def graph_with_commands(commands: list[list[str]]) -> GraphDefinition:
    nodes = [
        {"id": f"step-{index}", "type": "command", "config": {"argv": command}}
        for index, command in enumerate(commands, 1)
    ]
    edges = [
        {
            "source": f"step-{index}",
            "target": f"step-{index + 1}",
            "relationship": "Fact",
        }
        for index in range(1, len(nodes))
    ]
    return GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "command-test",
            "revision": 1,
            "nodes": nodes,
            "edges": edges,
        }
    )


def create(store: RunStore, graph: GraphDefinition) -> str:
    return store.create_run(
        CreateRun("op-1", "corr-1", graph, {"sourceRoot": "C:/media"})
    ).value["runId"]


def wait_terminal(store: RunStore, run_id: str, timeout: float = 10) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = store.get_run(run_id)
        if run["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return run
        time.sleep(0.02)
    raise AssertionError(f"run {run_id} did not finish")


def test_real_process_nodes_finish_strictly_in_order(tmp_path):
    marker = tmp_path / "order.txt"
    first = [
        sys.executable,
        "-c",
        f"from pathlib import Path; import time; p=Path(r'{marker}'); p.write_text('one-start\\n'); time.sleep(.15); p.write_text(p.read_text()+'one-end\\n')",
    ]
    second = [
        sys.executable,
        "-c",
        f"from pathlib import Path; p=Path(r'{marker}'); p.write_text(p.read_text()+'two-start\\n')",
    ]
    store = RunStore(tmp_path / "studio.db")
    run_id = create(store, graph_with_commands([first, second]))
    adapter = CommandAdapter()
    engine = WorkflowEngine(store, {"command": adapter})

    assert engine.start(run_id).result_class == "COMPLETED"
    run = wait_terminal(store, run_id)

    assert run["status"] == "COMPLETED"
    assert marker.read_text().splitlines() == ["one-start", "one-end", "two-start"]
    assert adapter.maximum_active_processes == 1
    assert [step["status"] for step in run["steps"]] == ["COMPLETED", "COMPLETED"]


def test_failure_preserves_prior_checkpoint_and_stops_successors(tmp_path):
    marker = tmp_path / "order.txt"
    commands = [
        [sys.executable, "-c", f"from pathlib import Path; Path(r'{marker}').write_text('done')"],
        [sys.executable, "-c", "raise SystemExit(7)"],
        [sys.executable, "-c", f"from pathlib import Path; Path(r'{marker}').write_text('wrong')"],
    ]
    store = RunStore(tmp_path / "studio.db")
    run_id = create(store, graph_with_commands(commands))
    engine = WorkflowEngine(store, {"command": CommandAdapter()})

    engine.start(run_id)
    run = wait_terminal(store, run_id)

    assert run["status"] == "FAILED"
    assert [step["status"] for step in run["steps"]] == [
        "COMPLETED",
        "FAILED",
        "PENDING",
    ]
    assert marker.read_text() == "done"


def test_retry_runs_only_failed_and_pending_steps(tmp_path):
    graph = graph_with_commands([["one"], ["two"]])
    store = RunStore(tmp_path / "studio.db")
    run_id = create(store, graph)
    calls = []

    class OnceFailing:
        def execute(self, node, context, on_log, cancel_event):
            calls.append(node.id)
            if node.id == "step-2" and calls.count("step-2") == 1:
                return AdapterResult(False, {}, "temporary")
            return AdapterResult(True, {"node": node.id})

    engine = WorkflowEngine(store, {"command": OnceFailing()})
    engine.start(run_id)
    assert wait_terminal(store, run_id)["status"] == "FAILED"
    assert engine.retry(run_id).result_class == "COMPLETED"
    assert wait_terminal(store, run_id)["status"] == "COMPLETED"
    assert calls == ["step-1", "step-2", "step-2"]


def test_cancel_is_idempotent_and_stops_owned_process(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    run_id = create(
        store,
        graph_with_commands([[sys.executable, "-c", "import time; print('ready', flush=True); time.sleep(30)"]]),
    )
    adapter = CommandAdapter()
    engine = WorkflowEngine(store, {"command": adapter})
    engine.start(run_id)
    deadline = time.monotonic() + 5
    while "ready" not in [row["message"] for row in store.get_run(run_id)["logs"]]:
        assert time.monotonic() < deadline
        time.sleep(0.02)

    first = engine.cancel(run_id)
    run = wait_terminal(store, run_id)
    replay = engine.cancel(run_id)

    assert first.result_class == "COMPLETED"
    assert run["status"] == "CANCELLED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert adapter.active_processes == 0

