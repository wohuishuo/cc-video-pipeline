import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"creator-discovery"
sys.path.insert(0,str(APP))

from creator_discovery.contracts import CreatorItem, DiscoveryPage, ProfileSpec
from creator_discovery.operation import DiscoveryOperation


class FakeEnumerator:
    identity="fake-profile@1"
    def __init__(self,fail_after=None): self.calls=[]; self.fail_after=fail_after
    def enumerate(self,spec,cookies,cursor,on_log):
        self.calls.append(cursor)
        pages=(
            DiscoveryPage("creator-1","Creator",(CreatorItem("v2","https://www.douyin.com/video/v2","Two",2),),"next",True),
            DiscoveryPage("creator-1","Creator",(CreatorItem("v2","https://www.douyin.com/video/v2","Two",2),CreatorItem("v1","https://www.douyin.com/video/v1","One",1)),None,False),
        )
        start=1 if cursor=="next" else 0
        for index,page in enumerate(pages[start:],start):
            if self.fail_after==index: raise RuntimeError("network failed")
            yield page


def test_pages_checkpoint_dedupe_and_publish_ordered_manifest(tmp_path):
    result=DiscoveryOperation().execute(ProfileSpec.from_url("https://www.douyin.com/user/x"),tmp_path/"out","op-1",enumerator=FakeEnumerator())
    manifest=json.loads(result.manifest_path.read_text(encoding="utf-8")); receipt=json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert result.result_class=="COMPLETED"
    assert [item["id"] for item in manifest["items"]]==["v2","v1"]
    assert manifest["complete"] is True and receipt["itemCount"]==2 and receipt["maximumActivePages"]==1


def test_same_operation_replays_and_changed_input_conflicts(tmp_path):
    adapter=FakeEnumerator(); operation=DiscoveryOperation(); output=tmp_path/"out"
    first=operation.execute(ProfileSpec.from_url("https://youtube.com/@x",max_items=3),output,"op-1",enumerator=adapter)
    replay=operation.execute(ProfileSpec.from_url("https://youtube.com/@x",max_items=3),output,"op-1",enumerator=adapter)
    conflict=operation.execute(ProfileSpec.from_url("https://youtube.com/@x",max_items=4),output,"op-1",enumerator=adapter)
    assert first.result_class=="COMPLETED" and replay.result_class=="DUPLICATE_COMPLETED"
    assert conflict.result_class=="REJECTED_CONFLICT" and len(adapter.calls)==1


def test_failure_receipt_resumes_from_cursor_without_cookie_leak(tmp_path):
    operation=DiscoveryOperation(); output=tmp_path/"out"; spec=ProfileSpec.from_url("https://v.douyin.com/a/",cookie_key="b"*64)
    failed=operation.execute(spec,output,"op-1",enumerator=FakeEnumerator(fail_after=1),cookies=tmp_path/"cookies.txt")
    resumed_adapter=FakeEnumerator(); resumed=operation.execute(spec,output,"op-1",enumerator=resumed_adapter,cookies=tmp_path/"cookies.txt")
    assert failed.result_class=="FAILED" and resumed.result_class=="COMPLETED" and resumed_adapter.calls==["next"]
    assert "cookie" not in failed.receipt_path.read_text(encoding="utf-8").lower()


def test_limit_marks_manifest_truncated(tmp_path):
    result=DiscoveryOperation().execute(ProfileSpec.from_url("https://youtube.com/@x",max_items=1),tmp_path/"out","op",enumerator=FakeEnumerator())
    value=json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert len(value["items"])==1 and value["complete"] is False and value["truncated"] is True


def test_single_video_source_kind_is_committed_to_manifest(tmp_path):
    class SingleVideoEnumerator:
        identity="single-video@1"
        def enumerate(self,spec,cookies,cursor,on_log):
            yield DiscoveryPage("creator-1","Creator",(CreatorItem("v1","https://www.douyin.com/video/v1","One",1),),None,False,"video")

    result=DiscoveryOperation().execute(ProfileSpec.from_url("https://v.douyin.com/a/"),tmp_path/"out","op",enumerator=SingleVideoEnumerator())
    value=json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert value["sourceKind"] == "video"
    assert value["complete"] is True
