"""Real two-Graph Studio -> Publication -> Vault -> fake Platform boundary drill."""

from __future__ import annotations

import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def envelope(contract_id, operation_id, correlation_id, payload=None):
    return {"contractId":contract_id,"contractVersion":"1.0","operationId":operation_id,"correlationId":correlation_id,"payload":payload or {}}


def wait_terminal(store, run_id):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        run=store.get_run(run_id)
        if run["status"] in {"COMPLETED","FAILED","CANCELLED"}: return run
        time.sleep(.05)
    raise TimeoutError(run_id)


def main() -> int:
    repository=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repository/"apps"/"video-graph-studio"))
    from studio.adapters import PublicationExecuteAdapter,PublicationPlanAdapter,VerifyPublicationExecutionAdapter,VerifyPublicationPlanAdapter
    from studio.api import StudioApplication
    from studio.engine import WorkflowEngine
    from studio.store import RunStore

    with tempfile.TemporaryDirectory(prefix="studio-publication-") as directory:
        root=Path(directory); video=root/"final.mp4"; metadata=root/"metadata.json"; vault=root/"vault.json"
        video.write_bytes(b"verified-video-fixture"); metadata.write_text(json.dumps({"title":"Private proof"}),encoding="utf-8")
        secret="studio-publication-child-only-secret"
        vault_launcher=repository/"apps"/"credential-vault"/"run.ps1"
        stored=subprocess.run(
            ["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(vault_launcher),"put","--vault",str(vault),"--credential-id","youtube-main","--provider","youtube","--label","Proof","--secret-env","PUBLICATION_SECRET","--json"],
            capture_output=True,text=True,encoding="utf-8",env={**os.environ,"PUBLICATION_SECRET":secret},check=False,
        )
        if stored.returncode!=0: raise RuntimeError("credential setup failed")
        fake_platform=root/"fake-platform.ps1"
        fake_platform.write_text(
            "param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)\n"
            "$ok = $env:VIDEO_PLATFORM_CREDENTIAL -eq 'studio-publication-child-only-secret'\n"
            "if ($ok) { '{\"status\":\"ok\",\"external_id\":\"fake-youtube-private-001\"}'; exit 0 }\n"
            "'{\"status\":\"failed\",\"error\":\"credential missing\"}'; exit 9\n",
            encoding="utf-8",
        )
        store=RunStore(root/"studio.db"); publication=repository/"apps"/"publication"/"run.ps1"; outputs=root/"artifacts"
        engine=WorkflowEngine(store,{
            "plan-publication":PublicationPlanAdapter(publication,outputs/"plans"),
            "verify-publication-plan":VerifyPublicationPlanAdapter(),
            "execute-publication":PublicationExecuteAdapter(publication,outputs/"executions",fake_platform),
            "verify-publication-execution":VerifyPublicationExecutionAdapter(),
        })
        app=StudioApplication(store,engine,allowed_roots=(root,))
        status,created=app.handle("POST","/api/v1/runs",{},envelope("CMD-RUN-CREATE","plan-proof","proof-correlation",{"templateId":"publication-plan","videoPath":str(video),"metadataPath":str(metadata),"targetPlatforms":["youtube"],"account":"primary","credentialIds":{"youtube":"youtube-main"},"public":False}))
        plan_run_id=created["value"]["runId"]
        app.handle("POST",f"/api/v1/runs/{plan_run_id}/start",{},envelope("CMD-RUN-START","start-plan","proof-correlation"))
        plan_run=wait_terminal(store,plan_run_id); plan_fact=next(step["result"] for step in plan_run["steps"] if step["nodeId"]=="plan-publication")
        status2,created2=app.handle("POST","/api/v1/runs",{},envelope("CMD-RUN-CREATE","execute-proof","proof-correlation",{"templateId":"publication-execute","planRunId":plan_run_id,"confirmation":plan_fact["manifestSha256"],"credentialVaultPath":str(vault)}))
        execute_run_id=created2["value"]["runId"]
        app.handle("POST",f"/api/v1/runs/{execute_run_id}/start",{},envelope("CMD-RUN-START","start-execute","proof-correlation"))
        execute_run=wait_terminal(store,execute_run_id); engine.wait_idle(10)
        execute_fact=next(step["result"] for step in execute_run["steps"] if step["nodeId"]=="execute-publication")
        manifest=json.loads(Path(execute_fact["manifest"]).read_text(encoding="utf-8")); persisted=(vault.read_text(encoding="utf-8")+json.dumps(plan_run)+json.dumps(execute_run)+json.dumps(manifest))
        receipt={"planHttpStatus":status,"planRunId":plan_run_id,"planStatus":plan_run["status"],"executeHttpStatus":status2,"executeRunId":execute_run_id,"executeStatus":execute_run["status"],"externalId":manifest["publications"][0]["externalId"],"visibility":manifest["publications"][0]["facts"]["visibility"],"credentialPlaintextPersisted":secret in persisted}
        del app,engine,store; gc.collect()
        print(json.dumps(receipt,ensure_ascii=False,indent=2))
        return 0 if receipt["planStatus"]==receipt["executeStatus"]=="COMPLETED" and not receipt["credentialPlaintextPersisted"] else 1


if __name__=="__main__": raise SystemExit(main())
