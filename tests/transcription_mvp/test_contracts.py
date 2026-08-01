import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "transcription"
sys.path.insert(0, str(APP))

from transcription_app.contracts import (  # noqa: E402
    Segment,
    TranscriptArtifact,
    TranscriptDocument,
    TranscriptManifest,
    TranscriptionError,
    load_source_manifest,
    sha256_file,
)


def write_source_manifest(tmp_path: Path, *, duplicate: bool = False) -> Path:
    first = tmp_path / "a.mp4"
    second = tmp_path / "b.mp4"
    first.write_bytes(b"aaa")
    second.write_bytes(b"bb")
    rows = [
        {"id": "media-a", "path": str(first), "size": 3, "extension": ".mp4"},
        {"id": "media-a" if duplicate else "media-b", "path": str(second), "size": 2, "extension": ".mp4"},
    ]
    path = tmp_path / "source-manifest.json"
    path.write_text(
        json.dumps({"schemaVersion": 1, "sourceKind": "folder", "source": {}, "media": rows}),
        encoding="utf-8",
    )
    return path


def test_source_manifest_loader_preserves_order_and_verifies_media(tmp_path):
    path = write_source_manifest(tmp_path)

    source = load_source_manifest(path)

    assert source.path == path.resolve()
    assert source.sha256 == sha256_file(path)
    assert [row.id for row in source.media] == ["media-a", "media-b"]
    assert [row.size for row in source.media] == [3, 2]


def test_source_manifest_rejects_duplicate_identity_and_changed_file(tmp_path):
    with pytest.raises(TranscriptionError, match="duplicate media ID"):
        load_source_manifest(write_source_manifest(tmp_path, duplicate=True))

    path = write_source_manifest(tmp_path)
    (tmp_path / "a.mp4").write_bytes(b"changed")
    with pytest.raises(TranscriptionError, match="size mismatch"):
        load_source_manifest(path)


@pytest.mark.parametrize(
    "values",
    [
        {"id": 0, "start": 0.0, "end": 1.0, "text": "hello"},
        {"id": 1, "start": -0.1, "end": 1.0, "text": "hello"},
        {"id": 1, "start": 1.0, "end": 1.0, "text": "hello"},
        {"id": 1, "start": 0.0, "end": 1.0, "text": "  "},
    ],
)
def test_segment_rejects_invalid_identity_timing_or_text(values):
    with pytest.raises(TranscriptionError):
        Segment(**values)


def test_transcript_document_requires_ordered_unique_segments(tmp_path):
    source = tmp_path / "a.mp4"
    source.write_bytes(b"source")
    first = Segment(1, 0.0, 1.0, "hello")
    second = Segment(2, 1.0, 2.0, "world")

    document = TranscriptDocument("media-a", str(source), sha256_file(source), "en", (first, second))
    assert [row["text"] for row in document.to_dict()["segments"]] == ["hello", "world"]

    with pytest.raises(TranscriptionError, match="ordered unique"):
        TranscriptDocument("media-a", str(source), sha256_file(source), "en", (second, first))


def test_transcript_manifest_requires_exact_source_coverage(tmp_path):
    source_manifest = write_source_manifest(tmp_path)
    transcript = tmp_path / "transcript.json"
    subtitle = tmp_path / "transcript.srt"
    transcript.write_text("{}", encoding="utf-8")
    subtitle.write_text("subtitle", encoding="utf-8")
    artifact = TranscriptArtifact(
        "media-a", str(tmp_path / "a.mp4"), sha256_file(tmp_path / "a.mp4"),
        str(transcript), sha256_file(transcript), str(subtitle), sha256_file(subtitle), "en", 1,
    )

    with pytest.raises(TranscriptionError, match="exact source coverage"):
        TranscriptManifest(str(source_manifest), sha256_file(source_manifest), ("media-a", "media-b"), (artifact,))
