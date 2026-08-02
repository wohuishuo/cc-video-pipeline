import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "publication-batch-execution"
TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP)); sys.path.insert(0, str(TEST_ROOT))

from fixtures import build_batch, digest, write_json
from publication_batch_execution.contracts import load_batch_plan
from publication_batch_execution.operation import (
    ChildExecutionFact,
    PublicationBatchExecution,
)


class FakeExecutor:
    identity = "fake-publication-executor@1"

    def __init__(self, outcomes=None):
        self.outcomes = {key: list(value) for key, value in (outcomes or {}).items()}
        self.calls = []
        self.active = 0
        self.maximum_active = 0

    def execute(self, item, output_dir, child_operation_id, vault_path, on_log):
        self.active += 1; self.maximum_active = max(self.maximum_active, self.active)
        try:
            self.calls.append((item.identity, child_operation_id, str(vault_path)))
            result_class = self.outcomes.get(item.identity, ["COMPLETED"]).pop(0)
            output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
            receipt = output / "publication-receipt.json"
            if result_class == "COMPLETED":
                external_id = f"youtube-{item.ordinal}"
                manifest = output / "publication-manifest.json"
                write_json(
                    manifest,
                    {
                        "schemaVersion": 1, "plan": str(item.plan_path),
                        "planSha256": item.plan_sha256, "public": False,
                        "publications": [{
                            "jobId": item.job_id, "platform": "youtube", "status": "COMPLETED",
                            "externalId": external_id, "facts": {"privacyStatus": "private"}, "reused": False,
                        }],
                    },
                )
                write_json(
                    receipt,
                    {
                        "schemaVersion": 1, "operationId": child_operation_id,
                        "inputFingerprint": "f" * 64, "plan": str(item.plan_path),
                        "planSha256": item.plan_sha256, "resultClass": "COMPLETED",
                        "items": [{"jobId": item.job_id, "platform": "youtube", "status": "COMPLETED", "externalId": external_id}],
                        "maximumActiveExecutions": 1, "manifest": str(manifest),
                        "manifestSha256": digest(manifest), "error": None,
                    },
                )
                return ChildExecutionFact("COMPLETED", receipt, manifest, digest(manifest), external_id)
            write_json(
                receipt,
                {
                    "schemaVersion": 1, "operationId": child_operation_id,
                    "inputFingerprint": "f" * 64, "plan": str(item.plan_path),
                    "planSha256": item.plan_sha256, "resultClass": result_class,
                    "items": [{"jobId": item.job_id, "platform": "youtube", "status": result_class}],
                    "maximumActiveExecutions": 1, "manifest": None, "manifestSha256": None,
                    "error": result_class.lower(),
                },
            )
            return ChildExecutionFact(result_class, receipt, None, None, None, result_class.lower())
        finally:
            self.active -= 1


def execute(tmp_path, executor, operation_id="batch-execute-op"):
    plan_path, confirmation, vault = build_batch(tmp_path)
    batch = load_batch_plan(plan_path, confirmation, vault)
    result = PublicationBatchExecution().execute(batch, tmp_path / "execution", operation_id, executor)
    return batch, result


def test_executes_every_child_strictly_serially_and_replays_without_side_effects(tmp_path):
    executor = FakeExecutor(); batch, first = execute(tmp_path, executor)
    replay = PublicationBatchExecution().execute(batch, tmp_path / "execution", "batch-execute-op", executor)
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))

    assert first.result_class == "COMPLETED" and replay.result_class == "DUPLICATE_COMPLETED"
    assert executor.maximum_active == 1
    assert [row[0] for row in executor.calls] == ["ru-RU:m1", "en-US:m1"]
    assert len({row[1] for row in executor.calls}) == 2
    assert [row["externalId"] for row in manifest["items"]] == ["youtube-1", "youtube-2"]
    assert manifest["maximumActiveItems"] == 1


def test_same_operation_with_different_executor_identity_conflicts(tmp_path):
    executor = FakeExecutor(); batch, first = execute(tmp_path, executor)
    changed = FakeExecutor(); changed.identity = "other-executor@1"

    conflict = PublicationBatchExecution().execute(batch, tmp_path / "execution", "batch-execute-op", changed)

    assert first.result_class == "COMPLETED"
    assert conflict.result_class == "REJECTED_CONFLICT"
    assert changed.calls == []


def test_failed_child_resumes_without_repeating_verified_later_child(tmp_path):
    executor = FakeExecutor({"ru-RU:m1": ["FAILED", "COMPLETED"]})
    batch, failed = execute(tmp_path, executor)
    resumed = PublicationBatchExecution().execute(batch, tmp_path / "execution", "batch-execute-op", executor)

    assert failed.result_class == "FAILED" and failed.manifest_path is None
    assert resumed.result_class == "COMPLETED"
    assert [row[0] for row in executor.calls] == ["ru-RU:m1", "en-US:m1", "ru-RU:m1"]


def test_stale_completed_child_is_reexecuted_but_valid_child_is_reused(tmp_path):
    executor = FakeExecutor(); batch, first = execute(tmp_path, executor)
    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    Path(receipt["items"][0]["executionManifest"]).write_text("stale", encoding="utf-8")

    repaired = PublicationBatchExecution().execute(batch, tmp_path / "execution", "batch-execute-op", executor)

    assert repaired.result_class == "COMPLETED"
    assert [row[0] for row in executor.calls] == ["ru-RU:m1", "en-US:m1", "ru-RU:m1"]


def test_unknown_child_is_never_reexecuted_but_distinct_children_continue(tmp_path):
    executor = FakeExecutor({"ru-RU:m1": ["UNKNOWN"]})
    batch, uncertain = execute(tmp_path, executor)
    replay = PublicationBatchExecution().execute(batch, tmp_path / "execution", "batch-execute-op", executor)
    receipt = json.loads(uncertain.receipt_path.read_text(encoding="utf-8"))

    assert uncertain.result_class == "UNKNOWN" and uncertain.manifest_path is None
    assert replay.result_class == "REJECTED_UNKNOWN"
    assert [row[0] for row in executor.calls] == ["ru-RU:m1", "en-US:m1"]
    assert [row["status"] for row in receipt["items"]] == ["UNKNOWN", "COMPLETED"]
    assert not (tmp_path / "execution" / "publication-batch-execution-manifest.json").exists()


def test_corrupt_existing_receipt_is_fenced_without_child_execution(tmp_path):
    plan_path, confirmation, vault = build_batch(tmp_path); batch = load_batch_plan(plan_path, confirmation, vault)
    output = tmp_path / "execution"; output.mkdir(); (output / "publication-batch-execution-receipt.json").write_text("bad", encoding="utf-8")
    executor = FakeExecutor()

    result = PublicationBatchExecution().execute(batch, output, "batch-execute-op", executor)

    assert result.result_class == "REJECTED_CONFLICT"
    assert executor.calls == []
