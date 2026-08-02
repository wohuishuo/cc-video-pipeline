import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "publication-batch-execution"
TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP)); sys.path.insert(0, str(TEST_ROOT))

from fixtures import build_batch, digest, write_json
from publication_batch_execution.child_executor import ProcessResult, PublicPublicationExecutor
from publication_batch_execution.contracts import load_batch_plan
from publication_batch_execution.operation import PublicationBatchExecution


def write_completed(item, output: Path, operation_id: str):
    output.mkdir(parents=True, exist_ok=True)
    external_id = f"external-{item.ordinal}"
    manifest = output / "publication-manifest.json"
    write_json(
        manifest,
        {
            "schemaVersion": 1, "plan": str(item.plan_path), "planSha256": item.plan_sha256,
            "public": False, "publications": [{
                "jobId": item.job_id, "platform": "youtube", "status": "COMPLETED",
                "externalId": external_id, "facts": {"privacyStatus": "private"}, "reused": False,
            }],
        },
    )
    receipt = output / "publication-receipt.json"
    write_json(
        receipt,
        {
            "schemaVersion": 1, "operationId": operation_id, "inputFingerprint": "f" * 64,
            "plan": str(item.plan_path), "planSha256": item.plan_sha256,
            "resultClass": "COMPLETED", "items": [{
                "jobId": item.job_id, "platform": "youtube", "status": "COMPLETED", "externalId": external_id,
            }], "maximumActiveExecutions": 1, "manifest": str(manifest),
            "manifestSha256": digest(manifest), "error": None,
        },
    )
    return receipt, manifest, external_id


def test_invokes_publication_with_exact_confirmation_and_verifies_completion(tmp_path):
    path, confirmation, vault = build_batch(tmp_path); item = load_batch_plan(path, confirmation, vault).items[0]
    seen = {}

    def runner(argv, on_log):
        seen["argv"] = list(argv)
        output = Path(argv[argv.index("--output-dir") + 1]); operation_id = argv[argv.index("--operation-id") + 1]
        write_completed(item, output, operation_id)
        return ProcessResult(0, json.dumps({"resultClass":"COMPLETED","artifact":str(output / "publication-manifest.json")}), "")

    executor = PublicPublicationExecutor(tmp_path / "publication.ps1", runner=runner)
    fact = executor.execute(item, tmp_path / "out", "child-op", vault, lambda _line: None)

    assert fact.result_class == "COMPLETED" and fact.external_id == "external-1"
    assert seen["argv"][:7] == ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str((tmp_path / "publication.ps1").resolve()), "execute"]
    assert seen["argv"][seen["argv"].index("--confirmation") + 1] == item.plan_sha256
    assert seen["argv"][seen["argv"].index("--credential-vault") + 1] == str(vault.resolve())
    assert "--platform-io-launcher" not in seen["argv"]


def test_rejects_tampered_child_manifest_even_when_process_reports_success(tmp_path):
    path, confirmation, vault = build_batch(tmp_path); item = load_batch_plan(path, confirmation, vault).items[0]

    def runner(argv, on_log):
        output = Path(argv[argv.index("--output-dir") + 1]); operation_id = argv[argv.index("--operation-id") + 1]
        _receipt, manifest, _external_id = write_completed(item, output, operation_id)
        manifest.write_text("tampered", encoding="utf-8")
        return ProcessResult(0, '{"resultClass":"COMPLETED"}', "")

    fact = PublicPublicationExecutor(tmp_path / "publication.ps1", runner=runner).execute(
        item, tmp_path / "out", "child-op", vault, lambda _line: None
    )

    assert fact.result_class == "FAILED"
    assert fact.manifest_path is None


def test_preserves_unknown_publication_receipt_without_manifest(tmp_path):
    path, confirmation, vault = build_batch(tmp_path); item = load_batch_plan(path, confirmation, vault).items[0]

    def runner(argv, on_log):
        output = Path(argv[argv.index("--output-dir") + 1]); operation_id = argv[argv.index("--operation-id") + 1]
        write_json(
            output / "publication-receipt.json",
            {
                "schemaVersion": 1, "operationId": operation_id, "inputFingerprint": "f" * 64,
                "plan": str(item.plan_path), "planSha256": item.plan_sha256,
                "resultClass": "UNKNOWN", "items": [{"jobId":item.job_id,"platform":"youtube","status":"UNKNOWN"}],
                "maximumActiveExecutions": 1, "manifest": None, "manifestSha256": None,
                "error": "publication outcome is unknown",
            },
        )
        return ProcessResult(3, '{"resultClass":"UNKNOWN","artifact":null}', "")

    fact = PublicPublicationExecutor(tmp_path / "publication.ps1", runner=runner).execute(
        item, tmp_path / "out", "child-op", vault, lambda _line: None
    )

    assert fact.result_class == "UNKNOWN"
    assert fact.receipt_path.is_file() and fact.manifest_path is None and fact.external_id is None


def test_real_publication_and_vault_compose_two_children_through_fake_platform_boundary(tmp_path):
    plan_path, confirmation, _placeholder_vault = build_batch(tmp_path)
    vault = tmp_path / "real-vault.json"
    secret = "batch-child-secret"
    environment = {**os.environ, "BATCH_SECRET": secret}
    stored = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(ROOT / "apps" / "credential-vault" / "run.ps1"), "put", "--vault", str(vault),
            "--credential-id", "youtube-main", "--provider", "youtube", "--label", "Main",
            "--secret-env", "BATCH_SECRET", "--json",
        ],
        env=environment, capture_output=True, text=True, encoding="utf-8",
    )
    assert stored.returncode == 0
    batch = load_batch_plan(plan_path, confirmation, vault)
    fake_platform = tmp_path / "fake-platform.ps1"
    fake_platform.write_text(
        "param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)\n"
        "$ok = $env:VIDEO_PLATFORM_CREDENTIAL -eq 'batch-child-secret'\n"
        "if (-not $ok) { '{\"status\":\"failed\"}'; exit 9 }\n"
        "$name = [IO.Path]::GetFileNameWithoutExtension($Arguments[2])\n"
        "@{status='ok'; external_id=('fake-' + $name)} | ConvertTo-Json -Compress\n",
        encoding="utf-8",
    )
    executor = PublicPublicationExecutor(
        ROOT / "apps" / "publication" / "run.ps1",
        platform_io_launcher=fake_platform,
    )

    result = PublicationBatchExecution().execute(batch, tmp_path / "execution", "adjacent-op", executor)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.result_class == "COMPLETED"
    assert [row["externalId"] for row in manifest["items"]] == ["fake-localized-ru-RU", "fake-localized-en-US"]
    persisted = "".join(
        file.read_text(encoding="utf-8", errors="replace")
        for file in (tmp_path / "execution").rglob("*.json")
    ) + vault.read_text(encoding="utf-8")
    assert secret not in persisted
