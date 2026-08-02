import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"localization"
sys.path.insert(0,str(APP))

from .helpers import manifests  # noqa: E402
from localization_app.ffmpeg import ProbeResult  # noqa: E402
from localization_app.operation import LocalizationLoop  # noqa: E402


class FakeAdapter:
    identity="fake-composer@1"
    def __init__(self,failures=()): self.failures=set(failures); self.calls=[]; self.active=0; self.maximum_active=0
    def compose(self,job,output,on_log,*,source_volume):
        key=(job.target_language,job.media_id); self.calls.append(key); self.active+=1; self.maximum_active=max(self.maximum_active,self.active)
        try:
            if key in self.failures: raise RuntimeError(f"failed {key}")
            output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(f"mp4-{key}".encode())
            return ProbeResult(4.0,320,240,"h264","aac",True)
        finally: self.active-=1


def test_loop_publishes_verified_derivatives_in_translation_order(tmp_path):
    inputs=manifests(tmp_path); adapter=FakeAdapter()
    result=LocalizationLoop().execute(*inputs,tmp_path/"out","op-1",adapter=adapter,source_volume=0.12)
    assert result.result_class=="COMPLETED"
    assert adapter.calls==[("ru-RU","m1"),("en-US","m1")]
    assert adapter.maximum_active==1
    manifest=json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [(row["targetLanguage"],row["mediaId"]) for row in manifest["derivatives"]]==adapter.calls
    assert all(Path(row["path"]).is_file() and row["videoCodec"]=="h264" and row["audioCodec"]=="aac" for row in manifest["derivatives"])


def test_failure_preserves_completed_derivative_and_retry_only_runs_failed_item(tmp_path):
    inputs=manifests(tmp_path); output=tmp_path/"out"
    failed=LocalizationLoop().execute(*inputs,output,"op-1",adapter=FakeAdapter({("ru-RU","m1")}),source_volume=0.12)
    assert failed.result_class=="FAILED" and failed.manifest_path is None
    receipt=json.loads(failed.receipt_path.read_text(encoding="utf-8"))
    assert [row["status"] for row in receipt["items"]]==["FAILED","COMPLETED"]
    retry=FakeAdapter(); completed=LocalizationLoop().execute(*inputs,output,"op-1",adapter=retry,source_volume=0.12)
    assert completed.result_class=="COMPLETED"
    assert retry.calls==[("ru-RU","m1")]


def test_completed_replay_skips_composition_and_policy_change_conflicts(tmp_path):
    inputs=manifests(tmp_path); output=tmp_path/"out"
    LocalizationLoop().execute(*inputs,output,"op-1",adapter=FakeAdapter(),source_volume=0.12)
    replay_adapter=FakeAdapter(); replay=LocalizationLoop().execute(*inputs,output,"op-1",adapter=replay_adapter,source_volume=0.12)
    conflict=LocalizationLoop().execute(*inputs,output,"op-1",adapter=FakeAdapter(),source_volume=0.2)
    assert replay.result_class=="DUPLICATE_COMPLETED" and replay_adapter.calls==[]
    assert conflict.result_class=="REJECTED_CONFLICT"
