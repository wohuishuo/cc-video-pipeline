import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult, CommandAdapter, CreatorBatchAdapter, VerifyCreatorBatchAdapter
from studio.api import StudioApplication
from studio.engine import WorkflowEngine
from studio.server import build_runtime
from studio.store import RunStore


def envelope(payload):
    return {
        "contractId": "CMD-RUN-CREATE",
        "contractVersion": "1.0",
        "operationId": "creator-batch-op",
        "correlationId": "creator-batch-corr",
        "payload": payload,
    }


def payload(cookie):
    return {
        "templateId": "creator-batch-dub",
        "sourceUrl": "https://www.douyin.com/user/creator",
        "maxItems": 74,
        "authenticationFile": str(cookie),
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
    }


def test_creator_batch_graph_admits_four_owner_steps_and_only_cookie_reference(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    cookie = home / "cookies.txt"
    cookie.write_text("session-cookie-secret", encoding="utf-8")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle("POST", "/api/v1/runs", {}, envelope(payload(cookie)))
    run = store.get_run(response["value"]["runId"])

    assert status == 201
    assert [node["type"] for node in run["graph"]["nodes"]] == [
        "discover-creator",
        "verify-creator",
        "localize-creator-batch",
        "verify-creator-batch",
    ]
    assert run["parameters"]["targetLanguages"] == ["ru-RU", "en-US"]
    assert run["parameters"]["sourceVolume"] == 0.08
    assert run["parameters"]["authenticationFile"] == str(cookie.resolve())
    assert "session-cookie-secret" not in json.dumps(run)


def test_creator_batch_graph_rejects_incomplete_voice_coverage(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    cookie = home / "cookies.txt"
    cookie.write_text("cookie", encoding="utf-8")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))
    invalid = payload(cookie)
    invalid["targetVoices"] = {"ru-RU": "voice"}

    status, _ = app.handle("POST", "/api/v1/runs", {}, envelope(invalid))

    assert status == 400
    assert store.list_runs() == []


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_localization_manifest(root, item_id, languages=("ru-RU", "en-US")):
    media_id = f"media-{item_id}"
    derivatives = []
    for language in languages:
        video = root / f"{item_id}-{language}.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(f"video-{item_id}-{language}".encode())
        derivatives.append(
            {
                "targetLanguage": language,
                "mediaId": media_id,
                "path": str(video),
                "sha256": digest(video),
                "size": video.stat().st_size,
                "duration": 2.5,
                "width": 1080,
                "height": 1920,
                "videoCodec": "h264",
                "audioCodec": "aac",
            }
        )
    manifest = root / f"{item_id}-localization.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "targetLanguages": list(languages),
                "expectedMediaIds": [media_id],
                "derivatives": derivatives,
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_creator_batch_adapters_require_committed_creator_fact_and_verify_every_derivative(tmp_path, monkeypatch):
    creator = tmp_path / "creator-manifest.json"
    creator.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "platform": "douyin",
                "maxItems": 2,
                "items": [
                    {"ordinal": 1, "id": "video-1", "url": "https://www.douyin.com/video/1", "title": "One"},
                    {"ordinal": 2, "id": "video-2", "url": "https://www.douyin.com/video/2", "title": "Two"},
                ],
            }
        ),
        encoding="utf-8",
    )
    first = write_localization_manifest(tmp_path / "localized", "video-1")
    second = write_localization_manifest(tmp_path / "localized", "video-2")
    output = tmp_path / "batches"
    batch = output / "run-1" / "creator-batch-manifest.json"
    batch.parent.mkdir(parents=True)
    batch.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "creatorManifest": str(creator),
                "creatorManifestSha256": digest(creator),
                "platform": "douyin",
                "expectedItemIds": ["video-1", "video-2"],
                "targetLanguages": ["ru-RU", "en-US"],
                "maximumActiveItems": 1,
                "items": [
                    {"ordinal": 1, "id": "video-1", "localizationManifest": str(first), "localizationManifestSha256": digest(first), "derivativeCount": 2},
                    {"ordinal": 2, "id": "video-2", "localizationManifest": str(second), "localizationManifestSha256": digest(second), "derivativeCount": 2},
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt = batch.parent / "creator-batch-receipt.json"
    receipt.write_text(
        json.dumps({"schemaVersion": 1, "operationId": "run-1:step:localize-creator-batch", "resultClass": "COMPLETED", "manifest": str(batch), "manifestSha256": digest(batch), "itemCount": 2}),
        encoding="utf-8",
    )
    seen = {}

    def fake_execute(self, node, context, on_log, cancel_event):
        seen["argv"] = node.config["argv"]
        return AdapterResult(True, {"exitCode": 0})

    monkeypatch.setattr(CommandAdapter, "execute", fake_execute)
    context = {
        "runId": "run-1",
        "parameters": {
            **payload(tmp_path / "unused-cookie.txt"),
            "authenticationFile": None,
        },
        "steps": [
            {"nodeId": "discover-creator", "status": "COMPLETED", "result": {"manifest": str(creator), "manifestSha256": digest(creator)}}
        ],
    }

    localized = CreatorBatchAdapter(tmp_path / "creator-batch.ps1", output).execute(type("Node", (), {"id": "localize-creator-batch"})(), context, lambda _line: None, None)
    context["steps"].append({"nodeId": "localize-creator-batch", "status": "COMPLETED", "result": localized.details})
    verified = VerifyCreatorBatchAdapter().execute(None, context, lambda _line: None, None)

    assert localized.completed and verified.completed
    assert str(creator.resolve()) in seen["argv"]
    assert seen["argv"].count("--target-language") == 2
    assert seen["argv"].count("--voice") == 2
    assert verified.details == {"manifest": str(batch.resolve()), "itemCount": 2, "derivativeCount": 4}


def test_runtime_registers_creator_batch_adapters(tmp_path):
    _, engine = build_runtime(Path(__file__).resolve().parents[2], tmp_path / "runtime")

    assert isinstance(engine.adapters["localize-creator-batch"], CreatorBatchAdapter)
    assert isinstance(engine.adapters["verify-creator-batch"], VerifyCreatorBatchAdapter)
