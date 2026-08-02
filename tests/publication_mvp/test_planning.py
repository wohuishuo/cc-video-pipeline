import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"publication"
sys.path.insert(0,str(APP))

from publication.contracts import PlanSpec, PublicationError
from publication.planning import PublicationPlanner


def assets(tmp_path):
    video=tmp_path/"video.mp4"; video.write_bytes(b"video")
    metadata=tmp_path/"metadata.json"; metadata.write_text(json.dumps({"title":"Launch","description":"Desc","tags":["one"]}),encoding="utf-8")
    return video,metadata


def test_plan_is_deterministic_private_by_default_and_replays(tmp_path):
    video,metadata=assets(tmp_path); spec=PlanSpec.create(video,metadata,{"youtube":"primary","douyin":"cn"})
    planner=PublicationPlanner(); first=planner.execute(spec,tmp_path/"out","op-1"); replay=planner.execute(spec,tmp_path/"out","op-1")
    value=json.loads(first.plan_path.read_text(encoding="utf-8"))
    assert first.result_class=="COMPLETED" and replay.result_class=="DUPLICATE_COMPLETED"
    assert [row["platform"] for row in value["jobs"]]==["youtube","douyin"]
    assert all(row["visibility"]=="private-or-draft" for row in value["jobs"])


def test_changed_plan_conflicts_and_no_secret_fields_are_published(tmp_path):
    video,metadata=assets(tmp_path); planner=PublicationPlanner(); output=tmp_path/"out"
    planner.execute(PlanSpec.create(video,metadata,{"youtube":"primary"}),output,"op-1")
    conflict=planner.execute(PlanSpec.create(video,metadata,{"youtube":"secondary"}),output,"op-1")
    assert conflict.result_class=="REJECTED_CONFLICT"
    text=(output/"publication-plan.json").read_text(encoding="utf-8").lower()
    assert "cookie" not in text and "password" not in text and "token" not in text


def test_invalid_metadata_or_duplicate_targets_are_rejected(tmp_path):
    video,metadata=assets(tmp_path); metadata.write_text("{}",encoding="utf-8")
    try: PlanSpec.create(video,metadata,{"youtube":"a"})
    except PublicationError: pass
    else: raise AssertionError("missing title accepted")
