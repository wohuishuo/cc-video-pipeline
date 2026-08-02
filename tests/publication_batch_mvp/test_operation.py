import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "publication-batch"
sys.path.insert(0, str(APP))

from publication_batch.contracts import BatchPolicy, load_localization_manifest, load_metadata_template
from publication_batch.operation import ChildPlanFact, PublicationBatchOperation


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    lineage = []
    for name in ("source", "translation", "voice"):
        path = tmp_path / f"{name}-manifest.json"
        path.write_text(name, encoding="utf-8")
        lineage.append(path)
    derivatives = []
    for ordinal, language in enumerate(("ru-RU", "en-US"), 1):
        video = tmp_path / f"localized-{ordinal}.mp4"
        video.write_bytes(f"video-{ordinal}".encode())
        derivatives.append(
            {
                "targetLanguage": language,
                "mediaId": "m1",
                "path": str(video),
                "sha256": digest(video),
                "size": video.stat().st_size,
                "duration": 3.0,
                "width": 1080,
                "height": 1920,
                "videoCodec": "h264",
                "audioCodec": "aac",
            }
        )
    manifest = tmp_path / "localization-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sourceManifest": str(lineage[0]),
                "sourceManifestSha256": digest(lineage[0]),
                "translationManifest": str(lineage[1]),
                "translationManifestSha256": digest(lineage[1]),
                "voiceManifest": str(lineage[2]),
                "voiceManifestSha256": digest(lineage[2]),
                "sourceVolume": 0.12,
                "targetLanguages": ["ru-RU", "en-US"],
                "expectedMediaIds": ["m1"],
                "derivatives": derivatives,
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps({"title": "{filename} [{language}]", "tags": ["{media_id}"]}),
        encoding="utf-8",
    )
    return load_localization_manifest(manifest), load_metadata_template(metadata)


class RecordingProcessor:
    def __init__(self, fail=None):
        self.fail = set(fail or [])
        self.calls = []
        self.child_ids = []
        self.active = 0
        self.maximum_active = 0

    def plan(self, derivative, metadata_path, output_dir, operation_id, policy, on_log):
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        self.calls.append((derivative.target_language, derivative.media_id))
        self.child_ids.append(operation_id)
        try:
            if derivative.identity in self.fail:
                raise RuntimeError(f"planned failure for {derivative.identity}")
            output_dir.mkdir(parents=True, exist_ok=True)
            credentials = dict(policy.credentials)
            jobs = []
            for ordinal, (platform, account) in enumerate(policy.targets, 1):
                job = {
                    "ordinal": ordinal,
                    "id": hashlib.sha256(f"{derivative.sha256}:{platform}".encode()).hexdigest(),
                    "platform": platform,
                    "account": account,
                    "visibility": "private-or-draft",
                }
                if platform in credentials:
                    job["credentialId"] = credentials[platform]
                jobs.append(job)
            plan_path = output_dir / "publication-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "video": {"path": str(derivative.path), "sha256": derivative.sha256, "size": derivative.size},
                        "metadata": {
                            "path": str(metadata_path.resolve()),
                            "sha256": digest(metadata_path),
                            "title": json.loads(metadata_path.read_text(encoding="utf-8"))["title"],
                        },
                        "public": False,
                        "jobs": jobs,
                    }
                ),
                encoding="utf-8",
            )
            return ChildPlanFact(plan_path.resolve(), digest(plan_path), len(jobs))
        finally:
            self.active -= 1


def policy(targets=None):
    selected = targets or [("youtube", "primary"), ("tiktok", "brand")]
    credentials = {"youtube": "youtube-main"} if any(platform == "youtube" for platform, _account in selected) else {}
    return BatchPolicy.create(selected, credentials)


def execute(tmp_path, processor, *, targets=None, operation_id="batch-1"):
    localization, metadata = inputs(tmp_path / "input")
    return PublicationBatchOperation().execute(
        localization,
        metadata,
        policy(targets),
        tmp_path / "out",
        operation_id,
        processor,
    )


def test_operation_plans_every_derivative_strictly_in_manifest_order(tmp_path):
    processor = RecordingProcessor()

    result = execute(tmp_path, processor)

    assert result.result_class == "COMPLETED"
    assert processor.maximum_active == 1
    assert processor.calls == [("ru-RU", "m1"), ("en-US", "m1")]
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [(row["targetLanguage"], row["mediaId"]) for row in manifest["items"]] == processor.calls
    assert manifest["totalJobCount"] == 4
    assert manifest["maximumActiveItems"] == 1


def test_failed_item_is_checkpointed_later_items_continue_and_retry_is_stable(tmp_path):
    failed_processor = RecordingProcessor(fail={"ru-RU:m1"})

    failed = execute(tmp_path, failed_processor)

    assert failed.result_class == "FAILED"
    assert failed.manifest_path is None
    assert failed_processor.calls == [("ru-RU", "m1"), ("en-US", "m1")]
    receipt = json.loads(failed.receipt_path.read_text(encoding="utf-8"))
    assert [row["status"] for row in receipt["items"]] == ["FAILED", "COMPLETED"]

    retry = RecordingProcessor()
    completed = execute(tmp_path, retry)

    assert completed.result_class == "COMPLETED"
    assert retry.calls == [("ru-RU", "m1")]
    assert retry.child_ids == [failed_processor.child_ids[0]]


def test_completed_replay_does_not_call_processor(tmp_path):
    execute(tmp_path, RecordingProcessor())
    replay = RecordingProcessor()

    result = execute(tmp_path, replay)

    assert result.result_class == "DUPLICATE_COMPLETED"
    assert replay.calls == []


def test_same_operation_id_with_changed_targets_conflicts_without_mutation(tmp_path):
    execute(tmp_path, RecordingProcessor(), targets=[("youtube", "primary")])
    receipt_path = tmp_path / "out" / "publication-batch-receipt.json"
    receipt_before = receipt_path.read_bytes()

    conflict = execute(tmp_path, RecordingProcessor(), targets=[("tiktok", "brand")])

    assert conflict.result_class == "REJECTED_CONFLICT"
    assert receipt_path.read_bytes() == receipt_before


def test_changed_operation_identity_conflicts_without_mutation(tmp_path):
    execute(tmp_path, RecordingProcessor(), operation_id="batch-1")
    receipt_path = tmp_path / "out" / "publication-batch-receipt.json"
    receipt_before = receipt_path.read_bytes()

    conflict = execute(tmp_path, RecordingProcessor(), operation_id="batch-2")

    assert conflict.result_class == "REJECTED_CONFLICT"
    assert receipt_path.read_bytes() == receipt_before


def test_stale_child_plan_is_repaired_with_same_child_identity(tmp_path):
    first_processor = RecordingProcessor()
    first = execute(tmp_path, first_processor)
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    Path(manifest["items"][0]["publicationPlan"]).write_text("changed", encoding="utf-8")
    repair = RecordingProcessor()

    result = execute(tmp_path, repair)

    assert result.result_class == "COMPLETED"
    assert repair.calls == [("ru-RU", "m1")]
    assert repair.child_ids == [first_processor.child_ids[0]]


def test_aggregate_exposes_only_non_secret_credential_references(tmp_path):
    result = execute(tmp_path, RecordingProcessor())

    persisted = result.receipt_path.read_text(encoding="utf-8") + result.manifest_path.read_text(encoding="utf-8")

    assert "youtube-main" in persisted
    assert "credentialValue" not in persisted
    assert "credentialVault" not in persisted
    assert "accessToken" not in persisted
