import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult, TranscriptSourceAdapter, VerifyTranscriptAdapter  # noqa: E402
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
        "operationId": "op-transcribe",
        "correlationId": "corr-transcribe",
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
        },
    )
    return StudioApplication(store, engine, allowed_roots=(tmp_path,)), store


def test_folder_transcription_template_admits_four_owner_steps(tmp_path):
    app, store = application(tmp_path)
    source = tmp_path / "media"
    source.mkdir()

    status, response = app.handle(
        "POST",
        "/api/v1/runs",
        {},
        envelope(
            {
                "templateId": "folder-transcription",
                "sourceRoot": str(source),
                "sourceLanguage": "auto",
                "asrModel": "small",
                "asrDevice": "cpu",
                "asrComputeType": "int8",
            }
        ),
    )

    run = store.get_run(response["value"]["runId"])
    assert status == 201
    assert [node["type"] for node in run["graph"]["nodes"]] == [
        "source-intake", "verify-source", "transcribe-source", "verify-transcript"
    ]
    assert run["parameters"]["sourceLanguage"] == "auto"
    assert run["parameters"]["asrDevice"] == "cpu"


def test_url_transcription_template_validates_asr_device(tmp_path):
    app, store = application(tmp_path)
    status, response = app.handle(
        "POST",
        "/api/v1/runs",
        {},
        envelope(
            {
                "templateId": "url-transcription",
                "sourceUrl": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "asrDevice": "quantum",
            }
        ),
    )
    assert status == 400
    assert response["resultClass"] == "REJECTED_MALFORMED"
    assert store.list_runs() == []


def write_transcript_fact(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    transcript = tmp_path / "transcript.json"
    srt = tmp_path / "transcript.srt"
    transcript.write_text('{"schemaVersion":1,"segments":[{"id":1,"start":0,"end":1,"text":"hi"}]}', encoding="utf-8")
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n\n", encoding="utf-8")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = tmp_path / "transcript-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sourceManifest": str(tmp_path / "source-manifest.json"),
                "sourceManifestSha256": "a" * 64,
                "expectedMediaIds": ["m1"],
                "transcripts": [
                    {
                        "mediaId": "m1",
                        "sourcePath": str(source),
                        "sourceSha256": digest(source),
                        "transcriptPath": str(transcript),
                        "transcriptSha256": digest(transcript),
                        "srtPath": str(srt),
                        "srtSha256": digest(srt),
                        "detectedLanguage": "en",
                        "segmentCount": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest, digest(manifest)


def test_verify_transcript_accepts_only_committed_hash_matched_artifacts(tmp_path):
    manifest, manifest_hash = write_transcript_fact(tmp_path)
    context = {
        "steps": [
            {
                "nodeId": "transcribe",
                "status": "COMPLETED",
                "result": {"manifest": str(manifest), "manifestSha256": manifest_hash},
            }
        ]
    }

    result = VerifyTranscriptAdapter().execute(None, context, lambda _message: None, None)

    assert result.completed is True
    assert result.details["transcriptCount"] == 1
    (tmp_path / "transcript.srt").write_text("changed", encoding="utf-8")
    rejected = VerifyTranscriptAdapter().execute(None, context, lambda _message: None, None)
    assert rejected.completed is False


def test_production_runtime_registers_transcription_owner_adapters(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    _, engine = build_runtime(repository, tmp_path / "runtime")
    assert isinstance(engine.adapters["transcribe-source"], TranscriptSourceAdapter)
    assert isinstance(engine.adapters["verify-transcript"], VerifyTranscriptAdapter)
