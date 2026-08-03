from pathlib import Path
import asyncio
import subprocess
import sys
from types import SimpleNamespace


ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/"apps"/"creator-discovery"
sys.path.insert(0,str(APP))

from creator_discovery.f2_helper import resolve_douyin_source


def test_pinned_f2_helper_compatibility_imports():
    python=ROOT.parents[1]/".tools"/"f2"/".venv"/"Scripts"/"python.exe"
    if not python.is_file(): return
    helper=ROOT/"apps"/"creator-discovery"/"creator_discovery"/"f2_helper.py"
    result=subprocess.run([str(python),str(helper),"--doctor"],text=True,capture_output=True,encoding="utf-8",errors="replace")
    assert result.returncode==0 and json_ready(result.stdout)


def json_ready(value):
    return '"ready": true' in value.lower()


def test_video_share_link_is_classified_as_one_video_source():
    class ProfileFetcher:
        @staticmethod
        async def get_sec_user_id(_url):
            raise RuntimeError("not a profile URL")

    class VideoFetcher:
        @staticmethod
        async def get_aweme_id(_url):
            return "7667560510975511842"

    class Handler:
        async def fetch_one_video(self, aweme_id):
            assert aweme_id == "7667560510975511842"
            return SimpleNamespace(sec_user_id="author-sec-user-id")

    result=asyncio.run(resolve_douyin_source("https://v.douyin.com/example/",Handler(),ProfileFetcher,VideoFetcher))

    assert result.kind == "video"
    assert result.sec_user_id == "author-sec-user-id"
    assert result.video is not None
