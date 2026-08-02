import hashlib
import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"video-graph-studio"; sys.path.insert(0,str(APP))
from studio.adapters import AdapterResult, CommandAdapter, PublicationExecuteAdapter, PublicationPlanAdapter, VerifyPublicationExecutionAdapter, VerifyPublicationPlanAdapter
from studio.api import PUBLICATION_GRAPHS, StudioApplication
from studio.contracts import GraphDefinition
from studio.engine import WorkflowEngine
from studio.server import build_runtime
from studio.store import CreateRun, RunStore


class Noop:
    def execute(self,node,context,on_log,cancel_event):return AdapterResult(True,{})


def envelope(payload):return {"contractId":"CMD-RUN-CREATE","contractVersion":"1.0","operationId":"publish-op","correlationId":"publish-corr","payload":payload}


def assets(tmp_path):
    video=tmp_path/"v.mp4"; video.write_bytes(b"video"); metadata=tmp_path/"m.json"; metadata.write_text(json.dumps({"title":"Title"}),encoding="utf-8"); return video,metadata


def test_publication_plan_graph_admits_verified_local_inputs_and_targets(tmp_path):
    video,metadata=assets(tmp_path); store=RunStore(tmp_path/"studio.db"); app=StudioApplication(store,WorkflowEngine(store,{"plan-publication":Noop(),"verify-publication-plan":Noop()}),allowed_roots=(tmp_path,))
    status,response=app.handle("POST","/api/v1/runs",{},envelope({"templateId":"publication-plan","videoPath":str(video),"metadataPath":str(metadata),"targetPlatforms":["youtube","tiktok"],"account":"primary"}))
    run=store.get_run(response["value"]["runId"])
    assert status==201 and [node["type"] for node in run["graph"]["nodes"]]==["plan-publication","verify-publication-plan"]
    assert run["parameters"]["targetPlatforms"]==["youtube","tiktok"] and run["parameters"]["public"] is False


def test_publication_plan_accepts_only_target_bound_nonsecret_credential_ids(tmp_path):
    video,metadata=assets(tmp_path); store=RunStore(tmp_path/"studio.db"); app=StudioApplication(store,WorkflowEngine(store,{}),allowed_roots=(tmp_path,))
    status,response=app.handle("POST","/api/v1/runs",{},envelope({"templateId":"publication-plan","videoPath":str(video),"metadataPath":str(metadata),"targetPlatforms":["youtube"],"account":"primary","credentialIds":{"youtube":"youtube-main"}}))

    assert status==201
    assert store.get_run(response["value"]["runId"])["parameters"]["credentialIds"]=={"youtube":"youtube-main"}

    bad=dict(envelope({"templateId":"publication-plan","videoPath":str(video),"metadataPath":str(metadata),"targetPlatforms":["youtube"],"account":"primary","credentialIds":{"tiktok":"tiktok-main"}})); bad["operationId"]="bad-op"
    rejected,_=app.handle("POST","/api/v1/runs",{},bad)
    assert rejected==400


def test_publication_plan_graph_rejects_public_or_duplicate_targets(tmp_path):
    video,metadata=assets(tmp_path); store=RunStore(tmp_path/"studio.db"); app=StudioApplication(store,WorkflowEngine(store,{}),allowed_roots=(tmp_path,))
    status,response=app.handle("POST","/api/v1/runs",{},envelope({"templateId":"publication-plan","videoPath":str(video),"metadataPath":str(metadata),"targetPlatforms":["youtube","youtube"],"account":"primary","public":True}))
    assert status==400 and store.list_runs()==[]


def test_verify_publication_plan_checks_hashes_and_job_coverage(tmp_path):
    video,metadata=assets(tmp_path); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest(); plan=tmp_path/"publication-plan.json"
    value={"schemaVersion":1,"video":{"path":str(video),"sha256":sha(video),"size":5},"metadata":{"path":str(metadata),"sha256":sha(metadata),"title":"Title"},"public":False,"jobs":[{"ordinal":1,"id":"a"*64,"platform":"youtube","account":"primary","visibility":"private-or-draft"}]}; plan.write_text(json.dumps(value),encoding="utf-8")
    context={"steps":[{"nodeId":"plan-publication","status":"COMPLETED","result":{"manifest":str(plan),"manifestSha256":sha(plan)}}]}
    assert VerifyPublicationPlanAdapter().execute(None,context,lambda _:None,None).completed
    video.write_bytes(b"changed"); assert not VerifyPublicationPlanAdapter().execute(None,context,lambda _:None,None).completed


def test_runtime_registers_publication_plan_adapters(tmp_path):
    _,engine=build_runtime(Path(__file__).resolve().parents[2],tmp_path/"runtime")
    assert isinstance(engine.adapters["plan-publication"],PublicationPlanAdapter)
    assert isinstance(engine.adapters["verify-publication-plan"],VerifyPublicationPlanAdapter)
    assert isinstance(engine.adapters["execute-publication"],PublicationExecuteAdapter)
    assert isinstance(engine.adapters["verify-publication-execution"],VerifyPublicationExecutionAdapter)


def committed_plan(store,tmp_path):
    video,metadata=assets(tmp_path); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest(); plan=tmp_path/"publication-plan.json"
    plan.write_text(json.dumps({"schemaVersion":1,"video":{"path":str(video),"sha256":sha(video),"size":5},"metadata":{"path":str(metadata),"sha256":sha(metadata),"title":"Title"},"public":False,"jobs":[{"ordinal":1,"id":"a"*64,"platform":"youtube","account":"primary","visibility":"private-or-draft","credentialId":"youtube-main"}]}),encoding="utf-8")
    run_id=store.create_run(CreateRun("source-plan","source-corr",PUBLICATION_GRAPHS["publication-plan"],{})).value["runId"]
    store.transition(run_id,expected_version=0,target="RUNNING")
    store.start_step(run_id,"plan-publication"); store.complete_step(run_id,"plan-publication",{"manifest":str(plan),"manifestSha256":sha(plan),"jobCount":1})
    store.start_step(run_id,"verify-publication-plan"); store.complete_step(run_id,"verify-publication-plan",{"manifest":str(plan),"jobCount":1})
    store.transition(run_id,expected_version=1,target="COMPLETED")
    return run_id,plan,sha(plan)


def test_execution_graph_resolves_same_store_completed_plan_and_exact_confirmation(tmp_path):
    store=RunStore(tmp_path/"studio.db"); plan_run,plan,digest=committed_plan(store,tmp_path); vault=tmp_path/"vault.json"; vault.write_text("{}",encoding="utf-8")
    app=StudioApplication(store,WorkflowEngine(store,{}),allowed_roots=(tmp_path,))
    command=envelope({"templateId":"publication-execute","planRunId":plan_run,"confirmation":digest,"credentialVaultPath":str(vault)}); command["operationId"]="execute-op"

    status,response=app.handle("POST","/api/v1/runs",{},command)
    run=store.get_run(response["value"]["runId"])

    assert status==201
    assert [node["type"] for node in run["graph"]["nodes"]]==["execute-publication","verify-publication-execution"]
    assert run["parameters"]["planPath"]==str(plan.resolve())
    assert run["parameters"]["confirmation"]==digest


def test_execution_graph_rejects_wrong_confirmation_or_unsafe_plan(tmp_path):
    store=RunStore(tmp_path/"studio.db"); plan_run,_,digest=committed_plan(store,tmp_path); vault=tmp_path/"vault.json"; vault.write_text("{}",encoding="utf-8")
    app=StudioApplication(store,WorkflowEngine(store,{}),allowed_roots=(tmp_path,))
    command=envelope({"templateId":"publication-execute","planRunId":plan_run,"confirmation":"0"*64,"credentialVaultPath":str(vault)}); command["operationId"]="wrong-confirmation"
    status,_=app.handle("POST","/api/v1/runs",{},command)

    assert status==400
    assert digest!="0"*64


def test_execution_graph_rejects_plan_run_outside_the_current_store(tmp_path):
    store=RunStore(tmp_path/"studio.db"); vault=tmp_path/"vault.json"; vault.write_text("{}",encoding="utf-8")
    app=StudioApplication(store,WorkflowEngine(store,{}),allowed_roots=(tmp_path,))
    command=envelope({"templateId":"publication-execute","planRunId":"11111111-1111-1111-1111-111111111111","confirmation":"a"*64,"credentialVaultPath":str(vault)}); command["operationId"]="foreign-plan"

    status,_=app.handle("POST","/api/v1/runs",{},command)

    assert status==400
    assert store.list_runs()==[]


def test_execute_and_verify_adapters_commit_only_fingerprinted_external_receipts(tmp_path,monkeypatch):
    plan=tmp_path/"plan.json"; plan.write_text("{}",encoding="utf-8"); vault=tmp_path/"vault.json"; vault.write_text("{}",encoding="utf-8"); output=tmp_path/"outputs"; manifest=output/"run-1"/"publication-manifest.json"; receipt=output/"run-1"/"publication-receipt.json"
    manifest.parent.mkdir(parents=True); manifest.write_text(json.dumps({"schemaVersion":1,"plan":str(plan),"planSha256":hashlib.sha256(plan.read_bytes()).hexdigest(),"public":False,"publications":[{"jobId":"a"*64,"platform":"youtube","status":"COMPLETED","externalId":"yt-private-1","facts":{"visibility":"private-or-draft"}}]}),encoding="utf-8"); receipt.write_text(json.dumps({"resultClass":"COMPLETED","manifest":str(manifest),"manifestSha256":hashlib.sha256(manifest.read_bytes()).hexdigest(),"items":[]}),encoding="utf-8")
    seen={}
    def fake_execute(self,node,context,on_log,cancel_event): seen["argv"]=node.config["argv"]; return AdapterResult(True,{"exitCode":0})
    monkeypatch.setattr(CommandAdapter,"execute",fake_execute)
    adapter=PublicationExecuteAdapter(tmp_path/"publication.ps1",output)
    result=adapter.execute(type("Node",(),{"id":"execute-publication"})(),{"runId":"run-1","parameters":{"planPath":str(plan),"confirmation":hashlib.sha256(plan.read_bytes()).hexdigest(),"credentialVaultPath":str(vault)}},lambda _:None,None)
    context={"parameters":{"planPath":str(plan),"confirmation":hashlib.sha256(plan.read_bytes()).hexdigest()},"steps":[{"nodeId":"execute-publication","status":"COMPLETED","result":result.details}]}

    assert result.completed and "--credential-vault" in seen["argv"]
    assert VerifyPublicationExecutionAdapter().execute(None,context,lambda _:None,None).completed
    manifest.write_text("{}",encoding="utf-8")
    assert not VerifyPublicationExecutionAdapter().execute(None,context,lambda _:None,None).completed
