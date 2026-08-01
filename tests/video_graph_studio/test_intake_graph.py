from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult  # noqa: E402
from studio.api import StudioApplication  # noqa: E402
from studio.engine import WorkflowEngine  # noqa: E402
from studio.store import RunStore  # noqa: E402


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

