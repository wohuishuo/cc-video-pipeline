import hashlib
import json
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult, VoiceRenderingAdapter, VerifyVoiceAdapter  # noqa: E402
from studio.api import StudioApplication  # noqa: E402
from studio.engine import WorkflowEngine  # noqa: E402
from studio.server import build_runtime  # noqa: E402
from studio.store import RunStore  # noqa: E402


class Noop:
    def execute(self, node, context, on_log, cancel_event): return AdapterResult(True, {})


def envelope(payload):
    return {"contractId":"CMD-RUN-CREATE","contractVersion":"1.0","operationId":"voice-op","correlationId":"voice-corr","payload":payload}


def test_folder_voice_graph_has_eight_owner_steps(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    types = ["source-intake","verify-source","transcribe-source","verify-transcript","translate-transcript","verify-translation","render-voice","verify-voice"]
    app = StudioApplication(store, WorkflowEngine(store, {key:Noop() for key in types}), allowed_roots=(tmp_path,))
    source=tmp_path/"media"; source.mkdir()
    status,response=app.handle("POST","/api/v1/runs",{},envelope({
        "templateId":"folder-voice","sourceRoot":str(source),"targetLanguages":["ru-RU","kk-KZ"],
        "targetVoices":{"ru-RU":"ru-RU-DmitryNeural","kk-KZ":"kk-KZ-DauletNeural"},
    }))
    run=store.get_run(response["value"]["runId"])
    assert status==201
    assert [node["type"] for node in run["graph"]["nodes"]]==types
    assert run["parameters"]["targetVoices"]["kk-KZ"]=="kk-KZ-DauletNeural"


def test_verify_voice_checks_clip_hashes_and_exact_count(tmp_path):
    clip=tmp_path/"clip.mp3"; clip.write_bytes(b"audio")
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=tmp_path/"voice-manifest.json"
    manifest.write_text(json.dumps({"schemaVersion":1,"voices":{"ru-RU":"voice"},"clips":[{"targetLanguage":"ru-RU","mediaId":"m1","segmentId":1,"clip":{"path":str(clip),"sha256":digest(clip),"duration":1.0,"size":5}}]}),encoding="utf-8")
    context={"steps":[{"nodeId":"render-voice","status":"COMPLETED","result":{"manifest":str(manifest),"manifestSha256":digest(manifest)}}]}
    assert VerifyVoiceAdapter().execute(None,context,lambda _:None,None).completed
    clip.write_bytes(b"bad")
    assert not VerifyVoiceAdapter().execute(None,context,lambda _:None,None).completed


def test_runtime_registers_voice_adapters(tmp_path):
    _,engine=build_runtime(Path(__file__).resolve().parents[2],tmp_path/"runtime")
    assert isinstance(engine.adapters["render-voice"],VoiceRenderingAdapter)
    assert isinstance(engine.adapters["verify-voice"],VerifyVoiceAdapter)
