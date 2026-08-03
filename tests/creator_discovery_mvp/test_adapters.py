import json
from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"creator-discovery"
sys.path.insert(0,str(APP))

from creator_discovery.adapters import ProcessResult, YtDlpProfileEnumerator
from creator_discovery.contracts import ProfileSpec


class Runner:
    def __init__(self,payload): self.payload=payload; self.argv=None
    def run(self,argv,env=None): self.argv=argv; return ProcessResult(0,json.dumps(self.payload),"")


def test_ytdlp_adapter_uses_flat_metadata_and_canonicalizes_entries(tmp_path):
    runner=Runner({"id":"channel","title":"Creator","entries":[{"id":"abc","title":"A","timestamp":7}]})
    adapter=YtDlpProfileEnumerator(runner=runner); spec=ProfileSpec.from_url("https://youtube.com/@creator",max_items=1)
    pages=list(adapter.enumerate(spec,None,None,lambda _:None))
    assert "--flat-playlist" in runner.argv and "--playlist-end" in runner.argv
    assert pages[0].items[0].url=="https://www.youtube.com/watch?v=abc" and pages[0].has_more


def test_ytdlp_adapter_passes_cookie_path_but_does_not_log_it(tmp_path):
    cookie=tmp_path/"secret.txt"; cookie.write_text("secret",encoding="utf-8")
    runner=Runner({"entries":[{"id":"BV1","url":"https://www.bilibili.com/video/BV1"}]})
    logs=[]; list(YtDlpProfileEnumerator(runner=runner).enumerate(ProfileSpec.from_url("https://space.bilibili.com/1"),cookie,None,logs.append))
    assert "--cookies" in runner.argv and str(cookie.resolve()) in runner.argv and all(str(cookie) not in line for line in logs)


def test_ytdlp_adapter_classifies_single_video_metadata():
    runner=Runner({"id":"abc","title":"One video","webpage_url":"https://www.youtube.com/watch?v=abc","channel_id":"creator","channel":"Creator"})
    page=list(YtDlpProfileEnumerator(runner=runner).enumerate(ProfileSpec.from_url("https://youtu.be/abc"),None,None,lambda _:None))[0]

    assert page.source_kind == "video"
    assert [item.id for item in page.items] == ["abc"]
    assert page.has_more is False
