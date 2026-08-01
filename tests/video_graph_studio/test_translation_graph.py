import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import (  # noqa: E402
    AdapterResult,
    TranslateTranscriptAdapter,
    VerifyTranslationAdapter,
)
from studio.api import StudioApplication  # noqa: E402
from studio.engine import WorkflowEngine  # noqa: E402
from studio.server import build_runtime  # noqa: E402
from studio.store import RunStore  # noqa: E402


class NoopAdapter:
    def execute(self, node, context, on_log, cancel_event):
        return AdapterResult(True, {"node": node.id})


def envelope(payload):
    return {
        "contractId": "CMD-RUN-CREATE",
        "contractVersion": "1.0",
        "operationId": "op-translate",
        "correlationId": "corr-translate",
        "payload": payload,
    }


def application(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    adapter = NoopAdapter()
    engine = WorkflowEngine(
        store,
        {
            "source-intake": adapter,
            "verify-source": adapter,
            "transcribe-source": adapter,
            "verify-transcript": adapter,
            "translate-transcript": adapter,
            "verify-translation": adapter,
        },
    )
    return StudioApplication(store, engine, allowed_roots=(tmp_path,)), store


def test_folder_translation_template_admits_six_owner_steps_and_languages(tmp_path):
    app, store = application(tmp_path)
    source = tmp_path / "media"
    source.mkdir()

    status, response = app.handle(
        "POST",
        "/api/v1/runs",
        {},
        envelope(
            {
                "templateId": "folder-translation",
                "sourceRoot": str(source),
                "sourceLanguage": "auto",
                "asrModel": "tiny",
                "asrDevice": "cpu",
                "asrComputeType": "int8",
                "targetLanguages": ["ru-RU", "en-US"],
                "translationModel": "facebook/nllb-200-distilled-600M",
                "translationDevice": "cpu",
                "translationBatchSize": 4,
            }
        ),
    )

    run = store.get_run(response["value"]["runId"])
    assert status == 201
    assert [node["type"] for node in run["graph"]["nodes"]] == [
        "source-intake", "verify-source", "transcribe-source", "verify-transcript",
        "translate-transcript", "verify-translation",
    ]
    assert run["parameters"]["targetLanguages"] == ["ru-RU", "en-US"]
    assert run["parameters"]["translationBatchSize"] == 4


def test_translation_template_rejects_duplicate_or_unsupported_languages(tmp_path):
    app, store = application(tmp_path)
    source = tmp_path / "media"
    source.mkdir()
    for languages in (["ru-RU", "ru-RU"], ["fr-FR"], []):
        status, response = app.handle(
            "POST", "/api/v1/runs", {},
            envelope({"templateId": "folder-translation", "sourceRoot": str(source), "targetLanguages": languages}),
        )
        assert status == 400
        assert response["resultClass"] == "REJECTED_MALFORMED"
    assert store.list_runs() == []


def write_translation_fact(tmp_path):
    translation = tmp_path / "translation.json"
    subtitle = tmp_path / "translation.srt"
    translation.write_text('{"schemaVersion":1,"reviewStatus":"MACHINE"}', encoding="utf-8")
    subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = tmp_path / "translation-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "transcriptManifest": str(tmp_path / "transcript-manifest.json"),
                "transcriptManifestSha256": "a" * 64,
                "expectedMediaIds": ["m1"],
                "targetLanguages": ["ru-RU"],
                "translations": [
                    {
                        "mediaId": "m1",
                        "targetLanguage": "ru-RU",
                        "translationPath": str(translation),
                        "translationSha256": digest(translation),
                        "srtPath": str(subtitle),
                        "srtSha256": digest(subtitle),
                        "reviewStatus": "MACHINE",
                        "segmentCount": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest, digest(manifest)


def test_verify_translation_requires_exact_language_media_coverage_and_hashes(tmp_path):
    manifest, manifest_hash = write_translation_fact(tmp_path)
    context = {
        "steps": [
            {
                "nodeId": "translate",
                "status": "COMPLETED",
                "result": {"manifest": str(manifest), "manifestSha256": manifest_hash},
            }
        ]
    }

    result = VerifyTranslationAdapter().execute(None, context, lambda _message: None, None)
    assert result.completed is True
    assert result.details["translationCount"] == 1

    (tmp_path / "translation.srt").write_text("changed", encoding="utf-8")
    rejected = VerifyTranslationAdapter().execute(None, context, lambda _message: None, None)
    assert rejected.completed is False


def test_production_runtime_registers_translation_owner_adapters(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    _, engine = build_runtime(repository, tmp_path / "runtime")
    assert isinstance(engine.adapters["translate-transcript"], TranslateTranscriptAdapter)
    assert isinstance(engine.adapters["verify-translation"], VerifyTranslationAdapter)
