import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "transcription"
sys.path.insert(0, str(APP))

from transcription_app.contracts import Segment  # noqa: E402
from transcription_app.operation import AdapterTranscript, TranscriptLoop  # noqa: E402


def source_manifest(tmp_path: Path) -> Path:
    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    a.write_bytes(b"aaa")
    b.write_bytes(b"bb")
    path = tmp_path / "source-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sourceKind": "folder",
                "source": {},
                "media": [
                    {"id": "media-a", "path": str(a), "size": 3, "extension": ".mp4"},
                    {"id": "media-b", "path": str(b), "size": 2, "extension": ".mp4"},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


class FakeAdapter:
    identity = "fake-asr@1"

    def __init__(self, failures=()):
        self.failures = set(failures)
        self.calls = []
        self.active = 0
        self.maximum_active = 0

    def transcribe(self, media, language, on_log):
        self.calls.append(media.id)
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            if media.id in self.failures:
                raise RuntimeError(f"failed {media.id}")
            on_log(f"fake transcript {media.id}")
            return AdapterTranscript(language if language != "auto" else "en", (Segment(1, 0.0, 1.0, f"text {media.id}"),))
        finally:
            self.active -= 1


def test_loop_publishes_one_verified_artifact_per_media_in_source_order(tmp_path):
    source = source_manifest(tmp_path)
    output = tmp_path / "out"
    adapter = FakeAdapter()

    result = TranscriptLoop().execute(source, output, "op-1", language="auto", adapter=adapter)

    assert result.result_class == "COMPLETED"
    assert adapter.calls == ["media-a", "media-b"]
    assert adapter.maximum_active == 1
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["expectedMediaIds"] == ["media-a", "media-b"]
    assert [row["mediaId"] for row in manifest["transcripts"]] == ["media-a", "media-b"]
    for row in manifest["transcripts"]:
        assert Path(row["transcriptPath"]).is_file()
        assert Path(row["srtPath"]).read_text(encoding="utf-8").startswith("1\n00:00:00,000")


def test_failed_item_is_isolated_and_retry_reuses_completed_checkpoint(tmp_path):
    source = source_manifest(tmp_path)
    output = tmp_path / "out"
    first = FakeAdapter({"media-a"})

    failed = TranscriptLoop().execute(source, output, "op-1", language="en", adapter=first)

    assert failed.result_class == "FAILED"
    assert failed.manifest_path is None
    receipt = json.loads(failed.receipt_path.read_text(encoding="utf-8"))
    assert [row["status"] for row in receipt["items"]] == ["FAILED", "COMPLETED"]
    assert first.calls == ["media-a", "media-b"]

    retry = FakeAdapter()
    completed = TranscriptLoop().execute(source, output, "op-1", language="en", adapter=retry)

    assert completed.result_class == "COMPLETED"
    assert retry.calls == ["media-a"]
    assert completed.manifest_path.is_file()


def test_completed_operation_replays_without_adapter_call(tmp_path):
    source = source_manifest(tmp_path)
    output = tmp_path / "out"
    TranscriptLoop().execute(source, output, "op-1", language="en", adapter=FakeAdapter())
    replay_adapter = FakeAdapter()

    replay = TranscriptLoop().execute(source, output, "op-1", language="en", adapter=replay_adapter)

    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert replay_adapter.calls == []


def test_changed_input_conflicts_instead_of_overwriting_prior_operation(tmp_path):
    source = source_manifest(tmp_path)
    output = tmp_path / "out"
    loop = TranscriptLoop()
    loop.execute(source, output, "op-1", language="en", adapter=FakeAdapter())

    conflict = loop.execute(source, output, "op-1", language="zh", adapter=FakeAdapter())

    assert conflict.result_class == "REJECTED_CONFLICT"
    assert conflict.manifest_path is None
