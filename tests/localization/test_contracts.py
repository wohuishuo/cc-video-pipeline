import json
import sys
from pathlib import Path

import pytest


LOCALIZATION_ROOT = Path(__file__).resolve().parents[2] / "apps" / "localization"
sys.path.insert(0, str(LOCALIZATION_ROOT))

from localizer.contracts import (  # noqa: E402
    BatchManifest,
    JobRecord,
    Segment,
    StageRecord,
    atomic_write_json,
    sha256_file,
)


def test_stage_is_reusable_only_when_fingerprints_and_outputs_match(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source-v1")
    output = tmp_path / "artifact.json"
    output.write_text("{}", encoding="utf-8")
    stage = StageRecord.completed(
        adapter="fixture@1",
        inputs={"source": sha256_file(source)},
        outputs={"artifact": str(output)},
    )

    assert stage.is_reusable({"source": sha256_file(source)}, adapter="fixture@1")

    source.write_bytes(b"source-v2")

    assert not stage.is_reusable({"source": sha256_file(source)}, adapter="fixture@1")


def test_stage_is_not_reusable_when_a_declared_output_is_empty_or_missing(tmp_path):
    output = tmp_path / "artifact.json"
    output.write_text("{}", encoding="utf-8")
    stage = StageRecord.completed(
        adapter="fixture@1",
        inputs={"source": "fingerprint"},
        outputs={"artifact": str(output)},
    )

    output.write_bytes(b"")
    assert not stage.is_reusable({"source": "fingerprint"}, adapter="fixture@1")

    output.unlink()
    assert not stage.is_reusable({"source": "fingerprint"}, adapter="fixture@1")


def test_stage_is_not_reusable_for_a_different_adapter_version(tmp_path):
    output = tmp_path / "artifact.json"
    output.write_text("{}", encoding="utf-8")
    stage = StageRecord.completed(
        adapter="fixture@1",
        inputs={"source": "fingerprint"},
        outputs={"artifact": str(output)},
    )

    assert not stage.is_reusable({"source": "fingerprint"}, adapter="fixture@2")


def test_stage_reuse_requires_the_current_adapter_version(tmp_path):
    output = tmp_path / "artifact.json"
    output.write_text("{}", encoding="utf-8")
    stage = StageRecord.completed(
        adapter="fixture@1",
        inputs={"source": "fingerprint"},
        outputs={"artifact": str(output)},
    )

    with pytest.raises(TypeError, match="adapter"):
        stage.is_reusable({"source": "fingerprint"})


def test_completed_stage_records_utc_iso_timestamps_and_no_error():
    stage = StageRecord.completed(
        adapter="fixture@1", inputs={}, outputs={"artifact": "result.json"}
    )

    assert stage.status == "completed"
    assert stage.completed_at is not None
    assert stage.completed_at.endswith("+00:00")
    assert stage.error is None


def test_completed_stage_requires_an_output_through_all_construction_paths():
    with pytest.raises(ValueError, match="completed stage requires at least one output"):
        StageRecord.completed(adapter="fixture@1", inputs={}, outputs={})

    with pytest.raises(ValueError, match="completed stage requires at least one output"):
        StageRecord(
            status="completed",
            adapter="fixture@1",
            inputs={},
            outputs={},
            started_at="2026-07-30T00:00:00+00:00",
            completed_at="2026-07-30T00:00:01+00:00",
        )

    with pytest.raises(ValueError, match="completed stage requires at least one output"):
        StageRecord.from_dict(
            {
                "schema_version": 1,
                "status": "completed",
                "adapter": "fixture@1",
                "inputs": {},
                "outputs": {},
                "started_at": "2026-07-30T00:00:00+00:00",
                "completed_at": "2026-07-30T00:00:01+00:00",
                "error": None,
            }
        )


def test_atomic_write_json_replaces_an_existing_receipt_with_valid_json(tmp_path):
    receipt = tmp_path / "job.json"
    receipt.write_text('{"state": "old"}', encoding="utf-8")

    atomic_write_json(receipt, {"state": "complete", "attempt": 2})

    assert json.loads(receipt.read_text(encoding="utf-8")) == {
        "state": "complete",
        "attempt": 2,
    }
    assert not list(tmp_path.glob(".job.json.*.tmp"))


def test_atomic_write_json_removes_its_temporary_file_after_a_replace_failure(
    tmp_path, monkeypatch
):
    receipt = tmp_path / "job.json"

    def fail_replace(self, target):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replacement failure"):
        atomic_write_json(receipt, {"state": "complete"})

    assert not list(tmp_path.glob(".job.json.*.tmp"))


def test_job_manifest_round_trip_preserves_immutable_segment_timing():
    segment = Segment(id=7, start=1.25, end=2.5, text="\u5de5\u4e1a", words=[])
    job = JobRecord(
        id="111",
        source="videos/[111] first.mp4",
        source_sha256="a" * 64,
        stages={"transcription": StageRecord.pending(adapter="asr@1")},
    )
    manifest = BatchManifest(
        manifest="video-urls.txt", expected_ids=("111",), jobs=[job]
    )

    restored = BatchManifest.from_dict(manifest.to_dict())

    assert restored.to_dict() == {
        "schema_version": 2,
        "manifest": "video-urls.txt",
        "expected_ids": ["111"],
        "jobs": [
            {
                "schema_version": 1,
                "id": "111",
                "source": "videos/[111] first.mp4",
                "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "stages": {
                    "transcription": {
                        "schema_version": 1,
                        "status": "pending",
                        "adapter": "asr@1",
                        "inputs": {},
                        "outputs": {},
                        "started_at": None,
                        "completed_at": None,
                        "error": None,
                    }
                },
            }
        ],
    }
    assert Segment.from_dict(segment.to_dict()) == segment


def test_stage_record_rejects_an_incomplete_completed_receipt(tmp_path):
    output = tmp_path / "artifact.json"
    output.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="completed stage requires timestamps"):
        StageRecord.from_dict(
            {
                "schema_version": 1,
                "status": "completed",
                "adapter": "fixture@1",
                "inputs": {"source": "fingerprint"},
                "outputs": {"artifact": str(output)},
                "started_at": None,
                "completed_at": None,
                "error": None,
            }
        )


def test_stage_record_rejects_an_incomplete_completed_state_in_memory():
    with pytest.raises(ValueError, match="completed stage requires timestamps"):
        StageRecord(
            status="completed",
            adapter="fixture@1",
            inputs={"source": "fingerprint"},
            outputs={"artifact": "artifact.json"},
        )


def test_stage_receipt_lifecycle_cannot_be_mutated_after_validation():
    stage = StageRecord.running(adapter="fixture@1", inputs={"source": "fingerprint"})

    with pytest.raises(AttributeError):
        stage.status = "completed"


def test_stage_receipt_fingerprints_cannot_be_mutated_after_validation(tmp_path):
    output = tmp_path / "artifact.json"
    output.write_text("{}", encoding="utf-8")
    stage = StageRecord.completed(
        adapter="fixture@1",
        inputs={"source": "original-fingerprint"},
        outputs={"artifact": str(output)},
    )

    with pytest.raises(TypeError):
        stage.inputs["source"] = "forged-fingerprint"


def test_manifest_rejects_an_unsupported_schema_version():
    with pytest.raises(ValueError, match="unsupported batch schema version: 3"):
        BatchManifest.from_dict(
            {"schema_version": 3, "manifest": "video-urls.txt", "jobs": []}
        )


def test_batch_manifest_rejects_legacy_schema_without_expected_ids():
    with pytest.raises(ValueError, match="unsupported batch schema version: 1"):
        BatchManifest.from_dict(
            {"schema_version": 1, "manifest": "video-urls.txt", "jobs": []}
        )


def test_job_identity_cannot_be_mutated_after_inventory_discovery():
    job = JobRecord(id="111", source="[111] source.mp4", source_sha256="a" * 64)

    with pytest.raises(AttributeError):
        job.id = "222"


@pytest.mark.parametrize(
    ("id", "source", "source_sha256", "message"),
    [
        ("", "videos/[111] source.mp4", "a" * 64, "job ID"),
        ("111", "", "a" * 64, "source path"),
        ("111", "videos/[111] source.mp4", "not-a-fingerprint", "SHA-256"),
    ],
)
def test_job_record_rejects_invalid_immutable_identity(
    id, source, source_sha256, message
):
    with pytest.raises(ValueError, match=message):
        JobRecord(id=id, source=source, source_sha256=source_sha256)


def test_job_record_rejects_a_source_id_that_does_not_match_its_job_id():
    with pytest.raises(ValueError, match="source ID.*222.*job ID.*111"):
        JobRecord(
            id="111",
            source="videos/[222] source.mp4",
            source_sha256="a" * 64,
        )


def test_job_record_deserialization_rejects_non_string_identity_fields():
    with pytest.raises(ValueError, match="job ID"):
        JobRecord.from_dict(
            {
                "schema_version": 1,
                "id": 111,
                "source": "videos/[111] source.mp4",
                "source_sha256": "a" * 64,
                "stages": {},
            }
        )


def test_batch_manifest_requires_complete_unique_job_coverage():
    first = JobRecord(
        id="111", source="videos/[111] source.mp4", source_sha256="a" * 64
    )
    duplicate_id = JobRecord(
        id="111", source="videos/[111] alternate.mp4", source_sha256="b" * 64
    )

    with pytest.raises(ValueError, match="duplicate job ID.*111"):
        BatchManifest(
            manifest="video-urls.txt",
            expected_ids=("111",),
            jobs=[first, duplicate_id],
        )

    with pytest.raises(ValueError, match="at least one job"):
        BatchManifest(manifest="video-urls.txt", expected_ids=("111",), jobs=[])


def test_batch_manifest_coverage_cannot_be_mutated_after_validation():
    job = JobRecord(
        id="111", source="videos/[111] source.mp4", source_sha256="a" * 64
    )
    manifest = BatchManifest(
        manifest="video-urls.txt", expected_ids=("111",), jobs=[job]
    )

    with pytest.raises(AttributeError):
        manifest.manifest = "other-urls.txt"

    with pytest.raises(TypeError):
        manifest.jobs[0] = job


def test_batch_manifest_rejects_missing_and_extra_jobs_against_expected_ids():
    first = JobRecord(
        id="111", source="videos/[111] source.mp4", source_sha256="a" * 64
    )
    second = JobRecord(
        id="222", source="videos/[222] source.mp4", source_sha256="b" * 64
    )

    with pytest.raises(ValueError, match="missing job IDs: 222"):
        BatchManifest(
            manifest="video-urls.txt", expected_ids=("111", "222"), jobs=[first]
        )

    with pytest.raises(ValueError, match="unexpected job IDs: 222"):
        BatchManifest(manifest="video-urls.txt", expected_ids=("111",), jobs=[first, second])
