import hashlib
import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"publication"
sys.path.insert(0,str(APP))

from publication.contracts import PlanSpec
from publication.execution import ExecutionOutcome, PublicationExecution
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
