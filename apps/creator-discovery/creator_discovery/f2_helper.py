"""JSON-lines bridge to the pinned F2 Douyin profile paginator."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import json
from pathlib import Path


def cookie_header(path: Path | None) -> str:
    if path is None: return ""
    pairs=[]
    for raw in path.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        line=raw.strip()
        if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")): continue
        columns=line.split("\t")
        if len(columns)>=7: pairs.append(f"{columns[-2]}={columns[-1]}")
    if pairs: return "; ".join(pairs)
    return path.read_text(encoding="utf-8-sig",errors="replace").strip()


@dataclass(frozen=True)
class ResolvedDouyinSource:
    kind: str
    sec_user_id: str
    video: object | None = None


async def resolve_douyin_source(url, handler, profile_fetcher, video_fetcher):
    """Classify a creator profile URL or a shared single-video URL."""
    try:
        return ResolvedDouyinSource("profile", await profile_fetcher.get_sec_user_id(url))
    except Exception as profile_error:
        try:
            aweme_id = await video_fetcher.get_aweme_id(url)
            video = await handler.fetch_one_video(aweme_id)
            sec_user_id = video.sec_user_id
            if not sec_user_id:
                raise ValueError("video author has no sec_user_id")
            return ResolvedDouyinSource("video", sec_user_id, video)
        except Exception as video_error:
            raise profile_error from video_error


async def run(args):
    from f2.apps.douyin.handler import DouyinHandler
    from f2.apps.douyin.utils import AwemeIdFetcher, ClientConfManager, SecUserIdFetcher

    kwargs={"cookie":cookie_header(args.cookies),"headers":{"User-Agent":ClientConfManager.user_agent(),"Referer":ClientConfManager.referer()},"proxies":ClientConfManager.proxies()}
    handler=DouyinHandler(kwargs)
    source=await resolve_douyin_source(args.url,handler,SecUserIdFetcher,AwemeIdFetcher)
    if source.kind == "video":
        raw=source.video._to_raw(); row=raw.get("aweme_detail") or {}
        identity=str(row.get("aweme_id") or "")
        author=row.get("author") or {}
        item={"id":identity,"url":f"https://www.douyin.com/video/{identity}","title":str(row.get("desc") or identity),"publishedAt":int(row.get("create_time") or 0) or None}
        print(json.dumps({"kind":"page","sourceKind":"video","creatorId":source.sec_user_id,"creatorName":author.get("nickname"),"items":[item],"nextCursor":None,"hasMore":False},ensure_ascii=False),flush=True)
        return
    sec_user_id=source.sec_user_id
    maximum=args.max_items or None
    async for page in handler.fetch_user_post_videos(sec_user_id=sec_user_id,max_cursor=int(args.cursor or 0),page_counts=min(20,args.max_items or 20),max_counts=maximum):
        raw=page._to_raw(); awemes=raw.get("aweme_list") or []; items=[]
        for row in awemes:
            identity=str(row.get("aweme_id") or "")
            if not identity: continue
            items.append({"id":identity,"url":f"https://www.douyin.com/video/{identity}","title":str(row.get("desc") or identity),"publishedAt":int(row.get("create_time") or 0) or None})
        author=(awemes[0].get("author") or {}) if awemes else {}
        print(json.dumps({"kind":"page","sourceKind":"profile","creatorId":sec_user_id,"creatorName":author.get("nickname"),"items":items,"nextCursor":str(raw.get("max_cursor")) if raw.get("has_more") else None,"hasMore":bool(raw.get("has_more"))},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("url",nargs="?"); parser.add_argument("--max-items",type=int,default=0); parser.add_argument("--cursor",default=""); parser.add_argument("--cookies",type=Path); parser.add_argument("--doctor",action="store_true")
    args=parser.parse_args()
    if args.doctor:
        from f2.apps.douyin.handler import DouyinHandler  # noqa: F401
        from f2.apps.douyin.utils import ClientConfManager, SecUserIdFetcher  # noqa: F401
        print(json.dumps({"ready":True,"adapter":"f2-douyin-profile@0.0.1.7"})); return
    if not args.url: parser.error("url is required")
    asyncio.run(run(args))


if __name__=="__main__": main()
