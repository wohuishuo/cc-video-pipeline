import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
STUDIO = ROOT / "apps" / "video-graph-studio"
SELECTION = ROOT / "apps" / "creator-selection"
for app in (STUDIO, SELECTION):
    sys.path.insert(0, str(app))

from creator_selection.contracts import SelectionSpec
from creator_selection.operation import SelectionOperation
from studio.adapters import (
    AdapterResult,
    CommandAdapter,
    CreatorBatchAdapter,
    CreatorSelectionAdapter,
    VerifyCreatorSelectionAdapter,
)
from studio.api import CREATOR_GRAPHS, StudioApplication
from studio.engine import WorkflowEngine
from studio.server import build_runtime
from studio.store import CreateRun, RunStore


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _creator_manifest(tmp_path: Path, *, complete: bool = True, truncated: bool = False) -> Path:
    path = tmp_path / "creator-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "platform": "douyin",
                "requestedUrl": "https://www.douyin.com/user/creator",
                "creator": {"id": "creator", "name": "Creator"},
                "adapter": "fixture@1",
                "maxItems": 3,
                "complete": complete,
                "truncated": truncated,
                "items": [
                    {"ordinal": 1, "id": "v3", "url": "https://www.douyin.com/video/3", "title": "Three", "publishedAt": 3},
                    {"ordinal": 2, "id": "v2", "url": "https://www.douyin.com/video/2", "title": "Two", "publishedAt": 2},
                    {"ordinal": 3, "id": "v1", "url": "https://www.douyin.com/video/1", "title": "One", "publishedAt": 1},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _completed_creator_run(store: RunStore, manifest: Path) -> str:
    created = store.create_run(
        CreateRun("creator-op", "creator-corr", CREATOR_GRAPHS["creator-profile"], {"templateId": "creator-profile", "authenticationFile": None})
    )
    run_id = created.value["runId"]
    store.transition(run_id, expected_version=0, target="RUNNING")
    store.start_step(run_id, "discover-creator")
    store.complete_step(run_id, "discover-creator", {"manifest": str(manifest), "manifestSha256": _sha(manifest)})
    store.start_step(run_id, "verify-creator")
    store.complete_step(run_id, "verify-creator", {"verified": True})
    store.transition(run_id, expected_version=1, target="COMPLETED")
    return run_id


def _envelope(payload):
    return {
        "contractId": "CMD-RUN-CREATE",
        "contractVersion": "1.0",
        "operationId": "campaign-op",
        "correlationId": "campaign-corr",
        "payload": payload,
    }


def _payload(creator_run_id):
    return {
        "templateId": "creator-campaign",
        "creatorRunId": creator_run_id,
        "selectedVideoIds": ["v1", "v3"],
        "sourceLanguage": "zh",
        "asrModel": "small",
        "asrDevice": "cpu",
        "asrComputeType": "int8",
        "targetLanguages": ["ru-RU", "en-US"],
        "translationModel": "facebook/nllb-200-distilled-600M",
        "translationDevice": "cpu",
        "translationBatchSize": 4,
        "voiceProvider": "edge",
        "targetVoices": {"ru-RU": "ru-RU-DmitryNeural", "en-US": "en-US-GuyNeural"},
        "sourceVolume": 0.08,
        "destinationPlans": [
            {"locale": "ru-RU", "targets": [{"platform": "youtube", "account": "ru-main"}, {"platform": "tiktok", "account": "ru-short"}]},
            {"locale": "en-US", "targets": [{"platform": "youtube", "account": "en-main"}]},
        ],
    }


def test_creator_campaign_resolves_server_fact_and_creates_four_steps(tmp_path):
    manifest = _creator_manifest(tmp_path)
    store = RunStore(tmp_path / "studio.db")
    creator_run_id = _completed_creator_run(store, manifest)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle("POST", "/api/v1/runs", {}, _envelope(_payload(creator_run_id)))
    run = store.get_run(response["value"]["runId"])

    assert status == 201
    assert [node["type"] for node in run["graph"]["nodes"]] == [
        "select-creator-videos", "verify-selection", "localize-creator-batch", "verify-creator-batch"
    ]
    assert run["parameters"]["creatorManifestPath"] == str(manifest.resolve())
    assert run["parameters"]["creatorManifestSha256"] == _sha(manifest)
    assert run["parameters"]["selectedVideoIds"] == ["v3", "v1"]
    assert run["parameters"]["voiceProvider"] == "edge"
    assert run["parameters"]["destinationPlans"][0]["targets"][1] == {"platform": "tiktok", "account": "ru-short", "executionStatus": "PLAN_ONLY"}
    assert run["parameters"]["destinationPlans"][1]["targets"][0]["executionStatus"] == "READY_PRIVATE"


def test_creator_campaign_preserves_qwen_device_policy(tmp_path):
    manifest = _creator_manifest(tmp_path)
    store = RunStore(tmp_path / "studio.db")
    creator_run_id = _completed_creator_run(store, manifest)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))
    payload = _payload(creator_run_id)
    payload.update({
        "voiceProvider": "qwen3",
        "targetVoices": {"ru-RU": "Ryan", "en-US": "Aiden"},
        "qwenDevice": "cuda",
    })

    status, response = app.handle("POST", "/api/v1/runs", {}, _envelope(payload))
    run = store.get_run(response["value"]["runId"])

    assert status == 201
    assert run["parameters"]["qwenDevice"] == "cuda"


def test_creator_campaign_rejects_browser_artifact_paths_and_unknown_ids(tmp_path):
    manifest = _creator_manifest(tmp_path)
    store = RunStore(tmp_path / "studio.db")
    creator_run_id = _completed_creator_run(store, manifest)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))
    injected = _payload(creator_run_id)
    injected["creatorManifestPath"] = str(manifest)

    status, _ = app.handle("POST", "/api/v1/runs", {}, _envelope(injected))
    unknown = _payload(creator_run_id)
    unknown["selectedVideoIds"] = ["missing"]
    status_unknown, _ = app.handle("POST", "/api/v1/runs", {}, _envelope(unknown))

    assert status == 400
    assert status_unknown == 400
    assert len(store.list_runs()) == 1


def test_creator_campaign_rejects_an_incomplete_restored_catalog(tmp_path):
    manifest = _creator_manifest(tmp_path, complete=False, truncated=True)
    store = RunStore(tmp_path / "studio.db")
    creator_run_id = _completed_creator_run(store, manifest)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle(
        "POST", "/api/v1/runs", {}, _envelope(_payload(creator_run_id))
    )

    assert status == 400
    assert response["resultClass"] == "REJECTED_CONFLICT"
    assert "complete creator catalog" in response["detail"]
    assert len(store.list_runs()) == 1


def test_creator_campaign_accepts_an_explicit_partial_catalog_selection(tmp_path):
    manifest = _creator_manifest(tmp_path, complete=False, truncated=True)
    store = RunStore(tmp_path / "studio.db")
    creator_run_id = _completed_creator_run(store, manifest)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))
    payload = _payload(creator_run_id)
    payload["allowPartialCatalog"] = True

    status, response = app.handle(
        "POST", "/api/v1/runs", {}, _envelope(payload)
    )

    assert status == 201
    run = store.get_run(response["value"]["runId"])
    assert run["parameters"]["allowPartialCatalog"] is True
    assert run["parameters"]["selectedVideoIds"] == ["v3", "v1"]


def test_creator_campaign_accepts_local_delivery_without_publication_routes(tmp_path):
    manifest = _creator_manifest(tmp_path)
    store = RunStore(tmp_path / "studio.db")
    creator_run_id = _completed_creator_run(store, manifest)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))
    payload = _payload(creator_run_id)
    payload["destinationPlans"] = [
        {"locale": "ru-RU", "targets": []},
        {"locale": "en-US", "targets": []},
    ]
    payload["localOutputRoot"] = str(tmp_path / "exports")

    status, response = app.handle("POST", "/api/v1/runs", {}, _envelope(payload))
    run = store.get_run(response["value"]["runId"])

    assert status == 201
    assert run["parameters"]["destinationPlans"] == payload["destinationPlans"]
    assert run["parameters"]["localOutputRoot"] == str((tmp_path / "exports").resolve())


def test_selection_and_batch_adapters_use_only_the_selected_fact(tmp_path, monkeypatch):
    source = _creator_manifest(tmp_path)
    output_root = tmp_path / "selection-output"
    context = {
        "runId": "campaign-run",
        "parameters": {
            **_payload("creator-run"),
            "creatorManifestPath": str(source),
            "creatorManifestSha256": _sha(source),
            "selectedVideoIds": ["v3", "v1"],
            "authenticationFile": None,
        },
        "steps": [],
    }
    observed = []

    def fake_execute(self, node, current, on_log, cancel_event):
        observed.append(node.config["argv"])
        SelectionOperation().execute(
            SelectionSpec.load(source, ["v3", "v1"]),
            output_root / "campaign-run",
            "campaign-run:step:select-creator-videos",
        )
        return AdapterResult(True, {"exitCode": 0})

    monkeypatch.setattr(CommandAdapter, "execute", fake_execute)
    selected = CreatorSelectionAdapter(tmp_path / "select.ps1", output_root).execute(
        type("Node", (), {"id": "select-creator-videos"})(), context, lambda _line: None, None
    )
    context["steps"].append({"nodeId": "select-creator-videos", "status": "COMPLETED", "result": selected.details})
    verified = VerifyCreatorSelectionAdapter().execute(None, context, lambda _line: None, None)

    assert selected.completed and verified.completed
    assert observed[0].count("--video-id") == 2
    selection_manifest = Path(selected.details["manifest"])
    assert [row["id"] for row in json.loads(selection_manifest.read_text())["items"]] == ["v3", "v1"]

    def capture_batch(self, node, current, on_log, cancel_event):
        observed.append(node.config["argv"])
        return AdapterResult(False, {}, "stop after argv proof")

    monkeypatch.setattr(CommandAdapter, "execute", capture_batch)
    CreatorBatchAdapter(tmp_path / "batch.ps1", tmp_path / "batch-output").execute(
        type("Node", (), {"id": "localize-creator-batch"})(), context, lambda _line: None, None
    )
    assert str(selection_manifest.resolve()) in observed[-1]
    assert str(source.resolve()) not in observed[-1]


def test_runtime_registers_creator_campaign_owner_adapters(tmp_path):
    _, engine = build_runtime(ROOT, tmp_path / "runtime")

    assert isinstance(engine.adapters["select-creator-videos"], CreatorSelectionAdapter)
    assert isinstance(engine.adapters["verify-selection"], VerifyCreatorSelectionAdapter)
