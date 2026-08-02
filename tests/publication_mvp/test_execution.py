import hashlib
import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"publication"
sys.path.insert(0,str(APP))

from publication.contracts import PlanSpec
from publication.execution import ExecutionOutcome, PlatformIOExecutionAdapter, PublicationExecution
from publication.planning import PublicationPlanner


class FakePlatform:
    identity="fake-platform@1"
    def __init__(self,fail=None): self.calls=[]; self.fail=fail; self.maximum_active=1
    def execute(self,job,on_log):
        self.calls.append(job["platform"])
        if job["platform"]==self.fail: return ExecutionOutcome(False,None,{},"failed")
        return ExecutionOutcome(True,f"external-{job['platform']}",{"visibility":job["visibility"]})


def plan(tmp_path,targets,public=False):
    video=tmp_path/"v.mp4"; video.write_bytes(b"video"); metadata=tmp_path/"m.json"; metadata.write_text(json.dumps({"title":"Title"}),encoding="utf-8")
    result=PublicationPlanner().execute(PlanSpec.create(video,metadata,targets,public=public),tmp_path/"plan","plan-op")
    return result.plan_path,hashlib.sha256(result.plan_path.read_bytes()).hexdigest()


def test_execute_requires_exact_plan_hash(tmp_path):
    path,digest=plan(tmp_path,{"youtube":"a"}); adapter=FakePlatform()
    result=PublicationExecution().execute(path,tmp_path/"run","run-op",confirmation="bad",adapter=adapter)
    assert result.result_class=="REJECTED_CONFIRMATION" and adapter.calls==[]


def test_private_execution_rejects_platform_without_visibility_guarantee(tmp_path):
    path,digest=plan(tmp_path,{"douyin":"a"}); adapter=FakePlatform()
    result=PublicationExecution().execute(path,tmp_path/"run","run-op",confirmation=digest,adapter=adapter)
    assert result.result_class=="REJECTED_POLICY" and adapter.calls==[]


def test_public_jobs_execute_serially_and_replay(tmp_path):
    path,digest=plan(tmp_path,{"youtube":"a","douyin":"b"},public=True); adapter=FakePlatform(); operation=PublicationExecution()
    first=operation.execute(path,tmp_path/"run","run-op",confirmation=digest,adapter=adapter); replay=operation.execute(path,tmp_path/"run","run-op",confirmation=digest,adapter=adapter)
    receipt=json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert first.result_class=="COMPLETED" and replay.result_class=="DUPLICATE_COMPLETED"
    assert adapter.calls==["youtube","douyin"] and receipt["maximumActiveExecutions"]==1


def test_failed_target_resumes_without_repeating_completed_target(tmp_path):
    path,digest=plan(tmp_path,{"youtube":"a","douyin":"b"},public=True); operation=PublicationExecution(); output=tmp_path/"run"
    failed_adapter=FakePlatform(fail="douyin"); failed=operation.execute(path,output,"run-op",confirmation=digest,adapter=failed_adapter)
    resumed_adapter=FakePlatform(); resumed=operation.execute(path,output,"run-op",confirmation=digest,adapter=resumed_adapter)
    assert failed.result_class=="FAILED" and resumed.result_class=="COMPLETED"
    assert failed_adapter.calls==["youtube","douyin"] and resumed_adapter.calls==["douyin"]


def test_adapter_success_without_external_id_cannot_commit_publication(tmp_path):
    class MissingIdentity(FakePlatform):
        def execute(self,job,on_log): return ExecutionOutcome(True,None,{"executed":True})

    path,digest=plan(tmp_path,{"youtube":"a"})
    result=PublicationExecution().execute(
        path,tmp_path/"run","run-op",confirmation=digest,adapter=MissingIdentity()
    )

    assert result.result_class=="FAILED"
    receipt=json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["items"][0]["status"]=="FAILED"


def test_credential_reference_requires_a_configured_vault(tmp_path):
    adapter=PlatformIOExecutionAdapter(tmp_path/"platform.ps1")
    outcome=adapter.execute(
        {
            "platform":"youtube","videoPath":str(tmp_path/"v.mp4"),
            "metadataPath":str(tmp_path/"m.json"),"account":"main",
            "visibility":"private-or-draft","credentialId":"youtube-main",
        },
        lambda _:None,
    )

    assert not outcome.completed
    assert outcome.error=="credential vault is required for referenced credential"


def test_real_vault_injects_secret_into_one_fake_platform_child(tmp_path):
    import os
    import subprocess

    root=Path(__file__).resolve().parents[2]
    vault_app=root/"apps"/"credential-vault"
    vault_path=tmp_path/"vault.json"
    secret="publication-child-only-secret"
    environment={**os.environ,"PYTHONPATH":str(vault_app),"PUBLICATION_SECRET":secret}
    stored=subprocess.run(
        [sys.executable,"-m","credential_vault.cli","put","--vault",str(vault_path),
         "--credential-id","youtube-main","--provider","youtube","--label","Main",
         "--secret-env","PUBLICATION_SECRET","--json"],
        capture_output=True,text=True,encoding="utf-8",env=environment,
    )
    assert stored.returncode==0

    fake_platform=tmp_path/"fake-platform.ps1"
    fake_platform.write_text(
        "param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)\n"
        "$ok = $env:VIDEO_PLATFORM_CREDENTIAL -eq 'publication-child-only-secret'\n"
        "if ($ok) { '{\"status\":\"ok\",\"external_id\":\"fake-123\"}'; exit 0 }\n"
        "'{\"status\":\"failed\",\"error\":\"missing credential\"}'; exit 9\n",
        encoding="utf-8",
    )
    adapter=PlatformIOExecutionAdapter(
        fake_platform,
        vault_launcher=vault_app/"run.ps1",
        vault_path=vault_path,
    )
    job={
        "platform":"youtube","videoPath":str(tmp_path/"v.mp4"),
        "metadataPath":str(tmp_path/"m.json"),"account":"main",
        "visibility":"private-or-draft","credentialId":"youtube-main",
    }

    outcome=adapter.execute(job,lambda _:None)

    assert outcome.completed and outcome.external_id=="fake-123"
    assert secret not in vault_path.read_text(encoding="utf-8")
    assert secret not in json.dumps(outcome.facts)

    wrong_provider=adapter.execute({**job,"platform":"douyin"},lambda _:None)
    assert not wrong_provider.completed


def test_credential_backed_failure_does_not_persist_untrusted_child_output(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import publication.execution as execution

    adapter=PlatformIOExecutionAdapter(
        tmp_path/"platform.ps1",
        vault_launcher=tmp_path/"vault.ps1",
        vault_path=tmp_path/"vault.json",
    )
    secret="untrusted-child-echoed-secret"
    monkeypatch.setattr(
        execution.subprocess,
        "run",
        lambda *args,**kwargs:SimpleNamespace(
            returncode=9,
            stdout=json.dumps({"status":"failed","error":secret}),
            stderr=secret,
        ),
    )

    outcome=adapter.execute(
        {
            "platform":"youtube","videoPath":"v.mp4","metadataPath":"m.json",
            "account":"main","visibility":"private-or-draft","credentialId":"youtube-main",
        },
        lambda _:None,
    )

    assert not outcome.completed
    assert outcome.error=="credential-backed platform upload failed"
    assert secret not in json.dumps(outcome.facts)+str(outcome.error)
