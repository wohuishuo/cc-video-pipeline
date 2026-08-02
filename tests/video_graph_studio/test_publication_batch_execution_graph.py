import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
STUDIO = ROOT / "apps" / "video-graph-studio"
BATCH = ROOT / "apps" / "publication-batch-execution"
BATCH_TESTS = ROOT / "tests" / "publication_batch_execution_mvp"
sys.path.insert(0, str(STUDIO)); sys.path.insert(0, str(BATCH)); sys.path.insert(0, str(BATCH_TESTS))

from fixtures import build_batch, digest
from publication_batch_execution.contracts import load_batch_plan
from publication_batch_execution.operation import ChildExecutionFact, PublicationBatchExecution
from studio.adapters import (
    AdapterResult,
    CommandAdapter,
    PublicationBatchExecuteAdapter,
    VerifyPublicationBatchExecutionAdapter,
)
from studio.api import RELEASE_GRAPHS, StudioApplication
from studio.engine import WorkflowEngine
from studio.server import build_runtime
from studio.store import CreateRun, RunStore


def envelope(payload, operation_id="batch-execute-op"):
    return {
        "contractId": "CMD-RUN-CREATE",
        "contractVersion": "1.0",
        "operationId": operation_id,
        "correlationId": "batch-execute-corr",
        "payload": payload,
    }


def completed_release_run(store: RunStore, plan: Path, confirmation: str) -> str:
    graph = RELEASE_GRAPHS["folder-release"]
    run_id = store.create_run(
        CreateRun(f"release-plan-{confirmation[:12]}", "release-plan-corr", graph, {"batchPlanSha256": confirmation})
    ).value["runId"]
    store.transition(run_id, expected_version=0, target="RUNNING")
    for node in graph.nodes:
        store.start_step(run_id, node.id)
        if node.id == "plan-publication-batch":
            result = {"manifest": str(plan.resolve()), "manifestSha256": confirmation, "itemCount": 2, "jobCount": 2}
        elif node.id == "verify-publication-batch":
            result = {"manifest": str(plan.resolve()), "itemCount": 2, "jobCount": 2}
        else:
            result = {"verified": True}
        store.complete_step(run_id, node.id, result)
    store.transition(run_id, expected_version=1, target="COMPLETED")
    return run_id


def test_batch_execution_graph_admits_exact_completed_same_store_release_fact(tmp_path):
    plan, confirmation, vault = build_batch(tmp_path)
    store = RunStore(tmp_path / "studio.db")
    release_run_id = completed_release_run(store, plan, confirmation)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle(
        "POST", "/api/v1/runs", {},
        envelope({
            "templateId": "publication-batch-execute",
            "releasePlanRunId": release_run_id,
            "confirmation": confirmation,
            "credentialVaultPath": str(vault),
        }),
    )
    run = store.get_run(response["value"]["runId"])

    assert status == 201
    assert [node["type"] for node in run["graph"]["nodes"]] == [
        "execute-publication-batch", "verify-publication-batch-execution",
    ]
    assert run["parameters"] == {
        "templateId": "publication-batch-execute",
        "releasePlanRunId": release_run_id,
        "batchPlanPath": str(plan.resolve()),
        "confirmation": confirmation,
        "credentialVaultPath": str(vault.resolve()),
    }


def test_batch_execution_graph_rejects_wrong_confirmation_or_unsupported_target_before_run(tmp_path):
    plan, confirmation, vault = build_batch(tmp_path)
    store = RunStore(tmp_path / "studio.db")
    release_run_id = completed_release_run(store, plan, confirmation)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    wrong_status, _ = app.handle(
        "POST", "/api/v1/runs", {},
        envelope({"templateId":"publication-batch-execute","releasePlanRunId":release_run_id,"confirmation":"0"*64,"credentialVaultPath":str(vault)}, "wrong-sha"),
    )
    value = json.loads(plan.read_text(encoding="utf-8"))
    value["targets"] = [{"platform":"tiktok","account":"primary","credentialId":"tiktok-main"}]
    plan.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    unsafe_sha = digest(plan)
    unsafe_run_id = completed_release_run(store, plan, unsafe_sha)
    unsafe_status, _ = app.handle(
        "POST", "/api/v1/runs", {},
        envelope({"templateId":"publication-batch-execute","releasePlanRunId":unsafe_run_id,"confirmation":unsafe_sha,"credentialVaultPath":str(vault)}, "unsafe-target"),
    )

    assert wrong_status == 400
    assert unsafe_status == 400
    assert [run["graph"]["graphId"] for run in store.list_runs()] == ["folder-release", "folder-release"]


class CompletedChild:
    identity = "studio-test-executor-v1"

    def execute(self, item, output, operation_id, vault_path, on_log):
        output.mkdir(parents=True, exist_ok=True)
        external_id = f"external-{item.ordinal}"
        manifest = output / "publication-manifest.json"
        manifest.write_text(json.dumps({
            "schemaVersion":1,"plan":str(item.plan_path),"planSha256":item.plan_sha256,"public":False,
            "publications":[{"jobId":item.job_id,"platform":"youtube","status":"COMPLETED","externalId":external_id,"facts":{"privacyStatus":"private"}}],
        }, separators=(",", ":")), encoding="utf-8")
        receipt = output / "publication-receipt.json"
        receipt.write_text(json.dumps({
            "schemaVersion":1,"operationId":operation_id,"inputFingerprint":"f"*64,"plan":str(item.plan_path),"planSha256":item.plan_sha256,
            "resultClass":"COMPLETED","items":[{"jobId":item.job_id,"platform":"youtube","status":"COMPLETED","externalId":external_id}],
            "maximumActiveExecutions":1,"manifest":str(manifest.resolve()),"manifestSha256":digest(manifest),"error":None,
        }, separators=(",", ":")), encoding="utf-8")
        return ChildExecutionFact("COMPLETED", receipt, manifest, digest(manifest), external_id)


def test_batch_execute_and_verify_adapters_use_public_launcher_and_validate_each_child(tmp_path, monkeypatch):
    plan, confirmation, vault = build_batch(tmp_path)
    output_root = tmp_path / "outputs"
    operation_id = "run-1:step:execute-publication-batch"
    result = PublicationBatchExecution().execute(
        load_batch_plan(plan, confirmation, vault), output_root / "run-1", operation_id, CompletedChild()
    )
    assert result.result_class == "COMPLETED"
    seen = {}

    def fake_execute(self, node, context, on_log, cancel_event):
        seen["argv"] = node.config["argv"]
        return AdapterResult(True, {"exitCode": 0})

    monkeypatch.setattr(CommandAdapter, "execute", fake_execute)
    adapter = PublicationBatchExecuteAdapter(tmp_path / "batch-execution.ps1", output_root)
    context = {"runId":"run-1","parameters":{"batchPlanPath":str(plan),"confirmation":confirmation,"credentialVaultPath":str(vault)}}
    executed = adapter.execute(type("Node", (), {"id":"execute-publication-batch"})(), context, lambda _:None, None)
    verify_context = {**context, "steps":[{"nodeId":"execute-publication-batch","status":"COMPLETED","result":executed.details}]}
    verified = VerifyPublicationBatchExecutionAdapter().execute(None, verify_context, lambda _:None, None)

    assert executed.completed and verified.completed
    assert seen["argv"][:7] == ["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str((tmp_path/"batch-execution.ps1").resolve()),"execute"]
    assert seen["argv"][seen["argv"].index("--confirmation") + 1] == confirmation
    assert seen["argv"][seen["argv"].index("--credential-vault") + 1] == str(vault)
    child_manifest = next((output_root / "run-1" / "items").rglob("publication-manifest.json"))
    child_manifest.write_text("{}", encoding="utf-8")
    assert not VerifyPublicationBatchExecutionAdapter().execute(None, verify_context, lambda _:None, None).completed


def test_runtime_registers_publication_batch_execution_adapters(tmp_path):
    _, engine = build_runtime(ROOT, tmp_path / "runtime")

    assert isinstance(engine.adapters["execute-publication-batch"], PublicationBatchExecuteAdapter)
    assert isinstance(engine.adapters["verify-publication-batch-execution"], VerifyPublicationBatchExecutionAdapter)
