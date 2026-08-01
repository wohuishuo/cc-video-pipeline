from pathlib import Path
import json
import sys
import time


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult, SourceIntakeAdapter, VerifySourceAdapter  # noqa: E402
from studio.api import StudioApplication  # noqa: E402
from studio.engine import WorkflowEngine  # noqa: E402
from studio.store import RunStore  # noqa: E402
from studio.server import build_runtime  # noqa: E402


class NoopAdapter:
    def execute(self, node, context, on_log, cancel_event):
        return AdapterResult(True, {"node": node.id})


def app(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    adapter = NoopAdapter()
    engine = WorkflowEngine(store, {"source-intake": adapter, "verify-source": adapter})
    return StudioApplication(store, engine, allowed_roots=(tmp_path,)), store


def envelope(payload):
    return {
        "contractId": "CMD-RUN-CREATE",
        "contractVersion": "1.0",
        "operationId": "op-1",
        "correlationId": "corr-1",
        "payload": payload,
    }


def test_folder_intake_template_admits_local_source_graph(tmp_path):
    application, store = app(tmp_path)
    source = tmp_path / "media"
    source.mkdir()
    status, response = application.handle(
        "POST",
        "/api/v1/runs",
        {},
        envelope({"templateId": "folder-intake", "sourceRoot": str(source)}),
    )
    run = store.get_run(response["value"]["runId"])
    assert status == 201
    assert run["graph"]["graphId"] == "folder-intake"
    assert [node["type"] for node in run["graph"]["nodes"]] == [
        "source-intake",
        "verify-source",
    ]
    assert run["parameters"]["sourceKind"] == "folder"


def test_url_intake_template_admits_supported_social_url_without_path_check(tmp_path):
    application, store = app(tmp_path)
    status, response = application.handle(
        "POST",
        "/api/v1/runs",
        {},
        envelope({"templateId": "url-intake", "sourceUrl": "https://v.douyin.com/abc"}),
    )
    run = store.get_run(response["value"]["runId"])
    assert status == 201
    assert run["graph"]["graphId"] == "url-intake"
    assert run["parameters"]["sourceKind"] == "url"
    assert run["parameters"]["sourceUrl"] == "https://v.douyin.com/abc"


def test_unknown_template_is_rejected_without_creating_run(tmp_path):
    application, store = app(tmp_path)
    status, response = application.handle(
        "POST",
        "/api/v1/runs",
        {},
        envelope({"templateId": "magic", "sourceRoot": str(tmp_path)}),
    )
    assert status == 400
    assert response["resultClass"] == "REJECTED_MALFORMED"
    assert store.list_runs() == []


def test_real_source_intake_cli_composes_through_graph_checkpoints(tmp_path):
    source = tmp_path / "media"
    source.mkdir()
    (source / "clip.mp4").write_bytes(b"video")
    store = RunStore(tmp_path / "studio.db")
    launcher = Path(__file__).resolve().parents[2] / "apps" / "source-intake" / "run.ps1"
    engine = WorkflowEngine(
        store,
        {
            "source-intake": SourceIntakeAdapter(launcher, tmp_path / "intakes"),
            "verify-source": VerifySourceAdapter(),
        },
    )
    application = StudioApplication(store, engine, allowed_roots=(tmp_path,))
    _, created = application.handle(
        "POST",
        "/api/v1/runs",
        {},
        envelope({"templateId": "folder-intake", "sourceRoot": str(source)}),
    )
    run_id = created["value"]["runId"]
    status, _ = application.handle(
        "POST",
        f"/api/v1/runs/{run_id}/start",
        {},
        {
            "contractId": "CMD-RUN-START",
            "contractVersion": "1.0",
            "operationId": "start-1",
            "correlationId": "corr-1",
            "payload": {},
        },
    )
    deadline = time.monotonic() + 10
    while store.get_run(run_id)["status"] not in {"COMPLETED", "FAILED"}:
        assert time.monotonic() < deadline
        time.sleep(0.03)
    run = store.get_run(run_id)
    intake = run["steps"][0]["result"]
    assert status == 202
    assert run["status"] == "COMPLETED"
    assert Path(intake["manifest"]).is_file()
    assert json.loads(Path(intake["manifest"]).read_text(encoding="utf-8"))["media"][0]["size"] == 5


def test_production_runtime_registers_intake_owner_adapters(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    _, engine = build_runtime(repository, tmp_path / "runtime")
    assert isinstance(engine.adapters["source-intake"], SourceIntakeAdapter)
    assert isinstance(engine.adapters["verify-source"], VerifySourceAdapter)
