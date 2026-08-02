import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import (
    AdapterResult,
    CommandAdapter,
    PublicationBatchPlanAdapter,
    VerifyPublicationBatchPlanAdapter,
)
from studio.api import StudioApplication
from studio.engine import WorkflowEngine
from studio.server import build_runtime
from studio.store import RunStore


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def envelope(payload, operation_id="release-op"):
    return {
        "contractId": "CMD-RUN-CREATE",
        "contractVersion": "1.0",
        "operationId": operation_id,
        "correlationId": "release-corr",
        "payload": payload,
    }


def release_payload(source: Path, metadata: Path, template_id="folder-release"):
    value = {
        "templateId": template_id,
        "sourceLanguage": "zh",
        "asrModel": "small",
        "asrDevice": "cpu",
        "asrComputeType": "int8",
        "targetLanguages": ["ru-RU", "en-US"],
        "translationModel": "facebook/nllb-200-distilled-600M",
        "translationDevice": "cpu",
        "translationBatchSize": 4,
        "targetVoices": {"ru-RU": "ru-RU-DmitryNeural", "en-US": "en-US-GuyNeural"},
        "sourceVolume": 0.08,
        "metadataTemplatePath": str(metadata),
        "targetPlatforms": ["youtube", "tiktok"],
        "targetAccounts": {"youtube": "primary", "tiktok": "brand"},
        "credentialIds": {"youtube": "youtube-main"},
        "public": False,
    }
    if template_id.startswith("folder-"):
        value["sourceRoot"] = str(source)
    else:
        value["sourceUrl"] = "https://www.youtube.com/watch?v=abcdefghijk"
    return value


def test_folder_release_graph_has_twelve_owner_steps_and_publication_policy(tmp_path):
    source = tmp_path / "media"
    source.mkdir()
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"{filename} [{language}]"}', encoding="utf-8")
    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle("POST", "/api/v1/runs", {}, envelope(release_payload(source, metadata)))
    run = store.get_run(response["value"]["runId"])

    assert status == 201
    assert run["graph"]["graphId"] == "folder-release"
    assert [node["id"] for node in run["graph"]["nodes"]][-2:] == [
        "plan-publication-batch",
        "verify-publication-batch",
    ]
    assert len(run["graph"]["nodes"]) == 12
    assert run["parameters"]["metadataTemplatePath"] == str(metadata.resolve())
    assert run["parameters"]["targetPlatforms"] == ["youtube", "tiktok"]
    assert run["parameters"]["targetAccounts"] == {"youtube": "primary", "tiktok": "brand"}
    assert run["parameters"]["credentialIds"] == {"youtube": "youtube-main"}
    assert run["parameters"]["public"] is False


def test_url_release_graph_reuses_localization_steps_before_batch_planning(tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"Title"}', encoding="utf-8")
    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle(
        "POST", "/api/v1/runs", {}, envelope(release_payload(tmp_path, metadata, "url-release"), "url-release-op")
    )
    run = store.get_run(response["value"]["runId"])

    assert status == 201
    assert run["graph"]["nodes"][0]["config"] == {"mode": "url"}
    assert [node["type"] for node in run["graph"]["nodes"]][-4:] == [
        "localize-video",
        "verify-localization",
        "plan-publication-batch",
        "verify-publication-batch",
    ]


def test_release_admission_rejects_missing_or_unsafe_publication_policy(tmp_path):
    source = tmp_path / "media"
    source.mkdir()
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"Title"}', encoding="utf-8")
    invalid_changes = [
        {"metadataTemplatePath": str(tmp_path / "missing.json")},
        {"targetPlatforms": []},
        {"targetPlatforms": ["unknown"], "targetAccounts": {"unknown": "main"}},
        {"targetPlatforms": ["youtube", "youtube"], "targetAccounts": {"youtube": "main"}},
        {"targetAccounts": {"youtube": "main"}},
        {"credentialIds": {"bilibili": "missing-target"}},
        {"credentialIds": {"youtube": "../secret"}},
        {"public": True},
    ]
    for ordinal, change in enumerate(invalid_changes, 1):
        store = RunStore(tmp_path / f"studio-{ordinal}.db")
        app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))
        payload = release_payload(source, metadata)
        payload.update(change)

        status, _response = app.handle("POST", "/api/v1/runs", {}, envelope(payload, f"invalid-{ordinal}"))

        assert status == 400
        assert store.list_runs() == []


def write_adapter_evidence(tmp_path: Path, output_root: Path):
    video = tmp_path / "localized.mp4"
    video.write_bytes(b"localized")
    localization = tmp_path / "localization-manifest.json"
    localization.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "targetLanguages": ["ru-RU"],
                "expectedMediaIds": ["m1"],
                "derivatives": [
                    {
                        "targetLanguage": "ru-RU",
                        "mediaId": "m1",
                        "path": str(video),
                        "sha256": digest(video),
                        "size": video.stat().st_size,
                        "duration": 2.0,
                        "width": 1080,
                        "height": 1920,
                        "videoCodec": "h264",
                        "audioCodec": "aac",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    metadata_template = tmp_path / "metadata-template.json"
    metadata_template.write_text('{"title":"{filename} [{language}]"}', encoding="utf-8")
    item_root = output_root / "run-1" / "items" / "0001-item"
    item_root.mkdir(parents=True)
    metadata = item_root / "metadata.json"
    metadata.write_text('{"title":"localized [ru-RU]"}', encoding="utf-8")
    plan = item_root / "publication-plan.json"
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "video": {"path": str(video), "sha256": digest(video), "size": video.stat().st_size},
                "metadata": {"path": str(metadata), "sha256": digest(metadata), "title": "localized [ru-RU]"},
                "public": False,
                "jobs": [
                    {
                        "ordinal": 1,
                        "id": "1" * 64,
                        "platform": "youtube",
                        "account": "primary",
                        "visibility": "private-or-draft",
                        "credentialId": "youtube-main",
                    },
                    {
                        "ordinal": 2,
                        "id": "2" * 64,
                        "platform": "tiktok",
                        "account": "brand",
                        "visibility": "private-or-draft",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    aggregate = output_root / "run-1" / "publication-batch-plan.json"
    aggregate.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "localizationManifest": str(localization),
                "localizationManifestSha256": digest(localization),
                "metadataTemplate": str(metadata_template),
                "metadataTemplateSha256": digest(metadata_template),
                "targetLanguages": ["ru-RU"],
                "expectedMediaIds": ["m1"],
                "targets": [
                    {"platform": "youtube", "account": "primary", "credentialId": "youtube-main"},
                    {"platform": "tiktok", "account": "brand"},
                ],
                "public": False,
                "maximumActiveItems": 1,
                "expectedDerivativeKeys": ["ru-RU:m1"],
                "items": [
                    {
                        "ordinal": 1,
                        "targetLanguage": "ru-RU",
                        "mediaId": "m1",
                        "derivativePath": str(video),
                        "derivativeSha256": digest(video),
                        "metadataPath": str(metadata),
                        "metadataSha256": digest(metadata),
                        "publicationPlan": str(plan),
                        "publicationPlanSha256": digest(plan),
                        "jobCount": 2,
                    }
                ],
                "totalJobCount": 2,
            }
        ),
        encoding="utf-8",
    )
    receipt = aggregate.parent / "publication-batch-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "operationId": "run-1:step:plan-publication-batch",
                "resultClass": "COMPLETED",
                "manifest": str(aggregate),
                "manifestSha256": digest(aggregate),
                "itemCount": 1,
                "completedCount": 1,
            }
        ),
        encoding="utf-8",
    )
    return localization, metadata_template, aggregate, video


def test_batch_adapters_consume_committed_localization_and_verify_all_child_plans(tmp_path, monkeypatch):
    output_root = tmp_path / "batch-plans"
    localization, metadata, aggregate, video = write_adapter_evidence(tmp_path, output_root)
    seen = {}

    def fake_execute(self, node, context, on_log, cancel_event):
        seen["argv"] = node.config["argv"]
        return AdapterResult(True, {"exitCode": 0})

    monkeypatch.setattr(CommandAdapter, "execute", fake_execute)
    context = {
        "runId": "run-1",
        "parameters": {
            "metadataTemplatePath": str(metadata),
            "targetPlatforms": ["youtube", "tiktok"],
            "targetAccounts": {"youtube": "primary", "tiktok": "brand"},
            "credentialIds": {"youtube": "youtube-main"},
            "public": False,
        },
        "steps": [
            {
                "nodeId": "localize-video",
                "status": "COMPLETED",
                "result": {"manifest": str(localization), "manifestSha256": digest(localization)},
            }
        ],
    }

    planned = PublicationBatchPlanAdapter(tmp_path / "publication-batch.ps1", output_root).execute(
        type("Node", (), {"id": "plan-publication-batch"})(), context, lambda _line: None, None
    )
    context["steps"].append(
        {"nodeId": "plan-publication-batch", "status": "COMPLETED", "result": planned.details}
    )
    verified = VerifyPublicationBatchPlanAdapter().execute(None, context, lambda _line: None, None)

    assert planned.completed and verified.completed
    assert str(localization.resolve()) in seen["argv"]
    assert str(metadata.resolve()) in seen["argv"]
    assert seen["argv"].count("--target") == 2
    assert seen["argv"].count("--credential") == 1
    assert "--public" not in seen["argv"]
    assert planned.details["manifest"] == str(aggregate.resolve())
    assert verified.details == {
        "manifest": str(aggregate.resolve()),
        "itemCount": 1,
        "jobCount": 2,
    }

    video.write_bytes(b"changed")
    assert not VerifyPublicationBatchPlanAdapter().execute(None, context, lambda _line: None, None).completed


def test_runtime_registers_publication_batch_adapters(tmp_path):
    _, engine = build_runtime(Path(__file__).resolve().parents[2], tmp_path / "runtime")

    assert isinstance(engine.adapters["plan-publication-batch"], PublicationBatchPlanAdapter)
    assert isinstance(engine.adapters["verify-publication-batch"], VerifyPublicationBatchPlanAdapter)
