import hashlib
import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"video-graph-studio"
sys.path.insert(0,str(APP))

from studio.adapters import AdapterResult, CreatorDiscoveryAdapter, VerifyCreatorManifestAdapter
from studio.api import StudioApplication
from studio.engine import WorkflowEngine
from studio.server import build_runtime
from studio.store import RunStore


class Noop:
    def execute(self,node,context,on_log,cancel_event): return AdapterResult(True,{})


def envelope(payload): return {"contractId":"CMD-RUN-CREATE","contractVersion":"1.0","operationId":"creator-op","correlationId":"creator-corr","payload":payload}


def test_creator_graph_admits_profile_limit_and_home_authentication_file(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,"home",classmethod(lambda cls:tmp_path)); cookie=tmp_path/"cookies.txt"; cookie.write_text("secret",encoding="utf-8")
    store=RunStore(tmp_path/"studio.db"); app=StudioApplication(store,WorkflowEngine(store,{"discover-creator":Noop(),"verify-creator":Noop()}),allowed_roots=(tmp_path,))
    status,response=app.handle("POST","/api/v1/runs",{},envelope({"templateId":"creator-profile","sourceUrl":"https://v.douyin.com/example/","maxItems":74,"authenticationFile":str(cookie)}))
    run=store.get_run(response["value"]["runId"])
    assert status==201 and [node["type"] for node in run["graph"]["nodes"]]==["discover-creator","verify-creator"]
    assert run["parameters"]["maxItems"]==74 and run["parameters"]["authenticationFile"]==str(cookie.resolve())


def test_creator_graph_rejects_authentication_file_outside_home(tmp_path,monkeypatch):
    home=tmp_path/"home"; home.mkdir(); monkeypatch.setattr(Path,"home",classmethod(lambda cls:home)); outside=tmp_path/"secret.txt"; outside.write_text("secret",encoding="utf-8")
    store=RunStore(tmp_path/"studio.db"); app=StudioApplication(store,WorkflowEngine(store,{}),allowed_roots=(tmp_path,))
    status,response=app.handle("POST","/api/v1/runs",{},envelope({"templateId":"creator-profile","sourceUrl":"https://youtube.com/@creator","maxItems":3,"authenticationFile":str(outside)}))
    assert status==400 and response["resultClass"]=="REJECTED_MALFORMED" and store.list_runs()==[]


def test_verify_creator_manifest_checks_hash_order_uniqueness_and_limit(tmp_path):
    manifest=tmp_path/"creator-manifest.json"; value={"schemaVersion":1,"platform":"douyin","requestedUrl":"https://v.douyin.com/a/","creator":{"id":"c","name":"Creator"},"adapter":"fake@1","maxItems":2,"complete":False,"truncated":True,"items":[{"ordinal":1,"id":"v2","url":"https://www.douyin.com/video/v2","title":"Two","publishedAt":2},{"ordinal":2,"id":"v1","url":"https://www.douyin.com/video/v1","title":"One","publishedAt":1}]}
    manifest.write_text(json.dumps(value),encoding="utf-8"); digest=hashlib.sha256(manifest.read_bytes()).hexdigest(); context={"steps":[{"nodeId":"discover-creator","status":"COMPLETED","result":{"manifest":str(manifest),"manifestSha256":digest}}]}
    assert VerifyCreatorManifestAdapter().execute(None,context,lambda _:None,None).completed
    value["items"][1]["id"]="v2"; manifest.write_text(json.dumps(value),encoding="utf-8"); context["steps"][0]["result"]["manifestSha256"]=hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert not VerifyCreatorManifestAdapter().execute(None,context,lambda _:None,None).completed


def test_runtime_registers_creator_discovery_adapters(tmp_path):
    _,engine=build_runtime(Path(__file__).resolve().parents[2],tmp_path/"runtime")
    assert isinstance(engine.adapters["discover-creator"],CreatorDiscoveryAdapter)
    assert isinstance(engine.adapters["verify-creator"],VerifyCreatorManifestAdapter)
