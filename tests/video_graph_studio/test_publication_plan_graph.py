import hashlib
import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"video-graph-studio"; sys.path.insert(0,str(APP))
from studio.adapters import AdapterResult, PublicationPlanAdapter, VerifyPublicationPlanAdapter
from studio.api import StudioApplication
from studio.engine import WorkflowEngine
from studio.server import build_runtime
from studio.store import RunStore


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
