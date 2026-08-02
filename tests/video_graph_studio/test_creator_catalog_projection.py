import hashlib
import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.api import CREATOR_GRAPHS, StudioApplication
from studio.contracts import ContractError
from studio.engine import WorkflowEngine
from studio.store import CreateRun, RunStore


def _manifest(tmp_path: Path) -> tuple[Path, dict]:
    value = {
        "schemaVersion": 1,
        "platform": "douyin",
        "requestedUrl": "https://v.douyin.com/example/",
        "creator": {"id": "creator-1", "name": "Creator One"},
        "adapter": "fixture@1",
        "maxItems": 2,
        "complete": True,
        "truncated": False,
        "items": [
            {
                "ordinal": 1,
                "id": "video-2",
                "url": "https://www.douyin.com/video/video-2",
                "title": "Second published",
                "publishedAt": 200,
            },
            {
                "ordinal": 2,
                "id": "video-1",
                "url": "https://www.douyin.com/video/video-1",
                "title": "First published",
                "publishedAt": 100,
            },
        ],
    }
    path = tmp_path / "creator-manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path, value


def _run(store: RunStore, manifest: Path, *, graph="creator-profile", terminal=True):
    result = store.create_run(
        CreateRun(
            operation_id=f"op-{graph}-{terminal}",
            correlation_id="catalog-test",
            graph=CREATOR_GRAPHS["creator-profile"],
            parameters={"templateId": graph},
        )
    )
    run_id = result.value["runId"]
    store.transition(run_id, expected_version=0, target="RUNNING")
    store.start_step(run_id, "discover-creator")
    store.complete_step(
        run_id,
        "discover-creator",
        {
            "manifest": str(manifest),
            "manifestSha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        },
    )
    store.start_step(run_id, "verify-creator")
    store.complete_step(run_id, "verify-creator", {"verified": True})
    if terminal:
        store.transition(run_id, expected_version=1, target="COMPLETED")
    run = store.get_run(run_id)
    if graph != "creator-profile":
        run["graph"]["graphId"] = graph
    return run


def test_projects_exact_ordered_verified_creator_catalog(tmp_path):
    from studio.creator_catalog import project_creator_catalog

    manifest, _ = _manifest(tmp_path)
    catalog = project_creator_catalog(_run(RunStore(tmp_path / "studio.db"), manifest))

    assert catalog == {
        "schemaVersion": 1,
        "runId": catalog["runId"],
        "platform": "douyin",
        "requestedUrl": "https://v.douyin.com/example/",
        "creator": {"id": "creator-1", "name": "Creator One"},
        "complete": True,
        "truncated": False,
        "itemCount": 2,
        "items": [
            {
                "ordinal": 1,
                "id": "video-2",
                "url": "https://www.douyin.com/video/video-2",
                "title": "Second published",
                "publishedAt": 200,
                "subtitleStatus": "UNKNOWN_ASR",
            },
            {
                "ordinal": 2,
                "id": "video-1",
                "url": "https://www.douyin.com/video/video-1",
                "title": "First published",
                "publishedAt": 100,
                "subtitleStatus": "UNKNOWN_ASR",
            },
        ],
    }


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("wrong-graph", "REJECTED_MALFORMED"),
        ("non-terminal", "REJECTED_CONFLICT"),
        ("missing-file", "REJECTED_NOT_FOUND"),
        ("fingerprint-conflict", "REJECTED_CONFLICT"),
    ],
)
def test_rejects_unverified_catalog_without_item_data(tmp_path, mutation, code):
    from studio.creator_catalog import project_creator_catalog

    manifest, _ = _manifest(tmp_path)
    store = RunStore(tmp_path / "studio.db")
    run = _run(
        store,
        manifest,
        graph="another-graph" if mutation == "wrong-graph" else "creator-profile",
        terminal=mutation != "non-terminal",
    )
    if mutation == "missing-file":
        manifest.unlink()
    if mutation == "fingerprint-conflict":
        manifest.write_text("{}", encoding="utf-8")

    with pytest.raises(ContractError) as raised:
        project_creator_catalog(run)
    assert raised.value.code == code
    assert not hasattr(raised.value, "items")


def test_api_exposes_creator_catalog_before_generic_run_route(tmp_path):
    manifest, _ = _manifest(tmp_path)
    store = RunStore(tmp_path / "studio.db")
    run = _run(store, manifest)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle(
        "GET", f'/api/v1/runs/{run["runId"]}/creator-catalog', {}, None
    )

    assert status == 200
    assert response["itemCount"] == 2
    assert [item["id"] for item in response["items"]] == ["video-2", "video-1"]
