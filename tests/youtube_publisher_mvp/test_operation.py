import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-publisher"
sys.path.insert(0, str(APP))

from youtube_publisher.client import UploadOutcome
from youtube_publisher.operation import YouTubePublishOperation


class Publisher:
    def __init__(self, outcome): self.outcome = outcome; self.calls = 0
    def upload(self, video, metadata, credential): self.calls += 1; return self.outcome


def assets(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"video")
    metadata = tmp_path / "metadata.json"; metadata.write_text('{"title":"Demo"}', encoding="utf-8")
    return video, metadata


def test_completed_operation_commits_redacted_receipt_and_replays(tmp_path):
    video, metadata = assets(tmp_path); secret = '{"accessToken":"never-persist"}'
    publisher = Publisher(UploadOutcome("COMPLETED", "youtube-id-3", {"privacyStatus": "private"}))
    operation = YouTubePublishOperation(publisher)

    first = operation.execute(video, metadata, tmp_path / "out", "operation-1", secret)
    second = operation.execute(video, metadata, tmp_path / "out", "operation-1", secret)
    receipt = first.receipt_path.read_text(encoding="utf-8")

    assert first.result_class == "COMPLETED"
    assert second.result_class == "DUPLICATE_COMPLETED"
    assert publisher.calls == 1
    assert "never-persist" not in receipt
    assert json.loads(receipt)["externalId"] == "youtube-id-3"


def test_unknown_operation_is_fenced_from_automatic_replay(tmp_path):
    video, metadata = assets(tmp_path); secret = '{"accessToken":"token"}'
    publisher = Publisher(UploadOutcome("UNKNOWN", None, {}, "upload outcome could not be determined"))
    operation = YouTubePublishOperation(publisher)

    first = operation.execute(video, metadata, tmp_path / "out", "operation-2", secret)
    second = operation.execute(video, metadata, tmp_path / "out", "operation-2", secret)

    assert first.result_class == "UNKNOWN"
    assert second.result_class == "REJECTED_UNKNOWN"
    assert publisher.calls == 1


def test_corrupt_or_incomplete_completed_receipt_is_fenced(tmp_path):
    video, metadata = assets(tmp_path); output = tmp_path / "out"; output.mkdir()
    receipt = output / "youtube-upload-receipt.json"
    publisher = Publisher(UploadOutcome("COMPLETED", "must-not-upload", {"privacyStatus": "private"}))
    operation = YouTubePublishOperation(publisher)

    receipt.write_text("not-json", encoding="utf-8")
    corrupt = operation.execute(video, metadata, output, "operation-3", '{"accessToken":"token"}')
    video_sha = hashlib.sha256(video.read_bytes()).hexdigest(); metadata_sha = hashlib.sha256(metadata.read_bytes()).hexdigest()
    fingerprint = hashlib.sha256(f"{video_sha}\0{metadata_sha}\0private\0youtube-publisher@1".encode()).hexdigest()
    receipt.write_text(json.dumps({"operationId": "operation-3", "inputFingerprint": fingerprint, "resultClass": "COMPLETED", "externalId": None}), encoding="utf-8")
    incomplete = operation.execute(video, metadata, output, "operation-3", '{"accessToken":"token"}')

    assert corrupt.result_class == "REJECTED_CONFLICT"
    assert incomplete.result_class == "REJECTED_CONFLICT"
    assert publisher.calls == 0
