import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.api import StudioApplication  # noqa: E402
from studio.result_projection import project_run_results  # noqa: E402


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def completed_run(tmp_path):
    video = tmp_path / "output" / "ru.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"0123456789")
    translation = write_json(tmp_path / "translation" / "translation-manifest.json", {"schemaVersion": 1})
    write_json(
        translation.with_name("translation-receipt.json"),
        {
            "schemaVersion": 1,
            "items": [
                {
                    "status": "COMPLETED",
                    "usage": {"promptTokens": 31, "completionTokens": 9, "totalTokens": 40},
                }
            ],
        },
    )
    localization = write_json(
        tmp_path / "localization" / "localization-manifest.json",
        {
            "schemaVersion": 1,
            "translationManifest": str(translation),
            "translationManifestSha256": sha(translation),
            "targetLanguages": ["ru-RU"],
            "expectedMediaIds": ["media-1"],
            "derivatives": [
                {
                    "targetLanguage": "ru-RU",
                    "mediaId": "media-1",
                    "path": str(video),
                    "sha256": sha(video),
                    "size": video.stat().st_size,
                    "duration": 12.5,
                    "width": 1080,
                    "height": 1920,
                    "videoCodec": "h264",
                    "audioCodec": "aac",
                }
            ],
        },
    )
    creator = write_json(
        tmp_path / "creator-manifest.json",
        {
            "schemaVersion": 1,
            "items": [{"ordinal": 1, "id": "creator-video-1", "title": "Original title"}],
        },
    )
    batch = write_json(
        tmp_path / "creator-batch-manifest.json",
        {
            "schemaVersion": 1,
            "creatorManifest": str(creator),
            "creatorManifestSha256": sha(creator),
            "items": [
                {
                    "ordinal": 1,
                    "id": "creator-video-1",
                    "localizationManifest": str(localization),
                    "localizationManifestSha256": sha(localization),
                    "derivativeCount": 1,
                }
            ],
        },
    )
    run = {
        "runId": "run-1",
        "status": "COMPLETED",
        "createdAt": "2026-08-03T10:00:00+00:00",
        "updatedAt": "2026-08-03T10:03:20+00:00",
        "logs": [
            {"sequence": 1, "created_at": "2026-08-03T10:00:10+00:00", "message": '{"event":"creator_phase","item":{"id":"creator-video-1"},"phase":"voice","status":"RUNNING"}'},
            {"sequence": 2, "created_at": "2026-08-03T10:02:10+00:00", "message": '{"event":"creator_phase","item":{"id":"creator-video-1"},"phase":"voice","status":"COMPLETED"}'},
        ],
        "steps": [
            {
                "nodeId": "localize-creator-batch",
                "status": "COMPLETED",
                "result": {"manifest": str(batch), "manifestSha256": sha(batch)},
            }
        ],
    }
    return run, video


def test_projects_verified_creator_results_metrics_and_usage(tmp_path):
    run, video = completed_run(tmp_path)

    result = project_run_results(run, allowed_roots=(tmp_path,))

    assert result["status"] == "COMPLETED"
    assert result["elapsedSeconds"] == 200
    assert result["outputRoot"] == str(tmp_path)
    assert result["totalBytes"] == 10
    assert result["reportedUsage"] == {
        "promptTokens": 31,
        "completionTokens": 9,
        "totalTokens": 40,
    }
    assert result["phaseDurations"] == {"voice": 120.0}
    assert result["videos"][0] == {
        "id": result["videos"][0]["id"],
        "available": True,
        "sourceItemId": "creator-video-1",
        "title": "Original title",
        "targetLanguage": "ru-RU",
        "mediaId": "media-1",
        "path": str(video),
        "size": 10,
        "duration": 12.5,
        "width": 1080,
        "height": 1920,
        "videoCodec": "h264",
        "audioCodec": "aac",
    }


def test_projects_stale_derivative_as_unavailable_without_losing_other_results(tmp_path):
    run, video = completed_run(tmp_path)
    video.write_bytes(b"changed")

    result = project_run_results(run, allowed_roots=(tmp_path,))

    assert result["totalBytes"] == 0
    assert result["videos"][0]["available"] is False
    assert "fingerprint" in result["videos"][0]["error"].lower()


def test_results_api_projects_the_stored_run(tmp_path):
    run, _video = completed_run(tmp_path)

    class Store:
        def get_run(self, run_id):
            assert run_id == "run-1"
            return run

    app = StudioApplication(Store(), object(), allowed_roots=(tmp_path,))
    status, payload = app.handle("GET", "/api/v1/runs/run-1/results", {}, None)

    assert status == 200
    assert payload["videos"][0]["previewUrl"].endswith(f"/{payload['videos'][0]['id']}")


def test_projects_a_local_folder_localization_without_a_creator_batch(tmp_path):
    run, video = completed_run(tmp_path)
    batch = json.loads(Path(run["steps"][0]["result"]["manifest"]).read_text(encoding="utf-8"))
    localization = Path(batch["items"][0]["localizationManifest"])
    run["steps"] = [
        {
            "nodeId": "localize-video",
            "status": "COMPLETED",
            "result": {"manifest": str(localization), "manifestSha256": sha(localization)},
        }
    ]

    result = project_run_results(run, allowed_roots=(tmp_path,))

    assert result["outputRoot"] == str(localization.parent)
    assert result["videos"][0]["sourceItemId"] == "media-1"
    assert result["videos"][0]["title"] == video.stem
    assert result["videos"][0]["available"] is True
