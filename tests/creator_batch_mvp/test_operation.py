import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "creator-batch"
sys.path.insert(0, str(APP))

from creator_batch.contracts import BatchPolicy, CreatorSource
from creator_batch.operation import BatchOperation, ItemProcessResult

def policy():
    return BatchPolicy.create(["ru-RU"], {"ru-RU": "ru-RU-DmitryNeural"})


def committed_manifest(root, item_id, marker="ok"):
    path = root / f"{item_id}-{marker}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schemaVersion": 1, "itemId": item_id, "marker": marker}), encoding="utf-8")
    return path


class RecordingProcessor:
    def __init__(self, failures=()):
        self.failures = set(failures)
        self.calls = []
        self.active = 0
        self.maximum_active = 0

    def process(self, item, item_root, child_prefix, batch_policy, cookies, on_log):
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        self.calls.append((item.id, Path(item_root), child_prefix))
        try:
            if item.id in self.failures:
                return ItemProcessResult(False, None, 0, f"unavailable: {item.id}")
            return ItemProcessResult(True, committed_manifest(Path(item_root), item.id), 1)
        finally:
            self.active -= 1


def three_item_source(tmp_path):
    items = [
        {"ordinal": index, "id": f"video-{index}", "url": f"https://www.douyin.com/video/{index}", "title": f"Video {index}", "publishedAt": None}
        for index in range(1, 4)
    ]
    value = {
        "schemaVersion": 1,
        "platform": "douyin",
        "requestedUrl": "https://www.douyin.com/user/creator",
        "creator": {"id": "creator-1", "name": "Creator"},
        "adapter": "fixture@1",
        "maxItems": 0,
        "complete": True,
        "truncated": False,
        "items": items,
    }
    path = tmp_path / "creator-manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return CreatorSource.load(path)


def test_batch_processes_strictly_serial_and_continues_after_one_item_failure(tmp_path):
    source = three_item_source(tmp_path)
    processor = RecordingProcessor({"video-2"})

    result = BatchOperation().execute(source, policy(), tmp_path / "out", "batch-1", processor=processor)
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))

    assert result.result_class == "FAILED"
    assert result.manifest_path is None
    assert [call[0] for call in processor.calls] == ["video-1", "video-2", "video-3"]
    assert processor.maximum_active == 1
    assert receipt["maximumActiveItems"] == 1
    assert [(row["id"], row["status"]) for row in receipt["items"]] == [
        ("video-1", "COMPLETED"),
        ("video-2", "FAILED"),
        ("video-3", "COMPLETED"),
    ]
    assert not (tmp_path / "out" / "creator-batch-manifest.json").exists()


def test_batch_resume_retries_only_incomplete_item_and_then_replays_without_work(tmp_path):
    source = three_item_source(tmp_path)
    output = tmp_path / "out"
    first = RecordingProcessor({"video-2"})
    assert BatchOperation().execute(source, policy(), output, "batch-1", processor=first).result_class == "FAILED"
    retry = RecordingProcessor()

    completed = BatchOperation().execute(source, policy(), output, "batch-1", processor=retry)
    replay = RecordingProcessor()
    duplicate = BatchOperation().execute(source, policy(), output, "batch-1", processor=replay)
    manifest = json.loads(completed.manifest_path.read_text(encoding="utf-8"))

    assert [call[0] for call in retry.calls] == ["video-2"]
    assert completed.result_class == "COMPLETED"
    assert manifest["expectedItemIds"] == ["video-1", "video-2", "video-3"]
    assert [row["id"] for row in manifest["items"]] == ["video-1", "video-2", "video-3"]
    assert duplicate.result_class == "DUPLICATE_COMPLETED"
    assert replay.calls == []


def test_batch_reprocesses_stale_completed_item_and_rejects_changed_input(tmp_path):
    source = three_item_source(tmp_path)
    output = tmp_path / "out"
    initial = RecordingProcessor()
    result = BatchOperation().execute(source, policy(), output, "batch-1", processor=initial)
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    stale = Path(receipt["items"][1]["localizationManifest"])
    stale.write_text("changed", encoding="utf-8")
    repair = RecordingProcessor()

    repaired = BatchOperation().execute(source, policy(), output, "batch-1", processor=repair)
    changed_policy = BatchPolicy.create(["en-US"], {"en-US": "en-US-GuyNeural"})
    conflict_processor = RecordingProcessor()
    conflict = BatchOperation().execute(source, changed_policy, output, "batch-1", processor=conflict_processor)

    assert repaired.result_class == "COMPLETED"
    assert [call[0] for call in repair.calls] == ["video-2"]
    assert conflict.result_class == "REJECTED_CONFLICT"
    assert conflict_processor.calls == []


def test_batch_receipt_never_persists_cookie_path_or_contents(tmp_path):
    source = three_item_source(tmp_path)
    cookies = tmp_path / "cookies-secret.txt"
    cookies.write_text("session-secret-value", encoding="utf-8")

    result = BatchOperation().execute(source, policy(), tmp_path / "out", "batch-1", processor=RecordingProcessor(), cookies=cookies)
    persisted = result.receipt_path.read_text(encoding="utf-8") + result.manifest_path.read_text(encoding="utf-8")

    assert "cookies-secret" not in persisted
    assert "session-secret-value" not in persisted
