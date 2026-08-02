import hashlib
import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "creator-selection"
sys.path.insert(0, str(APP))

from creator_selection.contracts import SelectionError, SelectionSpec
from creator_selection.operation import SelectionOperation


def _creator_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "creator-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "platform": "douyin",
                "requestedUrl": "https://www.douyin.com/user/creator",
                "creator": {"id": "creator-1", "name": "Creator"},
                "adapter": "fixture@1",
                "maxItems": 3,
                "complete": True,
                "truncated": False,
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


def test_selection_preserves_source_order_and_commits_source_fingerprint(tmp_path):
    source = _creator_manifest(tmp_path)
    spec = SelectionSpec.load(source, ["v1", "v3"])

    result = SelectionOperation().execute(spec, tmp_path / "out", "selection-op")
    value = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.result_class == "COMPLETED"
    assert value["creatorManifest"] == str(source.resolve())
    assert value["creatorManifestSha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert value["selectedItemIds"] == ["v3", "v1"]
    assert [item["ordinal"] for item in value["items"]] == [1, 2]
    assert [item["id"] for item in value["items"]] == ["v3", "v1"]


@pytest.mark.parametrize("selected", [["missing"], ["v1", "v1"], []])
def test_selection_rejects_unknown_duplicate_or_empty_ids(tmp_path, selected):
    with pytest.raises(SelectionError):
        SelectionSpec.load(_creator_manifest(tmp_path), selected)


def test_same_operation_replays_but_changed_selection_conflicts(tmp_path):
    source = _creator_manifest(tmp_path)
    operation = SelectionOperation()
    output = tmp_path / "out"

    first = operation.execute(SelectionSpec.load(source, ["v1", "v3"]), output, "op-1")
    replay = operation.execute(SelectionSpec.load(source, ["v3", "v1"]), output, "op-1")
    conflict = operation.execute(SelectionSpec.load(source, ["v2"]), output, "op-1")

    assert first.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert conflict.result_class == "REJECTED_CONFLICT"
    assert conflict.manifest_path is None
