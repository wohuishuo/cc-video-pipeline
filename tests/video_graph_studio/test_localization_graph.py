import hashlib
import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"video-graph-studio"
sys.path.insert(0,str(APP))

from studio.adapters import AdapterResult, LocalizedVideoAdapter, VerifyLocalizationAdapter  # noqa: E402
from studio.api import StudioApplication  # noqa: E402
from studio.engine import WorkflowEngine  # noqa: E402
from studio.server import build_runtime  # noqa: E402
from studio.store import RunStore  # noqa: E402


class Noop:
    def execute(self,node,context,on_log,cancel_event): return AdapterResult(True,{})


def envelope(payload): return {"contractId":"CMD-RUN-CREATE","contractVersion":"1.0","operationId":"dub-op","correlationId":"dub-corr","payload":payload}


def test_folder_dub_graph_has_ten_owner_steps_and_audio_policy(tmp_path):
    types=["source-intake","verify-source","transcribe-source","verify-transcript","translate-transcript","verify-translation","render-voice","verify-voice","localize-video","verify-localization"]
    store=RunStore(tmp_path/"studio.db"); app=StudioApplication(store,WorkflowEngine(store,{value:Noop() for value in types}),allowed_roots=(tmp_path,))
    source=tmp_path/"media"; source.mkdir()
    status,response=app.handle("POST","/api/v1/runs",{},envelope({"templateId":"folder-dub","sourceRoot":str(source),"targetLanguages":["ru-RU"],"targetVoices":{"ru-RU":"ru-RU-DmitryNeural"},"sourceVolume":0.12}))
    run=store.get_run(response["value"]["runId"])
    assert status==201 and [node["type"] for node in run["graph"]["nodes"]]==types
    assert run["parameters"]["sourceVolume"]==0.12


def test_dub_graph_rejects_out_of_range_source_volume(tmp_path):
    store=RunStore(tmp_path/"studio.db"); app=StudioApplication(store,WorkflowEngine(store,{}),allowed_roots=(tmp_path,)); source=tmp_path/"media"; source.mkdir()
    status,response=app.handle("POST","/api/v1/runs",{},envelope({"templateId":"folder-dub","sourceRoot":str(source),"targetLanguages":["ru-RU"],"targetVoices":{"ru-RU":"voice"},"sourceVolume":1.5}))
    assert status==400 and response["resultClass"]=="REJECTED_MALFORMED" and store.list_runs()==[]


def test_verify_localization_requires_exact_coverage_and_file_hash(tmp_path):
    video=tmp_path/"out.mp4"; video.write_bytes(b"mp4"); digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=tmp_path/"localization-manifest.json"; manifest.write_text(json.dumps({"schemaVersion":1,"targetLanguages":["ru-RU"],"expectedMediaIds":["m1"],"derivatives":[{"targetLanguage":"ru-RU","mediaId":"m1","path":str(video),"sha256":digest(video),"size":3,"duration":4.0,"width":320,"height":240,"videoCodec":"h264","audioCodec":"aac"}]}),encoding="utf-8")
    context={"steps":[{"nodeId":"localize-video","status":"COMPLETED","result":{"manifest":str(manifest),"manifestSha256":digest(manifest)}}]}
    assert VerifyLocalizationAdapter().execute(None,context,lambda _:None,None).completed
    video.write_bytes(b"bad")
    assert not VerifyLocalizationAdapter().execute(None,context,lambda _:None,None).completed


def test_runtime_registers_localization_adapters(tmp_path):
    _,engine=build_runtime(Path(__file__).resolve().parents[2],tmp_path/"runtime")
    assert isinstance(engine.adapters["localize-video"],LocalizedVideoAdapter)
    assert isinstance(engine.adapters["verify-localization"],VerifyLocalizationAdapter)
