"""Replaceable profile-enumeration adapters."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess

from .contracts import CreatorItem, DiscoveryError, DiscoveryPage, ProfileSpec


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int
    stdout: str
    stderr: str


class SubprocessRunner:
    def run(self, argv, env=None):
        result = subprocess.run(argv, text=True, capture_output=True, encoding="utf-8", errors="replace", env={**os.environ, **(env or {})})
        return ProcessResult(result.returncode, result.stdout, result.stderr)


class YtDlpProfileEnumerator:
    identity = "yt-dlp-flat-profile@1"
    def __init__(self, runner=None): self.runner = runner or SubprocessRunner()

    def enumerate(self, spec: ProfileSpec, cookies: Path | None, cursor: str | None, on_log):
        if cursor: on_log("Adapter restarts metadata enumeration; committed IDs remain deduplicated")
        argv = ["yt-dlp", "--flat-playlist", "--dump-single-json", "--skip-download", "--no-warnings"]
        if spec.max_items: argv.extend(["--playlist-end", str(spec.max_items)])
        if cookies: argv.extend(["--cookies", str(Path(cookies).resolve())])
        argv.append(spec.url); result = self.runner.run(argv)
        if result.exit_code != 0: raise DiscoveryError(result.stderr[-4000:] or "yt-dlp profile enumeration failed")
        try:
            payload = json.loads(result.stdout)
            source_kind = "profile" if isinstance(payload.get("entries"), list) else "video"
            raw_items = payload.get("entries", []) if source_kind == "profile" else [payload]
        except (json.JSONDecodeError, TypeError) as error: raise DiscoveryError(f"invalid yt-dlp metadata: {error}") from error
        items=[]
        for row in raw_items:
            if not isinstance(row,dict) or not row.get("id"): continue
            identity=str(row["id"]); url=str(row.get("webpage_url") or row.get("url") or "")
            if not url.startswith("https://"):
                if spec.platform=="youtube": url=f"https://www.youtube.com/watch?v={identity}"
                elif spec.platform=="bilibili": url=f"https://www.bilibili.com/video/{identity}"
                else: continue
            items.append(CreatorItem(identity,url,str(row.get("title") or identity),int(row["timestamp"]) if row.get("timestamp") else None))
        has_more=source_kind == "profile" and bool(spec.max_items and len(items)>=spec.max_items)
        yield DiscoveryPage(str(payload.get("channel_id") or payload.get("uploader_id") or payload.get("id") or "") or None,str(payload.get("channel") or payload.get("uploader") or payload.get("title") or "") or None,tuple(items),None,has_more,source_kind)


class F2DouyinEnumerator:
    identity = "f2-douyin-profile@0.0.1.7"
    def __init__(self, python: Path, helper: Path): self.python=Path(python).resolve(); self.helper=Path(helper).resolve()

    def enumerate(self, spec: ProfileSpec, cookies: Path | None, cursor: str | None, on_log):
        if not self.python.is_file() or not self.helper.is_file(): raise DiscoveryError("pinned F2 profile runtime is unavailable")
        argv=[str(self.python),str(self.helper),spec.url,"--max-items",str(spec.max_items),"--cursor",str(cursor or "")]
        if cookies: argv.extend(["--cookies",str(Path(cookies).resolve())])
        process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",env={**os.environ,"PYTHONUTF8":"1","PYTHONIOENCODING":"utf-8"})
        assert process.stdout is not None
        yielded=False
        for line in process.stdout:
            try: value=json.loads(line)
            except json.JSONDecodeError: continue
            if value.get("kind")!="page": continue
            items=tuple(CreatorItem(str(row["id"]),str(row["url"]),str(row.get("title") or row["id"]),int(row["publishedAt"]) if row.get("publishedAt") else None) for row in value.get("items",[]))
            yielded=True; yield DiscoveryPage(value.get("creatorId"),value.get("creatorName"),items,value.get("nextCursor"),bool(value.get("hasMore")),str(value.get("sourceKind") or "profile"))
        stderr=process.stderr.read() if process.stderr else ""; code=process.wait()
        if code!=0: raise DiscoveryError(stderr[-4000:] or "F2 profile enumeration failed")
        if not yielded: raise DiscoveryError("F2 returned no profile pages")
