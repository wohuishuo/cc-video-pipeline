from pathlib import Path
import json
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "source-intake"
sys.path.insert(0, str(APP))

from intake.contracts import SourceSpec  # noqa: E402
from intake.operation import IntakeOperation, TransportResult  # noqa: E402


class RecordingTransport:
    def __init__(self, fail: bool = False):
        self.calls = 0
        self.fail = fail

    def fetch(self, spec, output_dir, on_log):
        self.calls += 1
        if self.fail:
            return TransportResult(False, (), None, {}, "network failed")
        media = output_dir / "downloaded.mp4"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b"download")
        platform_receipt = output_dir / "download-receipt.json"
        platform_receipt.write_text('{"status":"ok"}', encoding="utf-8")
        return TransportResult(True, (media,), platform_receipt, {"height": 1080})


def test_same_operation_and_source_replays_without_repeating_discovery(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "video.mp4").write_bytes(b"video")
    output = tmp_path / "out"
    operation = IntakeOperation()

    first = operation.execute(SourceSpec.folder(source), output, "op-1")
    replay = operation.execute(SourceSpec.folder(source), output, "op-1")

    assert first.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert replay.manifest_path == first.manifest_path
    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["manifestSha256"]


def test_same_operation_with_changed_source_conflicts(tmp_path):
    first_source = tmp_path / "first"
    second_source = tmp_path / "second"
    first_source.mkdir()
    second_source.mkdir()
    (first_source / "a.mp4").write_bytes(b"a")
    (second_source / "b.mp4").write_bytes(b"b")
    output = tmp_path / "out"
    operation = IntakeOperation()
    operation.execute(SourceSpec.folder(first_source), output, "op-1")

    result = operation.execute(SourceSpec.folder(second_source), output, "op-1")

    assert result.result_class == "REJECTED_CONFLICT"
    manifest = json.loads((output / "source-manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["root"] == str(first_source.resolve())


def test_url_transport_is_called_once_and_receipt_contains_no_credentials(tmp_path):
    transport = RecordingTransport()
    operation = IntakeOperation()
    spec = SourceSpec.url("https://youtu.be/abc")

    first = operation.execute(spec, tmp_path / "out", "op-1", transport=transport)
    replay = operation.execute(spec, tmp_path / "out", "op-1", transport=transport)

    assert first.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert transport.calls == 1
    text = first.receipt_path.read_text(encoding="utf-8").lower()
    assert "cookie" not in text
    assert "credential" not in text


def test_failed_transport_publishes_failure_receipt_but_no_manifest(tmp_path):
    result = IntakeOperation().execute(
        SourceSpec.url("https://youtu.be/abc"),
        tmp_path / "out",
        "op-1",
        transport=RecordingTransport(fail=True),
    )
    assert result.result_class == "FAILED"
    assert result.receipt_path.is_file()
    assert result.manifest_path is None
    assert not (tmp_path / "out" / "source-manifest.json").exists()

